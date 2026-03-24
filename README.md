# Agentic AI Platform

![Platform](https://img.shields.io/badge/Platform-Multi--Agent%20AI-blue?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=for-the-badge&logo=nginx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

Multi-agent AI platform orchestrating 5 specialized intelligence agents behind a unified API gateway. Each agent handles a distinct task -- retrieval-augmented generation, natural language SQL queries, intelligent document generation, data ingestion, and document Q&A -- communicating through a centralized Nginx reverse proxy with health monitoring.

---

## Architecture

```mermaid
graph TB
    subgraph Client Layer
        C[Client Applications]
    end

    subgraph Gateway Layer
        N[Nginx Reverse Proxy :8000]
        H[Health Aggregator :8005]
    end

    subgraph Agent Layer
        RAG[RAG Engine :8001]
        SQL[SQL Engine :8002]
        DOC[Doc Generator :8003]
        ING[Ingestion Pipeline :8004]
        QA[Doc QA :8006]
    end

    subgraph Data Layer
        FAISS[(FAISS Indexes)]
        SQLDB[(SQL Server)]
        MONGO[(MongoDB)]
        REDIS[(Redis Cache)]
        S3[(AWS S3)]
    end

    C --> N
    N -->|/rag/| RAG
    N -->|/sql/| SQL
    N -->|/doc/| DOC
    N -->|/ingest/| ING
    N -->|/gateway/| H
    N -->|/docqa/| QA

    H -.->|health polls| RAG
    H -.->|health polls| SQL
    H -.->|health polls| DOC
    H -.->|health polls| ING
    H -.->|health polls| QA

    RAG --> FAISS
    RAG --> S3
    SQL --> SQLDB
    DOC --> MONGO
    DOC --> REDIS
    ING --> FAISS
    ING --> MONGO
    QA --> FAISS
```

---

## Agents

| Agent | Repository | Port | Route | Description |
|-------|-----------|------|-------|-------------|
| RAG Engine | [agentic-rag-engine](https://github.com/AniruddhaPKawarase/agentic-rag-engine) | 8001 | `/rag/` | Retrieval-augmented generation with FAISS & hybrid search |
| SQL Engine | [agentic-sql-engine](https://github.com/AniruddhaPKawarase/agentic-sql-engine) | 8002 | `/sql/` | Natural language to SQL with domain specialists |
| Doc Generator | [agentic-doc-generator](https://github.com/AniruddhaPKawarase/agentic-doc-generator) | 8003 | `/doc/` | AI document generation with hallucination guard |
| Ingestion Pipeline | [agentic-ingestion-pipeline](https://github.com/AniruddhaPKawarase/agentic-ingestion-pipeline) | 8004 | `/ingest/` | Document chunking, embedding & FAISS indexing |
| Doc QA | [agentic-doc-qa](https://github.com/AniruddhaPKawarase/agentic-doc-qa) | 8006 | `/docqa/` | Conversational document Q&A with file upload |
| Gateway | [agentic-gateway](https://github.com/AniruddhaPKawarase/agentic-gateway) | 8000/8005 | -- | Nginx proxy, health aggregation, deploy scripts |

---

## One-Command Clone

```bash
git clone --recurse-submodules https://github.com/AniruddhaPKawarase/agentic-ai-platform.git
```

---

## Quick Start

1. **Clone with submodules:**
   ```bash
   git clone --recurse-submodules https://github.com/AniruddhaPKawarase/agentic-ai-platform.git
   cd agentic-ai-platform
   ```

2. **Set up each agent** (create virtualenv, install deps, configure `.env`):
   ```bash
   cd agents/rag-engine
   python -m venv venv && source venv/bin/activate
   pip install -r requirements.txt
   cp .env.example .env  # Edit with your credentials
   ```
   Repeat for each agent. See the [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) for full instructions.

3. **Configure and start the gateway:**
   ```bash
   sudo cp agents/gateway/nginx/vcs-agents.conf /etc/nginx/sites-available/
   sudo ln -s /etc/nginx/sites-available/vcs-agents.conf /etc/nginx/sites-enabled/
   sudo nginx -t && sudo systemctl reload nginx
   sudo bash agents/gateway/scripts/start-all.sh
   ```

4. **Verify everything is running:**
   ```bash
   curl http://localhost:8000/gateway/health
   ```

---

## Shared Utilities

### S3 Storage Module (`shared/s3_utils/`)

A shared Python package used by all agents for AWS S3 operations:

- **`config.py`** -- Environment-based S3 configuration with `.env` auto-discovery
- **`client.py`** -- Singleton boto3 client with connection pooling and retry logic
- **`operations.py`** -- Upload, download, list, delete, and presigned URL generation
- **`helpers.py`** -- Structured S3 key builders for each agent's data paths
- **`check_connection.py`** -- Diagnostic script to verify S3 connectivity

Toggle S3 storage per agent via `STORAGE_BACKEND=s3` in each `.env` file. Set `STORAGE_BACKEND=local` to fall back to local disk.

---

## Tech Stack

![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4o-412991?style=flat-square&logo=openai&logoColor=white)
![FAISS](https://img.shields.io/badge/FAISS-Vector%20Search-blue?style=flat-square)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![SQL Server](https://img.shields.io/badge/SQL%20Server-CC2927?style=flat-square&logo=microsoftsqlserver&logoColor=white)
![Redis](https://img.shields.io/badge/Redis-DC382D?style=flat-square&logo=redis&logoColor=white)
![AWS S3](https://img.shields.io/badge/AWS%20S3-569A31?style=flat-square&logo=amazons3&logoColor=white)
![Nginx](https://img.shields.io/badge/Nginx-009639?style=flat-square&logo=nginx&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![systemd](https://img.shields.io/badge/systemd-Service%20Manager-black?style=flat-square)
![Let's Encrypt](https://img.shields.io/badge/Let's%20Encrypt-003A70?style=flat-square&logo=letsencrypt&logoColor=white)

---

## Documentation

| Document | Description |
|----------|-------------|
| [System Design](docs/SYSTEM_DESIGN.md) | Architecture decisions, options analysis, phase roadmap |
| [API Documentation](docs/API_DOCUMENTATION.md) | Complete API reference for all 6 agents |
| [Deployment Guide](docs/DEPLOYMENT_GUIDE.md) | Step-by-step setup on Ubuntu with Nginx and systemd |

---

## Project Structure

```
agentic-ai-platform/
├── agents/
│   ├── rag-engine/          # Submodule → agentic-rag-engine
│   ├── sql-engine/          # Submodule → agentic-sql-engine
│   ├── doc-generator/       # Submodule → agentic-doc-generator
│   ├── ingestion/           # Submodule → agentic-ingestion-pipeline
│   ├── doc-qa/              # Submodule → agentic-doc-qa
│   └── gateway/             # Submodule → agentic-gateway
│       ├── nginx/
│       │   └── vcs-agents.conf
│       ├── services/
│       │   └── *.service
│       ├── scripts/
│       │   └── *.sh
│       └── health_service/
│           └── main.py
├── shared/
│   └── s3_utils/
│       ├── __init__.py
│       ├── config.py
│       ├── client.py
│       ├── operations.py
│       ├── helpers.py
│       └── check_connection.py
├── docs/
│   ├── SYSTEM_DESIGN.md
│   ├── API_DOCUMENTATION.md
│   └── DEPLOYMENT_GUIDE.md
├── docker-compose.yml
├── .gitignore
├── LICENSE
└── README.md
```

---

## License

MIT -- see [LICENSE](LICENSE) for details.
