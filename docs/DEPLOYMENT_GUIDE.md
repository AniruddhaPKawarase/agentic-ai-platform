# Deployment Guide

## Prerequisites

- Ubuntu 22.04+ (recommended) or any Linux with systemd
- Python 3.12+
- Nginx 1.18+
- Git

## Clone the Platform

```bash
git clone --recurse-submodules https://github.com/AniruddhaPKawarase/agentic-ai-platform.git
cd agentic-ai-platform
```

## Agent Setup

Each agent is a git submodule in `agents/`. Set up each one:

### 1. RAG Engine (Port 8001)
```bash
cd agents/rag-engine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Edit with your credentials
```

### 2. SQL Engine (Port 8002)
```bash
cd agents/sql-engine
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 3. Doc Generator (Port 8003)
```bash
cd agents/doc-generator
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 4. Ingestion Pipeline (Port 8004)
```bash
cd agents/ingestion
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

### 5. Doc QA (Port 8006)
```bash
cd agents/doc-qa
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## Gateway Setup

### Install Nginx Config
```bash
sudo cp agents/gateway/nginx/vcs-agents.conf /etc/nginx/sites-available/
sudo ln -s /etc/nginx/sites-available/vcs-agents.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

### Install systemd Services
```bash
sudo cp agents/gateway/services/*.service /etc/systemd/system/
sudo systemctl daemon-reload
```

### Start All Services
```bash
sudo bash agents/gateway/scripts/start-all.sh
```

### Verify Health
```bash
curl http://localhost:8000/gateway/health
```

## SSL/TLS Setup

### Self-Signed (Testing)
```bash
sudo bash agents/gateway/scripts/setup-ssl-selfsigned.sh
```

### Let's Encrypt (Production)
```bash
sudo bash agents/gateway/scripts/setup-ssl-letsencrypt.sh
```

## Port Map

| Agent | Port | Route |
|-------|------|-------|
| Gateway (Nginx) | 8000 | Public entry |
| RAG Engine | 8001 | /rag/ |
| SQL Engine | 8002 | /sql/ |
| Doc Generator | 8003 | /construction/ |
| Ingestion Pipeline | 8004 | /ingestion/ |
| Health Service | 8005 | /gateway/ |
| Doc QA | 8006 | /docqa/ |
