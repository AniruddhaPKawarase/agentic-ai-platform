# SYSTEM DESIGN: Unified API Gateway for Agentic AI Platform

## Document Version: 1.0 | Date: 2026-03-10

---

## TABLE OF CONTENTS

1. [Current Problem](#1-current-problem)
2. [Solution Overview](#2-solution-overview)
3. [Architecture Options — Pros & Cons](#3-architecture-options--pros--cons)
4. [Recommended Architecture](#4-recommended-architecture--nginx-reverse-proxy)
5. [Complete API Mapping](#5-complete-api-mapping)
6. [How Adding a New Agent Works](#6-how-adding-a-new-agent-works)
7. [Phase-by-Phase Development Roadmap](#7-phase-by-phase-development-roadmap)
8. [Risk Assessment](#8-risk-assessment)
9. [Final Checklist Before Go-Live](#9-final-checklist-before-go-live)

---

## 1. CURRENT PROBLEM

```
TODAY (Broken):

  VM (single machine)
    Port 8000 ──── RAG Agent         ← Running
    Port 8000 ──── SQL Agent         ← CANNOT run (port taken)
    Port 8000 ──── Construction Agent← CANNOT run (port taken)
    No port  ──── Ingestion Pipeline ← CLI only, no API

  Result: Only 1 agent runs at a time.
  Webapp can only talk to 1 agent.
```

**What we have:**

| Agent | Type | Port | Status |
|-------|------|------|--------|
| RAG Agent | FastAPI Web API | 8000 | Works alone |
| SQL Agent | FastAPI Web API | 8000 | Works alone |
| Construction Agent | FastAPI Web API | 8000 | Works alone |
| Ingestion Pipeline | CLI Script | None | Works alone |

**The conflict:** All 3 web agents try to use port 8000. Only one can run at a time. The webapp UI needs to talk to ALL agents through ONE address.

---

## 2. SOLUTION OVERVIEW

```
AFTER (Working):

  Webapp UI (browser)
       |
       | All requests go to port 8000
       v
  ┌─────────────────────────────────────────┐
  │         NGINX REVERSE PROXY             │
  │         (Port 8000 — public)            │
  │                                         │
  │  /rag/*          → localhost:8001       │
  │  /sql/*          → localhost:8002       │
  │  /construction/* → localhost:8003       │
  │  /ingestion/*    → localhost:8004       │
  │  /gateway/*      → localhost:8005       │
  └─────────────────────────────────────────┘
       |         |         |         |
       v         v         v         v
   ┌───────┐ ┌───────┐ ┌───────┐ ┌───────┐
   │ RAG   │ │ SQL   │ │Constr.│ │Ingest.│
   │ Agent │ │ Agent │ │ Agent │ │  API  │
   │ :8001 │ │ :8002 │ │ :8003 │ │ :8004 │
   └───────┘ └───────┘ └───────┘ └───────┘

  Each agent runs as its own process.
  Each agent keeps its own code 100% untouched.
  Nginx routes requests by URL prefix.
```

**How the webapp calls each agent:**

| What you want | URL your webapp calls |
|---------------|----------------------|
| Ask RAG agent a question | `{{GATEWAY_URL}}/rag/query` |
| Ask SQL agent about RFIs | `{{GATEWAY_URL}}/sql/api/rfi/query` |
| Generate a scope document | `{{GATEWAY_URL}}/construction/api/chat` |
| Start data ingestion | `{{GATEWAY_URL}}/ingestion/api/ingest` |
| Check all agents health | `{{GATEWAY_URL}}/gateway/health` |

---

## 3. ARCHITECTURE OPTIONS — PROS & CONS

### OPTION A: Nginx Reverse Proxy (RECOMMENDED)

**How it works:** Nginx (a fast web server) sits on port 8000. Each agent runs on a different internal port. Nginx reads the URL and sends the request to the right agent.

| PROS | CONS |
|------|------|
| Zero code changes to any agent | Need to install Nginx on VM |
| If one agent crashes, others keep working | Need to manage multiple processes |
| Can restart/update one agent without stopping others | Slightly more setup effort initially |
| Battle-tested (used by Netflix, Uber, Airbnb) | Need a process manager (systemd) |
| Extremely fast (adds <1ms delay) | Nginx config file to maintain |
| Adding new agent = 2 lines in config | — |
| Each agent can be tested independently | — |
| Handles 10,000+ requests/second easily | — |

**Verdict: Best for production. Zero risk to existing agents.**

---

### OPTION B: FastAPI Gateway (Python Proxy)

**How it works:** A Python FastAPI app sits on port 8000 and forwards requests to agents using httpx (HTTP library).

| PROS | CONS |
|------|------|
| All Python, no external tools | Gateway itself can crash (single point of failure) |
| Can add auth/logging in Python | Adds 5-20ms delay per request (Python overhead) |
| Easier to understand for Python devs | Still needs multiple processes for agents |
| — | More code to write and maintain |
| — | Python GIL limits throughput |
| — | Gateway bugs can break ALL agents |

**Verdict: Acceptable but slower and riskier than Nginx.**

---

### OPTION C: FastAPI Sub-Application Mount (Single Process)

**How it works:** One Python process imports all 3 agents' code and runs them together.

| PROS | CONS |
|------|------|
| Single process, simplest deployment | If one agent crashes, ALL agents crash |
| No Nginx needed | Cannot update one agent without restarting ALL |
| Shared memory (efficient) | Memory leak in one agent kills everything |
| — | CORS/middleware conflicts between agents |
| — | Startup order problems |
| — | Cannot test agents independently |
| — | Python GIL = poor concurrency |
| — | Requires code changes to all agents |

**Verdict: NOT recommended for production. Too risky.**

---

### COMPARISON TABLE

| Criteria | Option A (Nginx) | Option B (Python) | Option C (Mount) |
|----------|-----------------|-------------------|------------------|
| Agent isolation | Complete | Complete | None |
| Code changes needed | None | None | Major |
| Added latency | <1ms | 5-20ms | 0ms |
| Can update 1 agent alone | Yes | Yes | No |
| Crash containment | Yes | Partial | No |
| Scalability | Excellent | Good | Poor |
| Production readiness | High | Medium | Low |
| Setup complexity | Medium | Medium | Low |
| **RECOMMENDATION** | **YES** | Maybe | No |

---

## 4. RECOMMENDED ARCHITECTURE — Nginx Reverse Proxy

### 4.1 Complete System Diagram

```
                    ┌──────────────────────┐
                    │   WEBAPP UI (Browser) │
                    └──────────┬───────────┘
                               │
                    Port 8000 (public)
                               │
                ┌──────────────▼──────────────┐
                │     NGINX REVERSE PROXY      │
                │                              │
                │  URL Routing Rules:          │
                │  /rag/*          → :8001     │
                │  /sql/*          → :8002     │
                │  /construction/* → :8003     │
                │  /ingestion/*    → :8004     │
                │  /gateway/*      → :8005     │
                │  /docqa/*        → :8006     │
                └──┬───────┬───────┬───────┬──┘
                   │       │       │       │
         ┌─────────▼─┐ ┌──▼────┐ ┌▼──────┐ ┌▼────────┐
         │ RAG Agent  │ │ SQL   │ │Constr.│ │Ingestion│
         │            │ │ Agent │ │ Agent │ │   API   │
         │ Port: 8001 │ │ :8002 │ │ :8003 │ │  :8004  │
         │            │ │       │ │       │ │         │
         │ FAISS      │ │SQL DB │ │Mongo  │ │Mongo+SQL│
         │ OpenAI     │ │OpenAI │ │Redis  │ │OpenAI   │
         │ Sessions   │ │Cache  │ │OpenAI │ │FAISS    │
         └────────────┘ └───────┘ └───────┘ └─────────┘

         ┌──────────┐  ┌──────────┐
         │ Gateway   │  │ Doc QA   │
         │ Service   │  │ Agent    │
         │ Port:8005 │  │ Port:8006│
         └──────────┘  └──────────┘
```

### 4.2 How Nginx Routes Requests (Simple Explanation)

When the webapp sends: `{{GATEWAY_URL}}/rag/query`

```
Step 1: Request arrives at Nginx (port 8000)
Step 2: Nginx sees URL starts with "/rag/"
Step 3: Nginx strips "/rag" prefix
Step 4: Nginx forwards "/query" to localhost:8001
Step 5: RAG Agent receives "/query" (exactly as it expects)
Step 6: RAG Agent responds
Step 7: Nginx sends response back to webapp
```

**The agent never knows Nginx exists.** It receives the same URLs it always did. Zero code changes.

### 4.3 Port Assignment Table

| Agent | Internal Port | Env Variable | URL Prefix | Status |
|-------|--------------|-------------|------------|--------|
| RAG Agent | 8001 | `PORT=8001` | `/rag/` | Active |
| SQL Agent | 8002 | `API_PORT=8002` | `/sql/` | Active |
| Construction Agent | 8003 | `APP_PORT=8003` | `/construction/` | Active |
| Ingestion API | 8004 | `INGEST_PORT=8004` | `/ingestion/` | Active |
| Gateway Service | 8005 | `GATEWAY_PORT=8005` | `/gateway/` | Active |
| Document QA | 8006 | `DOCQA_PORT=8006` | `/docqa/` | Active |

### 4.4 Process Management (systemd)

Each agent runs as a Linux system service:

```
systemctl start rag-agent           ← Start RAG agent
systemctl stop sql-agent            ← Stop SQL agent
systemctl restart construction-agent ← Restart construction agent
systemctl status rag-agent          ← Check if running
```

**Benefits:**
- Auto-restart on crash
- Start on VM boot
- Log management built-in
- Independent control per agent

---

## 5. COMPLETE API MAPPING

### 5.1 RAG Agent APIs (prefix: `/rag`)

| Webapp calls | Agent receives | Method | Purpose |
|-------------|---------------|--------|---------|
| `/rag/query` | `/query` | POST | Ask a question (RAG/Web/Hybrid) |
| `/rag/query/stream` | `/query/stream` | POST | Streaming answer (SSE) |
| `/rag/quick-query` | `/quick-query` | POST | Simplified UI query |
| `/rag/web-search` | `/web-search` | POST | Web search only |
| `/rag/sessions/create` | `/sessions/create` | POST | Create session |
| `/rag/sessions` | `/sessions` | GET | List sessions |
| `/rag/sessions/{id}/stats` | `/sessions/{id}/stats` | GET | Session stats |
| `/rag/sessions/{id}/conversation` | `/sessions/{id}/conversation` | GET | Full history |
| `/rag/sessions/{id}/update` | `/sessions/{id}/update` | POST | Update context |
| `/rag/sessions/{id}` | `/sessions/{id}` | DELETE | Delete session |
| `/rag/health` | `/health` | GET | Health check |
| `/rag/config` | `/config` | GET | Configuration |

### 5.2 SQL Agent APIs (prefix: `/sql`)

| Webapp calls | Agent receives | Method | Purpose |
|-------------|---------------|--------|---------|
| `/sql/api/rfi/query` | `/api/rfi/query` | POST | RFI natural language query |
| `/sql/api/rfi/health` | `/api/rfi/health` | GET | RFI domain health |
| `/sql/api/submittal/query` | `/api/submittal/query` | POST | Submittal query (future) |
| `/sql/api/bim/query` | `/api/bim/query` | POST | BIM query (future) |
| `/sql/api/statistics` | `/api/statistics` | GET | Performance stats |
| `/sql/api/cache/invalidate` | `/api/cache/invalidate` | POST | Clear caches |
| `/sql/health` | `/health` | GET | Health check |

### 5.3 Construction Agent APIs (prefix: `/construction`)

| Webapp calls | Agent receives | Method | Purpose |
|-------------|---------------|--------|---------|
| `/construction/api/chat` | `/api/chat` | POST | Main chat pipeline |
| `/construction/api/chat/stream` | `/api/chat/stream` | POST | Streaming chat (SSE) |
| `/construction/api/sessions/{id}/history` | `/api/sessions/{id}/history` | GET | Conversation history |
| `/construction/api/sessions/{id}/tokens` | `/api/sessions/{id}/tokens` | GET | Token usage |
| `/construction/api/sessions/{id}` | `/api/sessions/{id}` | DELETE | Clear session |
| `/construction/api/projects/{id}/context` | `/api/projects/{id}/context` | GET | Project context |
| `/construction/api/documents/{id}/download` | `/api/documents/{id}/download` | GET | Download Word doc |
| `/construction/api/documents/{id}/info` | `/api/documents/{id}/info` | GET | Document info |
| `/construction/health` | `/health` | GET | Health check |

### 5.4 Ingestion API (prefix: `/ingestion`)

| Webapp calls | Method | Purpose |
|-------------|--------|---------|
| `/ingestion/api/ingest` | POST | Start ingestion for project(s) |
| `/ingestion/api/ingest/confirm/{job_id}` | POST | Confirm job after cost estimate |
| `/ingestion/api/status/{job_id}` | GET | Check ingestion progress |
| `/ingestion/api/jobs` | GET | List all ingestion jobs |
| `/ingestion/api/cancel/{job_id}` | POST | Cancel running job |
| `/ingestion/health` | GET | Health check |

### 5.5 Document QA APIs (prefix: `/docqa`)

| Webapp calls | Method | Purpose |
|-------------|--------|---------|
| `/docqa/api/upload` | POST | Upload documents to session |
| `/docqa/api/chat` | POST | Ask questions about documents |
| `/docqa/api/chat/stream` | POST | Streaming Q&A (SSE) |
| `/docqa/api/converse` | POST | Upload + query in one request |
| `/docqa/api/converse/stream` | POST | Upload + query streaming |
| `/docqa/api/sessions` | GET | List all sessions |
| `/docqa/api/sessions/{id}` | GET | Session detail |
| `/docqa/api/sessions/{id}/files` | GET | Files in session |
| `/docqa/api/sessions/{id}` | DELETE | Delete session |
| `/docqa/health` | GET | Health check |

### 5.6 Gateway APIs (prefix: `/gateway`)

| Webapp calls | Method | Purpose |
|-------------|--------|---------|
| `/gateway/health` | GET | All agents health summary |
| `/gateway/agents` | GET | List registered agents + status |
| `/gateway/info` | GET | System info (version, uptime) |

---

## 6. HOW ADDING A NEW AGENT WORKS

### Example: Adding a "Safety Compliance Agent" (future)

**Step 1:** Create agent repository and assign port
```
Safety Agent → Port 8007 → Prefix /safety/
```

**Step 2:** Create systemd service file
```
Copy existing service template → change name, port, paths
```

**Step 3:** Add 5 lines to Nginx config
```nginx
location /safety/ {
    proxy_pass http://127.0.0.1:8007/;
}
```

**Step 4:** Reload Nginx
```
sudo nginx -s reload
```

**Done.** Zero changes to any existing agent. The new agent is live at `/safety/*`.

**Time required:** 10-15 minutes for an experienced developer.

---

## 7. PHASE-BY-PHASE DEVELOPMENT ROADMAP

### Overview

```
Phase 1: Gateway Foundation        ← Core infrastructure (Nginx + services)
   ↓
Phase 2: Agent Port Configuration  ← Make each agent use its own port
   ↓
Phase 3: Ingestion API Wrapper     ← Wrap CLI pipeline as HTTP API
   ↓
Phase 4: Gateway Health Service    ← Unified health monitoring
   ↓
Phase 5: Management Scripts        ← Start/stop/restart all agents easily
   ↓
Phase 6: Production Hardening      ← SSL, logging, auto-restart, monitoring
```

---

### PHASE 1: Gateway Foundation (Nginx Setup)

**Goal:** Install and configure Nginx as the single entry point on port 8000.

**Deliverable:** Nginx running on port 8000, configured to route to internal ports.

**Risk:** Low — Nginx is rock-solid, used by 30% of all websites.

---

### PHASE 2: Agent Port Configuration

**Goal:** Configure each agent to run on its own dedicated internal port.

**Changes:** Only `.env` file changes — zero code modifications.

**Risk:** Very low — only `.env` file changes, zero code changes.

---

### PHASE 3: Ingestion API Wrapper

**Goal:** Wrap the CLI-only ingestion pipeline as an HTTP API so the webapp can trigger ingestion jobs.

**Deliverable:** Ingestion pipeline accessible via `/ingestion/api/*` endpoints.

**Risk:** Medium — new code, but only wraps existing tested pipeline.

---

### PHASE 4: Gateway Health Service

**Goal:** A lightweight service that monitors all agents and provides a unified health dashboard.

**Deliverable:** Single URL (`/gateway/health`) shows health of entire system.

**Risk:** Low — read-only monitoring, cannot break any agent.

---

### PHASE 5: Management Scripts

**Goal:** Simple shell scripts so anyone can manage all agents.

**Deliverable:** Run `./start-all.sh` and everything comes up. Run `./status.sh` and see all agents.

---

### PHASE 6: Production Hardening

**Goal:** Make the system production-ready with security, monitoring, and reliability.

**Steps:**
1. SSL/HTTPS with Let's Encrypt
2. Rate limiting per endpoint
3. Unified access logging
4. Custom error pages for 502/503/504
5. Auto-restart on all services
6. Log rotation
7. Monitoring
8. Backup scripts
9. Firewall (only expose port 8000 and 22)

---

## 8. RISK ASSESSMENT

### What Can Go Wrong & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|------------|
| Nginx crash | Very Low | High (all agents unreachable) | systemd auto-restart, Nginx is extremely stable |
| One agent crash | Low | Low (only that agent down) | systemd auto-restart, other agents unaffected |
| Port conflict | Very Low | Medium | Port table documented, tested in Phase 2 |
| Streaming (SSE) issues through Nginx | Medium | Medium | Special Nginx config (proxy_buffering off) |
| Memory exhaustion on VM | Low | High | Monitor per-agent memory, set limits |
| Ingestion API blocks other agents | Very Low | None | Separate process, separate port |
| Agent update breaks gateway | Very Low | None | Gateway doesn't touch agent code |

### What This Architecture Guarantees

1. **Agent A crashes -> Agent B keeps working.** (Process isolation)
2. **Update Agent A -> Agent B and C are not affected.** (Independent deployment)
3. **Add Agent D -> Zero changes to A, B, C.** (Plug-in architecture)
4. **Webapp only talks to port 8000.** (Single entry point)
5. **Each agent can be tested on its own port.** (Independent testing)

---

## 9. FINAL CHECKLIST BEFORE GO-LIVE

### Pre-Deployment

- [ ] All agents tested individually on their assigned ports
- [ ] Nginx installed and configured
- [ ] All routes verified through Nginx (prefix stripping works)
- [ ] SSE/streaming endpoints verified through Nginx
- [ ] systemd services created and tested
- [ ] Auto-restart verified (kill agent, confirm it comes back)
- [ ] start-all.sh and stop-all.sh scripts tested
- [ ] Firewall configured (only port 8000 and 22 exposed)
- [ ] Gateway health endpoint shows all agents green
- [ ] Webapp UI integration tested with new URL prefixes

### Post-Deployment Monitoring

- [ ] All agents responding to health checks
- [ ] Logs being written and rotated
- [ ] Memory usage stable over 24 hours
- [ ] No error spikes in Nginx access logs
