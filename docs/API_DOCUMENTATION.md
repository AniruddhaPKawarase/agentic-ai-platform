# Agentic AI Platform — API Documentation

## Overview

| Item | Value |
|------|-------|
| **Base URL** | `{{GATEWAY_URL}}` |
| **Protocol** | HTTPS (TLS 1.2/1.3), HTTP/2 |
| **Auth** | None (API keys planned for future) |
| **CORS** | Allowed from all origins |

### Agents Summary

| # | Agent | Port | URL Prefix | Description |
|---|-------|------|------------|-------------|
| 1 | RAG Agent | 8001 | `/rag/` | Construction documentation Q&A — RAG, Web, Hybrid search |
| 2 | SQL Intelligence Agent | 8002 | `/sql/` | Natural language to SQL — RFI queries |
| 3 | Construction Intelligence Agent | 8003 | `/construction/` | Scope/Exhibit document generation with trade analysis |
| 4 | Ingestion API | 8004 | `/ingestion/` | FAISS index ingestion pipeline (MongoDB + SQL to embeddings) |
| 5 | Gateway Health Service | 8005 | `/gateway/` | Unified health monitoring for all agents |
| 6 | Document Q&A Agent | 8006 | `/docqa/` | Upload documents and ask questions — per-session FAISS |

---

## Quick Start — Test All Agents

Run these commands to verify all agents are working:

```bash
# Gateway — check all agents at once
curl {{GATEWAY_URL}}/gateway/health

# Individual health checks
curl {{GATEWAY_URL}}/rag/health
curl {{GATEWAY_URL}}/sql/health
curl {{GATEWAY_URL}}/construction/health
curl {{GATEWAY_URL}}/ingestion/health
curl {{GATEWAY_URL}}/docqa/health
```

---

# 1. RAG Agent (`/rag/`)

**Purpose:** Answer questions about construction drawings and specifications using FAISS vector search, web search, or hybrid mode.

## 1.1 Health Check

```
GET /rag/health
```

**Test:**
```bash
curl {{GATEWAY_URL}}/rag/health
```

**Response:**
```json
{
  "status": "ok",
  "model": "gpt-4o",
  "retrieval_available": true,
  "web_search_available": true,
  "openai_available": true,
  "memory_available": true,
  "active_sessions": 0,
  "index_vectors": 125000,
  "metadata_records": 125000,
  "timestamp": "2026-03-24T07:54:34Z",
  "version": "2.0.0"
}
```

## 1.2 Query (RAG Search)

```
POST /rag/query
```

Ask a question about construction documents. Supports three search modes: `rag` (vector search), `web` (internet search), `hybrid` (both).

**Request Body:**
```json
{
  "query": "What plumbing materials are specified?",
  "search_mode": "rag",
  "project_id": 7201,
  "top_k": 5,
  "min_score": 0.1,
  "temperature": 0.0,
  "max_tokens": 500,
  "include_citations": false,
  "include_s3_paths": true,
  "session_id": null,
  "create_new_session": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | The question to ask |
| `search_mode` | string | No | `"rag"` | `rag`, `web`, or `hybrid` |
| `project_id` | int | No | null | Filter to specific project |
| `top_k` | int | No | 5 | Number of chunks to retrieve (1-20) |
| `min_score` | float | No | 0.1 | Minimum similarity score (0-1) |
| `temperature` | float | No | 0.0 | LLM temperature (0-1) |
| `max_tokens` | int | No | 500 | Max response tokens (50-4000) |
| `include_s3_paths` | bool | No | true | Include S3 download links in response |
| `filter_source_type` | string | No | null | `drawing`, `specification`, or `sql` |
| `session_id` | string | No | null | Existing session for conversation memory |
| `create_new_session` | bool | No | false | Create a new session automatically |

**Test:**
```bash
curl -X POST {{GATEWAY_URL}}/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What plumbing materials are specified?",
    "search_mode": "rag",
    "project_id": 7201,
    "top_k": 5
  }'
```

**Response:**
```json
{
  "query": "What plumbing materials are specified?",
  "answer": "Based on the construction documents...",
  "retrieval_count": 5,
  "average_score": 0.72,
  "confidence_score": 0.85,
  "is_clarification": false,
  "follow_up_questions": ["What pipe sizes are used?"],
  "model_used": "gpt-4o",
  "token_usage": {"prompt_tokens": 1200, "completion_tokens": 350, "total_tokens": 1550},
  "source_documents": [
    {
      "s3_path": "project-slug/Drawings/abc123",
      "file_name": "PlumbingPlans.pdf",
      "display_title": "Plumbing Plans Sheet P-1",
      "download_url": "https://..."
    }
  ],
  "processing_time_ms": 2300,
  "search_mode": "rag",
  "session_id": null
}
```

## 1.3 Query — Streaming (SSE)

```
POST /rag/query/stream
```

Same request body as `/rag/query`. Returns Server-Sent Events (SSE) for real-time streaming.

**Test:**
```bash
curl -N -X POST {{GATEWAY_URL}}/rag/query/stream \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What electrical systems are in the project?",
    "search_mode": "rag",
    "project_id": 7212
  }'
```

## 1.4 Quick Query

```
POST /rag/quick-query
```

Simplified query with fewer parameters.

**Request Body:**
```json
{
  "query": "Show me HVAC drawings",
  "search_mode": "rag",
  "project_id": 7222
}
```

## 1.5 Web Search

```
POST /rag/web-search
```

Search the internet for construction-related information.

**Request Body:**
```json
{
  "query": "Latest building code requirements for fire sprinklers 2026",
  "temperature": 0.0,
  "max_tokens": 1000
}
```

## 1.6 Session Management

### Create Session
```bash
curl -X POST {{GATEWAY_URL}}/rag/sessions/create \
  -H "Content-Type: application/json" \
  -d '{"project_id": 7201}'
```

### List Sessions
```bash
curl {{GATEWAY_URL}}/rag/sessions
```

### Get Session History
```bash
curl {{GATEWAY_URL}}/rag/sessions/{session_id}
```

### Delete Session
```bash
curl -X DELETE {{GATEWAY_URL}}/rag/sessions/{session_id}
```

---

# 2. SQL Intelligence Agent (`/sql/`)

**Purpose:** Convert natural language questions into SQL queries against the RFI database.

## 2.1 Health Check

```bash
curl {{GATEWAY_URL}}/sql/health
```

**Response:**
```json
{
  "status": "healthy",
  "database": "connected",
  "environment": "production"
}
```

## 2.2 RFI Query

```
POST /sql/api/rfi/query
```

Ask natural language questions about RFIs (Requests for Information).

**Request Body:**
```json
{
  "query": "How many open RFIs are there for project 7298?",
  "project_id": 7298,
  "use_cache": true,
  "session_id": null
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `query` | string | Yes | — | Natural language question about RFIs |
| `project_id` | int | No | null | Filter by project ID |
| `use_cache` | bool | No | true | Use cached results if available |
| `session_id` | string | No | null | Session for conversation continuity |

**Test:**
```bash
curl -X POST {{GATEWAY_URL}}/sql/api/rfi/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "How many open RFIs are there for project 7298?",
    "project_id": 7298
  }'
```

**Response:**
```json
{
  "success": true,
  "request_id": "abc-123-def",
  "data": {
    "summary": "There are 15 open RFIs for project 7298...",
    "count": 15,
    "list": [...]
  },
  "metadata": {
    "sql_generated": "SELECT ...",
    "execution_time_ms": 450
  }
}
```

## 2.3 RFI Health Check

```bash
curl {{GATEWAY_URL}}/sql/api/rfi/health
```

## 2.4 Performance Statistics

```bash
curl {{GATEWAY_URL}}/sql/api/statistics
```

## 2.5 Cache Invalidation

```bash
curl -X POST {{GATEWAY_URL}}/sql/api/cache/invalidate
```

---

# 3. Construction Intelligence Agent (`/construction/`)

**Purpose:** Generate scope gap analysis documents (Word .docx) by analyzing construction drawing data per trade.

## 3.1 Health Check

```bash
curl {{GATEWAY_URL}}/construction/health
```

**Response:**
```json
{
  "status": "ok",
  "redis": "in-memory-only",
  "openai": "configured"
}
```

## 3.2 Chat (Document Generation)

```
POST /construction/api/chat
```

Ask about a project's trade scope. The agent fetches drawing data, analyzes it, and generates a Word document.

**Request Body:**
```json
{
  "project_id": 7298,
  "query": "Generate scope gap analysis for Electrical trade",
  "session_id": null,
  "generate_document": true
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_id` | int | Yes | — | Project ID to analyze |
| `query` | string | Yes | — | What to analyze (include trade name) |
| `session_id` | string | No | null | Session for multi-turn conversation |
| `generate_document` | bool | No | true | Generate Word document |

**Test:**
```bash
curl -X POST {{GATEWAY_URL}}/construction/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "project_id": 7298,
    "query": "Generate scope gap analysis for Electrical trade",
    "generate_document": true
  }'
```

**Response:**
```json
{
  "session_id": "abc-123",
  "project_name": "Granville Hotel",
  "answer": "## Electrical Scope Gap Analysis\n\n...",
  "document": {
    "file_id": "scope_electrical_GranvilleHotel_7298_a1b2c3d4",
    "filename": "scope_electrical_GranvilleHotel_7298_a1b2c3d4.docx",
    "download_url": "{{GATEWAY_URL}}/construction/api/documents/.../download",
    "size_bytes": 45000,
    "trade": "Electrical",
    "document_type": "scope"
  },
  "intent": {
    "trade": "Electrical",
    "csi_divisions": ["26"],
    "document_type": "scope",
    "confidence": 0.95
  },
  "token_usage": {
    "input_tokens": 25000,
    "output_tokens": 8000,
    "total_tokens": 33000,
    "cost_usd": 0.023
  },
  "groundedness_score": 0.85,
  "needs_clarification": false,
  "follow_up_questions": ["What about the Plumbing trade?"],
  "pipeline_ms": 12000,
  "cached": false
}
```

## 3.3 Chat — Streaming (SSE)

```
POST /construction/api/chat/stream
```

Same request body as `/construction/api/chat`. Returns Server-Sent Events.

## 3.4 Download Generated Document

```
GET /construction/api/documents/{file_id}/download
```

## 3.5 Document Info

```
GET /construction/api/documents/{file_id}/info
```

## 3.6 Project Context

```
GET /construction/api/projects/{project_id}/context
```

Get available trades and CSI divisions for a project.

**Response:**
```json
{
  "project_id": 7298,
  "trades": ["Electrical", "Plumbing", "Mechanical", "Fire Protection"],
  "csi_divisions": ["22", "23", "26"],
  "total_text_items": 1306,
  "cached": false
}
```

## 3.7 Session Management

```bash
# Get conversation history
curl {{GATEWAY_URL}}/construction/api/sessions/{session_id}/history

# Get token usage
curl {{GATEWAY_URL}}/construction/api/sessions/{session_id}/tokens

# Delete session
curl -X DELETE {{GATEWAY_URL}}/construction/api/sessions/{session_id}
```

---

# 4. Ingestion API v2.0 (`/ingestion/`)

**Purpose:** Trigger and monitor FAISS index ingestion jobs with **incremental** and **full** modes. Processes MongoDB drawings/specifications and SQL Server metadata into vector embeddings.

### Key Features (v2.0)
- **Incremental mode:** Only embeds documents added/changed since the last successful ingestion
- **Full mode:** Deletes existing FAISS index and rebuilds from scratch
- **Cost estimation:** Shows estimated chunks, tokens, and cost before execution
- **Confirmation flow:** User must confirm after reviewing cost estimate
- **Per-project manifest:** Tracks `last_ingestion_timestamp` in S3 across runs
- **Scheduled ingestion:** Monthly cron with `skip_confirmation=true`

### Ingestion Flow Diagram
```
POST /api/ingest (mode: incremental|full)
  │
  ├── Phase 1: ESTIMATE (automatic)
  │     ├── Load manifest from S3 → get last_ingestion_timestamp
  │     ├── Count new/changed docs
  │     └── Return estimate (chunks, tokens, cost)
  │
  ├── Status: "awaiting_confirmation"
  │     └── User reviews estimate via GET /api/status/{job_id}
  │
  ├── POST /api/ingest/confirm/{job_id}  ← User confirms
  │
  └── Phase 2: EXECUTE
        ├── Full mode: delete old index → rebuild from scratch
        └── Incremental mode: load existing → append only new vectors
```

### Job Statuses

| Status | Meaning |
|--------|---------|
| `pending` | Job created |
| `estimating` | Counting new/changed documents, calculating cost |
| `awaiting_confirmation` | Estimate ready, waiting for user to confirm |
| `running` | Embedding and indexing in progress |
| `completed` | All projects processed successfully |
| `failed` | Error occurred |
| `cancelled` | User cancelled |
| `expired` | Not confirmed within 1 hour |

## 4.1 Health Check

```bash
curl {{GATEWAY_URL}}/ingestion/health
```

**Response:**
```json
{
  "status": "ok",
  "pipeline_available": true,
  "running_jobs": 0,
  "awaiting_confirmation": 0,
  "total_jobs": 0
}
```

## 4.2 Start Ingestion Job

```
POST /ingestion/api/ingest
```

**Request Body:**
```json
{
  "project_ids": [7277],
  "mode": "incremental",
  "skip_confirmation": false
}
```

| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `project_ids` | list[int] | Yes | — | Project IDs to ingest |
| `mode` | string | No | `"incremental"` | `"incremental"` or `"full"` |
| `skip_sample` | bool | No | false | Skip sample phase |
| `skip_confirmation` | bool | No | false | Skip cost estimate step (for cron/automated runs) |

**Response (immediate):**
```json
{
  "job_id": "eab141ab-5c9",
  "status": "estimating",
  "mode": "incremental",
  "message": "Ingestion job created. Estimating cost — check status for estimate.",
  "project_ids": [7277],
  "estimate": null
}
```

## 4.3 Check Job Status

```
GET /ingestion/api/status/{job_id}
```

Returns job status, progress, cost estimate (when available), and results.

## 4.4 Confirm Job

```
POST /ingestion/api/ingest/confirm/{job_id}
```

Confirm a job in `awaiting_confirmation` status to start execution.

## 4.5 List All Jobs

```bash
curl {{GATEWAY_URL}}/ingestion/api/jobs
```

## 4.6 Cancel Job

```bash
curl -X POST {{GATEWAY_URL}}/ingestion/api/cancel/{job_id}
```

### Decision: When to Use Which Mode

| Scenario | Mode | Why |
|----------|------|-----|
| Monthly data update | `incremental` | Fast, cheap — only processes changes |
| First-time indexing for a new project | `full` | No existing index to append to |
| Suspected stale/corrupt data | `full` | Clean rebuild ensures consistency |
| Chunking strategy changed | `full` | Old chunks incompatible |
| Embedding model changed | `full` | Old vectors have different dimensions |
| Routine monthly cron job | `incremental` + `skip_confirmation` | Auto-detects changes |

---

# 5. Document Q&A Agent (`/docqa/`)

**Purpose:** Upload any document (PDF, DOCX, XLSX, TXT, CSV, JSON) and ask questions about it. Each session gets its own FAISS index.

## 5.1 Health Check

```bash
curl {{GATEWAY_URL}}/docqa/health
```

**Response:**
```json
{
  "status": "ok",
  "model": "gpt-4o-mini",
  "embedding_model": "text-embedding-3-small",
  "active_sessions": 0,
  "total_indexed_vectors": 0,
  "max_file_size_mb": 20
}
```

## 5.2 Upload Files

```
POST /docqa/api/upload
```

Upload one or more files to create or add to a session.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `files` | file(s) | Yes | Up to 10 files, max 20MB each |
| `session_id` | string | No | Existing session (creates new if omitted) |

**Supported formats:** `.pdf`, `.docx`, `.xlsx`, `.xls`, `.txt`, `.csv`, `.json`

**Test:**
```bash
curl -X POST {{GATEWAY_URL}}/docqa/api/upload \
  -F "files=@/path/to/document.pdf"
```

**Response:**
```json
{
  "session_id": "sess-abc123",
  "files": [
    {
      "file_name": "document.pdf",
      "file_type": ".pdf",
      "size_bytes": 1234567,
      "chunk_count": 45,
      "status": "processed"
    }
  ],
  "total_chunks": 45,
  "message": "1 file(s) processed successfully"
}
```

## 5.3 Chat (Ask Questions)

```
POST /docqa/api/chat
```

**Request Body:**
```json
{
  "session_id": "sess-abc123",
  "query": "What are the main findings in this document?"
}
```

**Response:**
```json
{
  "session_id": "sess-abc123",
  "answer": "The document highlights three main findings...",
  "sources": [
    {
      "file_name": "document.pdf",
      "chunk_index": 12,
      "page_number": 3,
      "score": 0.89,
      "text_preview": "The key finding indicates that..."
    }
  ],
  "follow_up_questions": ["What evidence supports finding #1?"],
  "groundedness_score": 0.92,
  "needs_clarification": false,
  "token_usage": {
    "embedding_tokens": 50,
    "prompt_tokens": 3500,
    "completion_tokens": 600,
    "total_tokens": 4150,
    "estimated_cost_usd": 0.002
  },
  "pipeline_ms": {"retrieval_ms": 15, "llm_ms": 2100, "guard_ms": 5, "total_ms": 2120},
  "cached": false
}
```

## 5.4 Chat — Streaming (SSE)

```
POST /docqa/api/chat/stream
```

Same request body as `/docqa/api/chat`. Returns Server-Sent Events.

## 5.5 Converse (Upload + Query in One Request)

```
POST /docqa/api/converse
```

Upload files AND ask a question in a single request.

```bash
curl -X POST {{GATEWAY_URL}}/docqa/api/converse \
  -F "files=@/path/to/report.pdf" \
  -F "query=What are the key recommendations?" \
  -F "session_id=sess-abc123"
```

## 5.6 Converse — Streaming (SSE)

```
POST /docqa/api/converse/stream
```

Same as `/docqa/api/converse` but returns SSE stream.

## 5.7 Session Management

```bash
# List all sessions
curl {{GATEWAY_URL}}/docqa/api/sessions

# Get session detail
curl {{GATEWAY_URL}}/docqa/api/sessions/{session_id}

# List files in session
curl {{GATEWAY_URL}}/docqa/api/sessions/{session_id}/files

# Delete session
curl -X DELETE {{GATEWAY_URL}}/docqa/api/sessions/{session_id}
```

---

# 6. Gateway Health Service (`/gateway/`)

**Purpose:** Unified monitoring endpoint that checks the health of all agents.

## 6.1 Health (All Agents)

```bash
curl {{GATEWAY_URL}}/gateway/health
```

**Response:**
```json
{
  "status": "all_healthy",
  "healthy": 5,
  "total": 5,
  "timestamp": "2026-03-24T07:54:34Z",
  "agents": {
    "rag": "healthy",
    "sql": "healthy",
    "construction": "healthy",
    "ingestion": "healthy",
    "docqa": "healthy"
  },
  "details": [...]
}
```

| Status | Meaning |
|--------|---------|
| `all_healthy` | All agents responding normally |
| `degraded` | Some agents down or unhealthy |
| `all_down` | No agents responding |

## 6.2 Agent Registry

```bash
curl {{GATEWAY_URL}}/gateway/agents
```

Returns detailed info about each registered agent including port, prefix, description, and live status.

## 6.3 System Info

```bash
curl {{GATEWAY_URL}}/gateway/info
```

Returns gateway version, uptime, and agent port mapping.
