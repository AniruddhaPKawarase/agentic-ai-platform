"""
S3 configuration — reads from environment variables.

Loads .env from the calling agent's directory using python-dotenv.
Searches multiple paths to ensure .env is found regardless of how the agent is started.
"""

import os
import logging
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

logger = logging.getLogger(__name__)

# ── .env auto-discovery ───────────────────────────────────────────────────────
# Problem: pydantic-settings loads .env into its Settings object but does NOT
# export to os.environ. systemd may also start agents from / or /home/ubuntu.
# Solution: search multiple paths and load the first .env found.

_env_loaded = False
_env_path = None

try:
    from dotenv import load_dotenv

    # s3_utils/ can live in two locations:
    #   1. PROD_SETUP/s3_utils/           (local dev — .env is in sibling agent dirs)
    #   2. agent_folder/s3_utils/         (VM deploy — .env is in parent dir)
    _s3_utils_dir = Path(__file__).resolve().parent       # s3_utils/
    _parent_dir = _s3_utils_dir.parent                    # PROD_SETUP/ or agent_folder/

    _search_paths = [
        Path.cwd() / ".env",              # CWD (agent started from its own dir)
        _parent_dir / ".env",             # VM: agent_folder/.env (s3_utils is inside agent)
    ]

    # Walk up from s3_utils to find .env (covers any nesting depth)
    _p = _parent_dir
    for _ in range(5):
        _candidate = _p / ".env"
        if _candidate not in _search_paths:
            _search_paths.append(_candidate)
        _p = _p.parent

    # Also check known agent directory names as siblings of parent
    for _agent_dir in [
        "construction-intelligence-agent",
        "RAG_agent_VCS/RAG",
        "SQL-Intelligence-Agent",
        "INGESTION_for_RAG_agent",
        "document-qa-agent",
    ]:
        _candidate = _parent_dir / _agent_dir / ".env"
        if _candidate not in _search_paths:
            _search_paths.append(_candidate)

    for _p in _search_paths:
        if _p.exists():
            load_dotenv(_p, override=True)
            _env_loaded = True
            _env_path = str(_p)
            break

except ImportError:
    pass


@dataclass(frozen=True)
class S3Config:
    """Immutable S3 configuration loaded from environment."""

    bucket_name: str
    region: str
    access_key_id: str
    secret_access_key: str
    agent_prefix: str
    storage_backend: str
    endpoint_url: str = ""

    @property
    def is_s3_enabled(self) -> bool:
        return self.storage_backend.strip().lower() == "s3"

    @property
    def has_credentials(self) -> bool:
        return bool(self.access_key_id.strip() and self.secret_access_key.strip())


@lru_cache(maxsize=1)
def get_s3_config() -> S3Config:
    """Load S3 configuration from environment variables (cached)."""
    config = S3Config(
        bucket_name=os.getenv("S3_BUCKET_NAME", "").strip(),
        region=os.getenv("S3_REGION", "us-east-1").strip(),
        access_key_id=os.getenv("AWS_ACCESS_KEY_ID", "").strip(),
        secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY", "").strip(),
        agent_prefix=os.getenv("S3_AGENT_PREFIX", "").strip(),
        storage_backend=os.getenv("STORAGE_BACKEND", "local").strip(),
        endpoint_url=os.getenv("S3_ENDPOINT_URL", "").strip(),
    )
    return config


def verify_s3_connection() -> dict:
    """
    Test S3 connectivity and return diagnostic info.
    Call this at agent startup to catch config issues early.

    Returns dict with: connected, env_loaded, env_path, config, error
    """
    result = {
        "env_loaded": _env_loaded,
        "env_path": _env_path,
        "cwd": str(Path.cwd()),
    }

    config = get_s3_config()
    result["config"] = {
        "storage_backend": config.storage_backend,
        "is_s3_enabled": config.is_s3_enabled,
        "bucket_name": config.bucket_name,
        "region": config.region,
        "agent_prefix": config.agent_prefix,
        "has_credentials": config.has_credentials,
        "access_key_id": config.access_key_id[:8] + "..." if config.access_key_id else "(empty)",
    }

    if not config.is_s3_enabled:
        result["connected"] = False
        result["error"] = f"STORAGE_BACKEND='{config.storage_backend}' (not 's3')"
        return result

    if not config.has_credentials:
        result["connected"] = False
        result["error"] = "AWS credentials empty"
        return result

    if not config.bucket_name:
        result["connected"] = False
        result["error"] = "S3_BUCKET_NAME empty"
        return result

    # Actually test the connection
    try:
        from .client import get_s3_client
        get_s3_client.cache_clear()
        client = get_s3_client()
        if client is None:
            result["connected"] = False
            result["error"] = "get_s3_client() returned None"
        else:
            result["connected"] = True
            result["error"] = None
    except Exception as e:
        result["connected"] = False
        result["error"] = str(e)

    return result
