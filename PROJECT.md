# ZenSEO AI — Autonomous AI-Powered SEO Engine

## Vision

Build an autonomous SEO engine that learns from data, makes intelligent decisions using Reinforcement Learning, and drives real website growth — all managed from a single admin panel. The system thinks, decides, and acts on SEO like a tireless expert, continuously improving through PPO-based training.

## Problem

SEO is reactive, manual, and fragmented. Agencies juggle disconnected tools (Ahrefs, SEMrush, PageSpeed Insights, rank trackers), run manual audits, and guess at priorities. There's no system that:

- Continuously monitors websites across all SEO dimensions
- Learns from what works (and what doesn't)
- Makes data-driven decisions about what to fix next
- Executes improvements autonomously with safety guards
- Provides a single pane of glass for the entire operation

## Approach

### Architecture Philosophy

```
WordPress Plugin
    → API Gateway (FastAPI, torch-free)
        → ML Service (PyTorch, sentence-transformers, sklearn) [separate container]
            → PPO Trainer, Embeddings, LoRA, DBSCAN Clustering
        → Admin Dashboard (React + TypeScript)
            → Users, Websites, API Keys, ML Service control
            → Results, Backend Monitoring, AI Logs, Growth Engine
```

**Key design decisions:**

- **ML lives in its own container** — Backend is torch-free (~300MB), ML service carries all ML deps (~2.5GB). Fault isolation, independent scaling, hot-swappable.
- **PPO for continuous learning** — Not static rules. The system trains on real outcomes: what actions improved scores, what didn't, adapting its policy over time.
- **LoRA adapters per site** — Lightweight fine-tuning vectors per website, allowing personalization without full model retraining.
- **Confidence-gated execution** — Actions pass through thresholds before executing: HIGH (≥0.7) runs immediately, MEDIUM (≥0.4) needs monitoring, LOW (<0.4) is queued or blocked.
- **Docker-native deployment** — Single `docker compose up` for the full stack. CI/CD builds images on push, pushes to ghcr.io.

### What We've Built

#### Backend (FastAPI)
- **Auth**: JWT-based admin authentication with bearer tokens
- **Users CRUD**: Create, list, update, delete users with plan/subscription management, OpenRouter key field
- **Websites CRUD**: Create, list, update, delete websites per user, scan triggering
- **API Keys CRUD**: Generate (`zenseo_sk_*`) with rate limiting, revoke (soft-delete)
- **ML Service communication**: HTTP client to ml-service with API key auth, container lifecycle control (start/stop/restart/logs via Docker CLI)
- **Client Origin security**: Middleware checks Origin/Referer header against allowlist, HMAC signature support for non-browser access
- **Security**: All v1 endpoints protected with JWT auth, backend binds to 127.0.0.1

#### ML Service (PyTorch)
- **PPOTrainer**: Policy/value networks (199K params), GAE, KL early stopping, cosine annealing LR
- **6 SEO Environments**: TechnicalSEO, ContentSEO, KeywordResearch, Backlink, CWV, Schema
- **Embeddings**: sentence-transformers (all-MiniLM-L6-v2, 384-dim) with LRU cache
- **SemanticDB**: In-memory graph store with embedding similarity search
- **LoRA Adapters**: Low-rank adaptation per site, REINFORCE-style training
- **Cross-Site Analyzer**: DBSCAN clustering, pattern discovery, entity matching
- **Decision Engine**: LLM-based strategic decisions enriched with PPO policy confidence
- **Growth Engine**: Opportunity detection, priority scheduling, growth trajectory tracking

#### Admin Frontend (React + TypeScript)
- **Login**: JWT-based authentication with auto-redirect on 401
- **Management Page**: Tabbed interface (Users, Websites, API Keys, ML Service)
  - Each tab: stats cards, data table, inline create/edit/delete modals
  - ML tab: container lifecycle buttons, logs viewer, status cards
- **Growth Dashboard**: Growth trajectory, opportunities, scheduled actions
- **Other pages**: Results, Backend status, AI Logs
- **Security**: Protected routes, axios interceptors for auth headers and 401 handling

#### WordPress Plugin (`wp-plugin/`)
- PHP connector plugin for WordPress sites
- Collects site data and reports back to the API

#### Deployment
- `docker-compose.yml` — 5 services: postgres, redis, backend, ml-service, frontend
- `docker-compose.run.yml` — ghcr.io-based images with `platform: linux/amd64` for Apple Silicon
- `deploy.sh` — One-command deploy script for Ubuntu 24.04
- `.github/workflows/ci.yml` — GitHub Actions: tests → build → push to ghcr.io on push to main/master
- `Makefile` — Common commands: `deploy`, `up`, `down`, `test`, `smoke`, `seed`

### Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | React 18, TypeScript, Vite, TailwindCSS, React Router v6, Axios |
| Backend API | Python 3.12, FastAPI, SQLAlchemy 2.0, PostgreSQL 16, Redis 7 |
| ML | PyTorch 2.5, sentence-transformers, scikit-learn |
| Infrastructure | Docker, GitHub Actions (CI/CD), ghcr.io |
| Deployment | Ubuntu 24.04, Docker Compose, Nginx/Caddy (reverse proxy) |

### Current Status

**Ready:**
- Admin panel CRUD for users, websites, API keys
- JWT auth with 401 auto-redirect
- ML service container lifecycle from admin panel
- 6 RL environments with PPO trainer
- Embedding engine (sentence-transformers)
- LoRA adapters per website
- Cross-site pattern analysis
- Growth engine with opportunity detection
- CI/CD pipeline (test → build → push)
- One-command deploy script
- SSL/Origin-based security hardening

**In Progress:**
- Real database integration testing
- Alembic migrations
- Rate limit persistence
- Multi-worker safety
- Full SEO results pipeline end-to-end

### Project Structure

```
zenseo-ai-new/
├── admin/                    # React frontend (Vite)
│   ├── src/pages/           # 9 pages (Management, Growth, Results, etc.)
│   ├── src/hooks/           # useAuth, axios interceptors
│   └── Dockerfile
├── backend/                  # FastAPI backend
│   ├── app/api/v1/          # 11 route files (users, websites, api-keys, auth, ml, etc.)
│   ├── app/core/            # Config, auth, database, models, monitoring
│   ├── app/services/        # ML client, docker manager, trainers, learning pipeline
│   │   ├── atropos/         # PPO trainer, environments, scored data
│   │   ├── semantic/        # Embeddings, LoRA, cross-site, semantic DB
│   │   ├── learning/        # Data collector, reward calc, training pipeline, growth scorer
│   │   ├── growth/          # Growth tracker, opportunity detector, action scheduler
│   │   └── executor/        # Decision executor, action executor, safety monitor
│   ├── tests/               # 645 tests (core, executors, semantic, learning, growth)
│   └── Dockerfile
├── ml-service/               # ML-only container (PyTorch + deps)
│   ├── app/
│   └── Dockerfile
├── wp-plugin/                # WordPress connector plugin
├── docs/                     # Architecture docs
├── docker-compose.yml        # Local build config
├── docker-compose.run.yml    # ghcr.io image config
├── deploy.sh                 # Production deploy script
├── Makefile                  # Common commands
├── SPEC.md                   # Original specification
└── PROJECT.md                # This file
```

### Who This Is For

Agencies and SaaS operators managing multiple websites who need:

- A single dashboard to monitor all client sites
- Autonomous SEO that learns and adapts
- ML-powered insights without hiring a data science team
- Simple deployment (one Docker command)
- Complete control over their data and infrastructure

### Running

```bash
# Local development (no Docker)
make dev-backend   # FastAPI on :8000
make dev-frontend  # Vite on :3000

# Production deploy
SECRET_KEY=$(openssl rand -hex 32) \
  GITHUB_USER=devrahmanbd \
  GITHUB_TOKEN=ghp_xxx \
  bash deploy.sh

# Or build locally
make deploy

# Login: admin@zenseo.ai / admin123
```
