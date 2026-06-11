"""Session tracker — push agent session metadata to S3 + iField Mongo.

Used by all three live agents:
  - drawing-agent          (agents/rag-engine)
  - scope-of-work          (agents/doc-generator)
  - constructability-review (agents/review-pipeline)

Two public entrypoints:

  push_session_start(user_id, project_id, agent_id, client_session_id, **meta)
      Called once when a UI session begins. Writes a tiny S3 marker file and
      POSTs to the userSession API.

  push_session_call(user_id, project_id, agent_id, client_session_id, payload)
      Called once per agent call (chat turn, scope-gap run, etc.). Writes the
      full request/response payload to S3 and POSTs to the userSession API so
      iField records a Mongo row pointing at the S3 object.

Both are best-effort + non-blocking: on any failure they log a warning, never
raise, and never block the user-facing flow. Two events share the same
``client_session_id`` (caller-supplied UUID) in their S3 payloads, which is how
calls are linked back to their session-start row; the API has no parent/child
field of its own.
"""
from __future__ import annotations

import json
import logging
import os
import uuid
from datetime import datetime, timezone
from typing import Any, Literal

import requests

logger = logging.getLogger(__name__)


VALID_AGENT_IDS = frozenset({
    "drawing-agent",
    "scope-of-work",
    "constructability-review",
})

USERSESSION_URL = "https://mongo.ifieldsmart.com/api/userSession"
DEFAULT_S3_BUCKET = "agentic-ai-production"
DEFAULT_TIMEOUT_SECONDS = 5.0
MAX_RESPONSE_BYTES = 100_000  # truncate large agent responses before S3 PUT


def _userSession_url() -> str:
    return os.environ.get("IFIELD_USERSESSION_URL", USERSESSION_URL)


def _userSession_timeout_s() -> float:
    return float(os.environ.get(
        "IFIELD_USERSESSION_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS,
    ))


def _s3_bucket() -> str:
    return os.environ.get("S3_BUCKET", DEFAULT_S3_BUCKET)


def _validate_agent_id(agent_id: str) -> None:
    if agent_id not in VALID_AGENT_IDS:
        raise ValueError(
            f"unknown agent_id {agent_id!r}; "
            f"must be one of {sorted(VALID_AGENT_IDS)}"
        )


def _truncate_response(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a new dict with ``response`` truncated to MAX_RESPONSE_BYTES."""
    out = dict(payload)
    response = out.get("response")
    if isinstance(response, str) and len(response.encode("utf-8", "ignore")) > MAX_RESPONSE_BYTES:
        encoded = response.encode("utf-8", "ignore")[:MAX_RESPONSE_BYTES]
        out["response"] = encoded.decode("utf-8", "ignore")
        out["response_truncated"] = True
    return out


def _s3_client():
    import boto3
    return boto3.client(
        "s3",
        region_name=os.environ.get("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.environ.get("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.environ.get("AWS_SECRET_ACCESS_KEY"),
    )


def _write_s3_json(*, bucket: str, key: str, payload: dict[str, Any]) -> bool:
    try:
        s3 = _s3_client()
        body = json.dumps(payload, default=str, indent=2).encode("utf-8")
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=body,
            ContentType="application/json",
        )
        return True
    except Exception as e:
        logger.warning(
            "[session] S3 write failed for %s/%s: %s: %s",
            bucket, key, type(e).__name__, e,
        )
        return False


def _post_user_session(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
    s3_bucket_path: str,
) -> str | None:
    """POST to userSession; return ifield-issued sessionId on 200, else None."""
    try:
        resp = requests.post(
            _userSession_url(),
            json={
                "userId":       int(user_id),
                "projectId":    int(project_id),
                "agent":        agent_id,
                "s3BucketPath": s3_bucket_path,
            },
            timeout=_userSession_timeout_s(),
        )
        if resp.status_code != 200:
            logger.warning(
                "[session] userSession API returned %s: %s",
                resp.status_code, resp.text[:200],
            )
            return None
        body = resp.json()
        return ((body or {}).get("data") or {}).get("sessionId")
    except Exception as e:
        logger.warning(
            "[session] userSession API call failed: %s: %s",
            type(e).__name__, e,
        )
        return None


def _push(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
    client_session_id: str,
    event_uuid: str,
    kind: Literal["session_start", "call"],
    payload: dict[str, Any],
) -> dict[str, Any]:
    _validate_agent_id(agent_id)

    bucket = _s3_bucket()
    if kind == "session_start":
        key = (
            f"sessions/{int(user_id)}/{int(project_id)}/{agent_id}/"
            f"_session-start_{client_session_id}.json"
        )
    else:
        key = (
            f"sessions/{int(user_id)}/{int(project_id)}/{agent_id}/"
            f"{event_uuid}.json"
        )
    s3_full = f"{bucket}/{key}"

    full_payload = {
        "kind":               kind,
        "client_session_id":  client_session_id,
        "event_id":           event_uuid,
        "user_id":            int(user_id),
        "project_id":         int(project_id),
        "agent_id":           agent_id,
        "captured_at":        datetime.now(timezone.utc).isoformat(),
        **_truncate_response(payload or {}),
    }

    s3_ok = _write_s3_json(bucket=bucket, key=key, payload=full_payload)
    ifield_id = _post_user_session(
        user_id=user_id,
        project_id=project_id,
        agent_id=agent_id,
        s3_bucket_path=s3_full,
    )

    if ifield_id:
        logger.info(
            "[session] pushed kind=%s agent=%s client_session=%s ifield=%s",
            kind, agent_id, client_session_id, ifield_id,
        )

    return {
        "client_session_id": client_session_id,
        "event_id":          event_uuid,
        "s3_bucket_path":    s3_full,
        "ifield_session_id": ifield_id,
        "s3_written":        s3_ok,
        "ifield_pushed":     bool(ifield_id),
    }


def push_session_start(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
    client_session_id: str | None = None,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Register a new UI session for an agent.

    Returns a dict with ``client_session_id`` (use it for subsequent
    push_session_call invocations to link calls back to this session).
    """
    sid = client_session_id or str(uuid.uuid4())
    return _push(
        user_id=user_id,
        project_id=project_id,
        agent_id=agent_id,
        client_session_id=sid,
        event_uuid=sid,
        kind="session_start",
        payload=payload or {},
    )


def push_session_call(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
    client_session_id: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    """Record one agent call (chat turn / pipeline run) inside an existing session."""
    if not client_session_id:
        raise ValueError("client_session_id is required for push_session_call")
    return _push(
        user_id=user_id,
        project_id=project_id,
        agent_id=agent_id,
        client_session_id=client_session_id,
        event_uuid=str(uuid.uuid4()),
        kind="call",
        payload=payload,
    )


# ── read-side helpers (list + detail) ────────────────────────────────


def list_sessions(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
) -> dict[str, Any]:
    """Return all userSession rows for one (user, project, agent).

    Proxies ``GET https://mongo.ifieldsmart.com/api/userSession/byAgent``.
    Result shape: ``{"success": bool, "data": [<record>, ...]}``.

    On error returns ``{"success": False, "error": "...", "data": []}`` —
    never raises (best-effort, matches push semantics).
    """
    _validate_agent_id(agent_id)
    base = _userSession_url().rstrip("/")
    url = f"{base}/byAgent"
    try:
        resp = requests.get(
            url,
            params={
                "userId":    int(user_id),
                "projectId": int(project_id),
                "agent":     agent_id,
            },
            timeout=_userSession_timeout_s(),
        )
        if resp.status_code != 200:
            logger.warning(
                "[session] list_sessions HTTP %s: %s",
                resp.status_code, resp.text[:200],
            )
            return {"success": False, "error": f"HTTP {resp.status_code}", "data": []}
        body = resp.json() or {}
        data = body.get("data") or []
        return {"success": True, "data": data, "count": len(data)}
    except Exception as e:
        logger.warning(
            "[session] list_sessions failed: %s: %s",
            type(e).__name__, e,
        )
        return {"success": False, "error": f"{type(e).__name__}: {e}", "data": []}


def fetch_session_payload(s3_bucket_path: str) -> dict[str, Any] | None:
    """Fetch the audit JSON for one session from S3 (``s3BucketPath`` in Mongo).

    Returns ``None`` if the object isn't found or the read fails. Never raises.
    """
    if not s3_bucket_path or "/" not in s3_bucket_path:
        return None
    bucket, _, key = s3_bucket_path.partition("/")
    if not bucket or not key:
        return None
    try:
        s3 = _s3_client()
        obj = s3.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        return json.loads(body.decode("utf-8"))
    except Exception as e:
        logger.warning(
            "[session] fetch_session_payload failed for %s: %s: %s",
            s3_bucket_path, type(e).__name__, e,
        )
        return None


def get_session_by_id(
    *,
    user_id: int,
    project_id: int,
    agent_id: str,
    session_id: str,
    include_payload: bool = True,
) -> dict[str, Any] | None:
    """Return a single session row + (optionally) its S3 payload.

    Enforces user ownership: the lookup is filtered by ``user_id`` via the
    byAgent API, so a session created by user A cannot be fetched by user B
    (no record returned).

    Shape:
        ``{"record": {<mongo doc>}, "payload": {<s3 blob>} | None}``
    or ``None`` if no record matches.
    """
    res = list_sessions(
        user_id=user_id, project_id=project_id, agent_id=agent_id,
    )
    if not res.get("success"):
        return None
    match = next(
        (r for r in res["data"] if r.get("sessionId") == session_id),
        None,
    )
    if match is None:
        return None
    out: dict[str, Any] = {"record": match, "payload": None}
    if include_payload:
        out["payload"] = fetch_session_payload(match.get("s3BucketPath", ""))
    return out


__all__ = [
    "VALID_AGENT_IDS",
    "push_session_start",
    "push_session_call",
    "list_sessions",
    "fetch_session_payload",
    "get_session_by_id",
]
