# ZenSEO AI — System Architecture

An autonomous AI-powered SEO engine that learns from data, drives website growth, and makes intelligent decisions using Reinforcement Learning.

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         WordPress Plugin                                 │
│  (Connector: collects data, applies fixes, reports results)              │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │ HTTPS / WebSocket
┌────────────────────────────▼─────────────────────────────────────────────┐
│                         API Gateway (FastAPI)                            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────────┐ │
│  │ Auth     │ │ Admin    │ │ REPL     │ │ Growth   │ │ Policy        │ │
│  │ (JWT)    │ │ CRUD     │ │ (WS)     │ │ Dashboard│ │ Inference     │ │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └───────────────┘ │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                      Learning from Data Pipeline                         │
│                                                                          │
│  ┌────────────┐  ┌──────────────┐  ┌───────────────┐  ┌──────────────┐ │
│  │ Data       │→ │ Reward       │→ │ ScoredData    │→ │ PPO Trainer  │ │
│  │ Collector  │  │ Calculator   │  │ Buffer        │  │ (PyTorch)    │ │
│  └────────────┘  └──────────────┘  └───────────────┘  └──────┬───────┘ │
│                                                              │          │
│  ┌────────────┐  ┌──────────────┐                            │          │
│  │ Feedback   │← │ Training     │←────────────────────────────          │
│  │ Loop       │  │ Pipeline     │                                        │
│  └────────────┘  └──────────────┘                                        │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                     Decision Engine Layer                                │
│                                                                          │
│  ┌─────────────────┐  ┌─────────────────┐  ┌──────────────────────────┐ │
│  │ Decision        │  │ Decision        │  │ Growth                   │ │
│  │ Engine (LLM)    │←─┤ Integrator      │←─┤ Scorer                   │ │
│  │                 │  │ (PPO + LLM)     │  │ (Velocity, Trend,        │ │
│  └─────────────────┘  └─────────────────┘  │  Effectiveness)           │ │
│                                             └──────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                      Website Growth Engine                               │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │ Growth           │  │ Opportunity      │  │ Action                 │ │
│  │ Tracker          │→│ Detector         │→│ Scheduler              │ │
│  │ (Trends,         │  │ (PPO + Cross-    │  │ (Priority, Dedup,      │ │
│  │  Interventions)  │  │  site + Heuristic)│  │  Timeline)             │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │
└────────────────────────────┬─────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                      Execution Layer                                     │
│                                                                          │
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────────────────┐ │
│  │ Decision         │→ │ Action           │→ │ Safety                 │ │
│  │ Executor         │  │ Executor         │  │ Monitor                │ │
│  │ (Confidence      │  │ (Environment     │  │ (Rate Limits,          │ │
│  │  Gating)         │  │  Dispatch)       │  │  Circuit Breaker)      │ │
│  └──────────────────┘  └──────────────────┘  └────────────────────────┘ │
│                                    │                                      │
│                                    ▼                                      │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                      SEO Environments                                │ │
│  │  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐            │ │
│  │  │Tech  │ │Content│ │Keyword│ │Back- │ │CWV   │ │Schema│            │ │
│  │  │SEO   │ │SEO   │ │Search │ │link  │ │Env   │ │Env   │            │ │
│  │  └──────┘ └──────┘ └──────┘ └──────┘ └──────┘ └──────┘            │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
                             │
┌────────────────────────────▼─────────────────────────────────────────────┐
│                      Semantic Layer                                      │
│                                                                          │
│  ┌────────────────┐  ┌────────────────┐  ┌────────────────────────────┐ │
│  │ Semantic DB    │  │ LoRA Adapter   │  │ Cross-Site Analyzer        │ │
│  │ (Vector +      │  │ (Low-Rank      │  │ (DBSCAN Clustering,        │ │
│  │  Graph Store)  │  │  Adaptation)   │  │  Pattern Discovery)        │ │
│  └────────────────┘  └────────────────┘  └────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────────────┘
```

---

## Component Descriptions

### Phase 1: Foundation — PPO Trainer & Embedding Engine

| Component | File | Purpose |
|-----------|------|---------|
| **PPOTrainer** | `backend/app/services/atropos/trainer.py` | PyTorch-based PPO implementation with policy/value networks, GAE, KL early stopping, cosine annealing LR scheduler. 199K parameters (configurable). |
| **ScoredDataBuffer** | `backend/app/services/atropos/scored_data_api.py` | Thread-safe ring buffer (max 10K) for RL trajectory storage. |
| **SEO Environments** | `backend/app/services/atropos/environments/` | 6 RL environments: TechnicalSEO, ContentSEO, KeywordResearch, Backlink, CWV, Schema. Each implements reset/step/render. |
| **Embedding Engine** | `backend/app/services/semantic/embeddings.py` | sentence-transformers (all-MiniLM-L6-v2, 384-dim) with LRU cache + hash-based fallback. |
| **Environment Registry** | `backend/app/services/atropos/base_env.py` | Registry pattern for creating environments by name. |

### Phase 2: Semantic Layer Production Hardening

| Component | File | Purpose |
|-----------|------|---------|
| **SemanticDB** | `backend/app/services/semantic/db.py` | In-memory graph store with embedding-based similarity search, topic vectors, cross-site queries. |
| **LoRASemanticAdapter** | `backend/app/services/semantic/lora.py` | Low-rank adaptation module (PyTorch nn.Module) with trainable A/B matrices per site. REINFORCE-style training from rewards. |
| **CrossSiteAnalyzer** | `backend/app/services/semantic/cross_site.py` | DBSCAN-based site clustering, embedding-based entity matching, action sequence fingerprinting. |
| **Pattern Detection** | `backend/app/services/semantic/cross_site.py` | Cross-site pattern discovery with deduplication and similarity thresholds. |

### Phase 3: Learning from Data

| Component | File | Purpose |
|-----------|------|---------|
| **DataCollector** | `backend/app/services/learning/data_collector.py` | Transforms DB records (SEOResults, Tasks, AgentLogs) into (state, action, reward, next_state) trajectories. |
| **RewardCalculator** | `backend/app/services/learning/reward_calculator.py` | Computes reward signals from score deltas, issue reductions, task success/failure. Normalized to [-1, 1]. |
| **TrainingPipeline** | `backend/app/services/learning/training_pipeline.py` | Continuous feedback loop: collect → transform → buffer → train → persist. Cancellable background auto-training. |
| **FeedbackLoop** | `backend/app/services/learning/feedback_loop.py` | Real-time event handlers: on_scan_complete, on_task_complete, on_website_update. Builds single-step trajectories. |
| **DecisionIntegrator** | `backend/app/services/learning/decision_integrator.py` | Bridges PPO policy to DecisionEngine. Recommends actions, scores confidence, enriches LLM decisions with data-driven insights. |
| **GrowthScorer** | `backend/app/services/learning/growth_scorer.py` | Scores website growth trajectory (velocity, consistency, comparative rank, action effectiveness). Predicts growth outcomes. |
| **DecisionEngine** | `core/agents/decision_engine.py` | LLM-based strategic decision engine with 4-phase flow: diagnose → analyze competition → identify opportunities → decide. Now enriched with PPO policy. |

### Phase 4: Website Growth Engine

| Component | File | Purpose |
|-----------|------|---------|
| **GrowthTracker** | `backend/app/services/growth/growth_tracker.py` | Monitors website growth in real-time. Detects plateaus (threshold 0.2), triggers interventions. |
| **OpportunityDetector** | `backend/app/services/growth/opportunity_detector.py` | 3-source detection: PPO policy (high confidence), cross-site patterns (medium), heuristics (low). |
| **ActionScheduler** | `backend/app/services/growth/action_scheduler.py` | Priority-based scheduling: `reward * confidence * effort_penalty * urgency_boost`. Dedup and max-actions enforcement. |
| **Growth Dashboard API** | `backend/app/api/v1/growth.py` | 6 REST endpoints exposing growth state, comparisons, opportunities, scheduled actions. |
| **Growth Frontend** | `admin/src/pages/GrowthPage.tsx` | React dashboard with growth overview cards, trajectory charts, opportunity list, action timeline. |

### Phase 5: Production Hardening

| Component | File | Purpose |
|-----------|------|---------|
| **DecisionExecutor** | `backend/app/services/executor/decision_executor.py` | Confidence-gated execution: HIGH(≥0.7)=immediate, MEDIUM(≥0.4)=monitored, LOW(<0.4)=blocked/queue. Integrates with FeedbackLoop. |
| **ActionExecutor** | `backend/app/services/executor/action_executor.py` | Maps 31 action types to 6 SEO environments. Executes via Registry-created env instances. |
| **SafetyMonitor** | `backend/app/services/executor/safety_monitor.py` | Per-site rate limiting, circuit breaker (5 failures → 300s timeout), dangerous action confirmation. |
| **MetricsCollector** | `backend/app/core/monitoring.py` | Thread-safe operational metrics: training runs, executions, API calls, health checks. |
| **ConfigProvider** | `backend/app/core/config_provider.py` | Pydantic-based hierarchical config: defaults → env vars → overrides. Nested Learning/Execution configs. |
| **PolicyServer** | `backend/app/services/learning/policy_server.py` | Serves trained policy for inference: recommendations, policy info, model reload. |
| **Startup Verification** | `backend/app/core/startup.py` | System readiness checks: DB connection, model existence, env registrations, required env vars. |

---

## Data Flow

### Learning Flow

```
Website Scan
    │
    ▼
SEOResult created (score, issues, data)
    │
    ▼
DataCollector.get_website_trajectories()
    ├── Queries historical SEOResults (ordered by time)
    ├── Finds Tasks between consecutive scans
    └── Builds (state, action, reward, next_state) tuples
    │
    ▼
RewardCalculator
    ├── from_seo_results(before, after) → score delta / 100
    ├── from_task_result(task) → success(+1.0), failure(-0.5)
    ├── from_issues(before, after) → reduction rate
    └── combined(...) → weighted [-1, 1] reward
    │
    ▼
TrainingPipeline._transform_to_scored_data()
    └── trajectory dict → ScoredData(state, action, reward, next_state)
    │
    ▼
ScoredDataBuffer.append(data)
    └── Thread-safe FIFO ring buffer (max 10K)
    │
    ▼
PPOTrainer.train_on_buffer(batch_size=32)
    ├── Policy network: MLP(128→256→256→action_dim)
    ├── Value network: MLP(128→256→256→1)
    ├── GAE(lambda=0.95) advantage estimation
    ├── PPO clipped surrogate objective (epsilon=0.2)
    ├── KL early stopping (target=0.02)
    ├── Adam optimizer + cosine annealing LR
    └── save() → /tmp/ppo_model.pt
```

### Decision Flow

```
User/System triggers analysis
    │
    ▼
DecisionEngine.analyze_and_decide()
    ├── 1. Diagnose (LLM: health score, problems, strengths)
    ├── 2. Analyze competition (LLM: barriers, gaps, difficulty)
    ├── 3. Identify opportunities (LLM: quick wins, content gaps)
    ├── 4. Make decision (LLM: strategic, confidence, actions)
    │
    ▼
DecisionIntegrator.enrich_decision()
    ├── PPO policy forward pass on site state
    ├── Top-K actions with confidence scores
    ├── Cross-reference with LLM recommendations
    └── Return enriched decision + data_confidence
    │
    ▼
GrowthScorer.score_growth()
    ├── Compute velocity (accelerating/steady/decelerating)
    ├── Compute trend (upward/stable/declining)
    ├── Score action effectiveness
    └── Comparative rank vs similar sites
    │
    ▼
DecisionExecutor.execute_decision()
    ├── Check confidence gate (HIGH/MEDIUM/LOW)
    ├── Check rate limit
    ├── Check circuit breaker
    ├── Check dangerous action confirmation
    │
    ▼
ActionExecutor.execute(action_type, params)
    ├── Map action_type → environment class
    ├── Create env via Registry.create()
    ├── SEOAction(action_type, params)
    ├── env.step(action) → (next_state, reward, done, info)
    └── Return success + reward
    │
    ▼
SafetyMonitor.record_execution()
    └── Update rate limits + circuit breaker
    │
    ▼
FeedbackLoop.on_scan_complete()
    └── Build trajectory → append to buffer → trigger training
```

---

## API Routes

### Admin API (`/api/admin/v1/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/auth/login` | Admin login |
| GET | `/users` | List users (paginated, searchable) |
| GET | `/websites` | List websites |
| POST | `/websites/{id}/scan` | Trigger scan |
| GET | `/results/summary` | SEO results summary |
| GET | `/results` | List results |
| GET | `/results/issues` | List issues |
| GET | `/api-keys` | List API keys |
| GET | `/backend/status` | Backend service status |
| GET | `/ai-logs` | AI agent logs |

### Growth API (`/api/v1/growth/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/state/{site_id}` | Current growth state |
| POST | `/compare` | Compare multiple sites |
| GET | `/intervention/{site_id}` | Check if intervention needed |
| GET | `/effective-actions` | Most effective actions |
| POST | `/opportunities` | Detect opportunities |
| POST | `/schedule` | Schedule actions |

### REPL API (`/api/v1/repl/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/session` | Create REPL session |
| GET | `/session/{id}` | Get session info |
| POST | `/session/{id}/command` | Send command |
| WebSocket | `/session/{id}/ws` | Real-time terminal |

### Semantic API (`/api/v1/semantic/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/graph/{site_id}` | Entity graph |
| POST | `/context` | Query-specific context |
| GET | `/similar/{site_id}` | Similar sites |
| POST | `/adapt` | LoRA adapter |
| GET | `/patterns` | Cross-site patterns |
| GET | `/health` | Health check |

### Atropos API (`/api/v1/atropos/`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/scored_data` | Single trajectory point |
| POST | `/scored_data_list` | Batch trajectory |
| GET | `/batch` | Pull training batch |
| GET | `/stats` | Buffer statistics |

### Policy Inference API (`/v1/`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/policy/recommend` | PPO action recommendations |
| GET | `/growth/score` | Growth trajectory score |
| GET | `/policy/info` | Model info & training stats |
| GET | `/components` | List initialized components |

---

## Configuration Reference

| Key | Default | Description |
|-----|---------|-------------|
| `learning.batch_size` | 32 | PPO training batch size |
| `learning.min_buffer_size` | 100 | Min trajectories before training |
| `learning.train_interval` | 3600 | Auto-train interval (seconds) |
| `learning.model_save_path` | `/tmp/ppo_model.pt` | Model persistence path |
| `execution.high_confidence_threshold` | 0.7 | Auto-execute threshold |
| `execution.medium_confidence_threshold` | 0.4 | Monitor threshold |
| `execution.max_concurrent` | 3 | Max concurrent actions |
| `execution.rate_limit_per_hour` | 10 | Actions per site per hour |
| `growth.plateau_threshold` | 0.2 | Growth plateau detection |
| `growth.intervention_cooldown` | 86400 | Post-intervention cooldown (24h) |
| `SECRET_KEY` | (required) | JWT signing key (env var) |
| `DATABASE_URL` | `postgresql://...` | PostgreSQL connection |
| `REDIS_URL` | (optional) | Redis connection |

---

## Deployment Requirements

| Dependency | Version | Purpose |
|-----------|---------|---------|
| Python | 3.11+ | Runtime |
| PyTorch | 2.5.1 | Neural networks (PPO trainer) |
| sentence-transformers | 3.0.1 | Semantic embeddings |
| scikit-learn | 1.4.1 | DBSCAN clustering |
| FastAPI | 0.104+ | API framework |
| SQLAlchemy | 2.0+ | ORM |
| PostgreSQL | 16 | Primary database |
| Redis | 7 | Caching (optional) |

---

## Project Metrics

| Metric | Value |
|--------|-------|
| Backend source lines | 8,172 |
| Test lines | 7,160 |
| Core library lines | 2,133 |
| Frontend pages | 1,014 |
| Frontend components | 380 |
| Total tests | 645 (1 skipped) |
| API endpoint files | 10 |
| SEO Environments | 6 |
| REPL Commands | 14 |
| Action types supported | 31 |
| Services/modules | 25+ |
| Configuration parameters | 10+ |

---

## Production Readiness

### Ready for Production
- ✅ PPO trainer with proper PyTorch implementation (not a stub)
- ✅ Real sentence-transformers embeddings (not hash-based)
- ✅ Confidence-gated execution with safety checks
- ✅ Rate limiting and circuit breaker
- ✅ Comprehensive metrics and monitoring
- ✅ Graceful degradation when components are unavailable
- ✅ Structured JSON logging for log aggregators
- ✅ Environment-variable-based configuration
- ✅ Full test suite (645 tests)
- ✅ Startup verification checks

### Needs More Work
- ⚠️ Real database integration testing (tests use mocks)
- ⚠️ Multi-worker deployment safety (global singletons)
- ⚠️ WebSocket endpoint auth (currently open)
- ⚠️ Production Docker Compose with all services
- ⚠️ CI/CD pipeline configuration
- ⚠️ Real SSL/TLS configuration
- ⚠️ Database migration scripts (Alembic)
- ⚠️ Rate limit persistence across restarts
