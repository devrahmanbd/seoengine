# AtroposRL SEO Engine — Hermes REPL + LoRA Semantic Layer

**Product:** Autonomous SEO Engine with Reinforcement Learning  
**Target:** ZenSEO AI SaaS backend — admin dashboard integration  
**Architecture:** Hybrid Atropos-compatible environments with bundled trainer  
**Status:** Design Document v1  
**Date:** 2026-05-20

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Atropos SEO Environments](#2-atropos-seo-environments)
3. [Semantic DB + LoRA Layer](#3-semantic-db--lora-layer)
4. [Hermes REPL Agent (Web Terminal)](#4-hermes-repl-agent-web-terminal)
5. [Integration Flow](#5-integration-flow)
6. [File Map & Implementation Order](#6-file-map--implementation-order)

---

## 1. Architecture Overview

```
Admin Dashboard (React)
  └─ WebSocket Terminal (Hermes REPL)
       │
       ▼
Backend API (FastAPI)
  ├─ /api/v1/repl/*         — REPL session management
  ├─ /api/v1/atropos/*      — Environment + trainer control
  ├─ /api/v1/semantic/*     — Semantic DB queries
  └─ /api/v1/agents/*       — Existing agent system
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│  AtroposRL Engine                                             │
│                                                               │
│  ┌─────────────────────┐   ┌─────────────────────────────┐   │
│  │  Atropos Environment │   │  Hermes Agent Core          │   │
│  │  Server              │   │  (ReAct loop, memory,       │   │
│  │  • TechnicalSEO Env  │   │   skill docs, tool dispatch)│   │
│  │  • ContentSEO Env    │   └──────────┬──────────────────┘   │
│  │  • KeywordResearch   │              │                       │
│  │  • Backlink Env      │   ┌──────────▼──────────────────┐   │
│  │  • CWV Env           │   │  LoRA Relational-Semantic    │   │
│  │  • Schema Env        │   │  Adapter Generator           │   │
│  └──────────┬───────────┘   │  (inference-time dynamic     │   │
│             │               │   low-rank adapters from     │   │
│  ┌──────────▼───────────┐   │   entity graphs)            │   │
│  │  ScoredData API +     │   └──────────┬──────────────────┘   │
│  │  Batch Queue          │              │                       │
│  └──────────┬───────────┘   ┌──────────▼──────────────────┐   │
│             │               │  Semantic DB                 │   │
│  ┌──────────▼───────────┐   │  ┌────────┐ ┌───────────┐  │   │
│  │  PPO Trainer          │   │  │Qdrant  │ │ Neo4j     │  │   │
│  │  (standalone OR       │   │  │vectors │ │ graph     │  │   │
│  │   atroposlib bridge)  │   │  └────────┘ └───────────┘  │   │
│  └───────────────────────┘   └─────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

All components run as backend services accessible from the admin dashboard. No CLI dependency — the REPL is a WebSocket-connected web terminal inside the dashboard.

---

## 2. Atropos SEO Environments

### 2.1 Environment Contract (Atropos-Compatible)

Each environment follows this contract so it can run standalone OR be served by `atroposlib`:

```python
class SEOEnvironment:
    """Atropos-compatible SEO RL environment"""

    async def reset(self) -> State:
        """Initialize/refresh environment state from live site data"""

    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]:
        """Execute action, return (next_state, reward, done, info)"""

    async def render(self) -> dict:
        """Return human-readable state for dashboard display"""
```

### 2.2 Environments

| Environment | State Space | Action Space | Reward Signal |
|-------------|-------------|--------------|---------------|
| `TechnicalSEOEnv` | HTTP status, meta tags, schema count, heading structure, CWV metrics, mobile score, page speed | `fix_title`, `fix_meta`, `add_schema`, `fix_headings`, `fix_images`, `improve_cwv` | Score delta from re-audit, schema validation pass rate |
| `ContentSEOEnv` | Content quality, readability score, keyword density, entity coverage, word count, topical relevance | `optimize_content`, `add_entities`, `improve_readability`, `add_faq_schema`, `restructure_headings` | Ranking movement, engagement delta, readability improvement |
| `KeywordResearchEnv` | Current rankings, keyword difficulty, search volume, competitor coverage, content gaps | `target_keyword`, `expand_cluster`, `fill_content_gap`, `optimize_for_intent` | Ranking improvement for targeted terms, gap closure rate |
| `BacklinkEnv` | Backlink count, domain authority, referring domains, anchor text distribution, competitor links | `earn_backlink`, `fix_broken_links`, `diversify_anchors`, `disavow_toxic` | Domain authority change, new referring domains |
| `CWVEnv` | LCP, INP, CLS, FCP, TBT values, loading strategy, image sizes, font loading | `optimize_images`, `lazy_load`, `reduce_js`, `optimize_fonts`, `improve_server_response` | CWV threshold pass rate, Lighthouse score delta |
| `SchemaEnv` | Current schema types, schema errors from testing tool, missing entity markup | `generate_article_schema`, `generate_faq_schema`, `generate_breadcrumb`, `generate_organization`, `generate_local_business` | Schema validation pass rate, rich snippet eligibility |

### 2.3 ScoredData API (Atropos Contract)

```python
@dataclass
class ScoredData:
    """Atropos-compatible trajectory data point"""
    state: dict          # Environment state at step t
    action: dict         # Action taken
    reward: float        # Observed reward
    next_state: dict     # State at step t+1
    done: bool           # Episode terminal
    logprobs: dict       # Action log probabilities (for PPO)
    distill_data: dict | None  # Optional distillation arrays

# API endpoints
POST /api/v1/atropos/scored_data      # Single trajectory point
POST /api/v1/atropos/scored_data_list # Batch
GET  /api/v1/atropos/batch            # Trainer pulls batches
```

### 2.4 PPO Trainer (Standalone with Atropos Bridge)

A lightweight PPO trainer that:
- Pulls batches from the ScoredData API
- Computes advantage estimates (GAE)
- Updates policy network (small MLP on top of LLM embeddings)
- Supports on-policy distillation for teacher-student workflows
- Can switch backend to `atroposlib` for distributed GPU training when available

---

## 3. Semantic DB + LoRA Layer

### 3.1 Database Layer

Two stores queried as one semantic interface:

**Vector Store (Qdrant):**
- Collections: `page_embeddings`, `keyword_clusters`, `user_context`, `site_relationships`
- Each point carries payload with entity IDs, relationship types, timestamps
- 1536-dim embeddings (OpenAI `text-embedding-3-small`)

**Graph DB (Neo4j):**
- Nodes: `Site`, `Page`, `Topic`, `Entity`, `Keyword`, `Competitor`, `ContentGap`
- Relations: `COVERS`, `RELATES_TO`, `TARGETS`, `COMPETES_ON`, `GAPS_IN`, `CITES`, `REFERENCES`
- Each edge has confidence score (EXTRACTED=1.0, INFERRED=0.65-0.95)

### 3.2 LoRA Relational-Semantic Adapter Generator

This is the key innovation — NOT fine-tuning, but dynamic inference-time adaptation:

```python
class LoRASemanticAdapter:
    """Generates compact semantic context from entity graphs for API-based LLMs"""

    def __init__(self):
        # Small local embedding model for semantic compression
        self.encoder = SentenceTransformer('all-MiniLM-L6-v2')

    async def generate_context(
        self, site_id: str, query_context: str
    ) -> dict:
        """
        1. Query semantic DB for site entity graph
        2. Encode entities as low-dimensional embedding vectors
        3. Rerank entities by relevance to query context
        4. Compress top entities into structured context block
        """
        entities = await self._query_semantic_db(site_id)
        query_vec = self.encoder.encode(query_context)
        ranked = self._rank_by_relevance(entities, query_vec)
        return self._compress(ranked, max_tokens=200)

    def _compress(self, entities: list, max_tokens: int) -> dict:
        """Encode entity graph as compact structured block"""
        return {
            "primary_topics": extract_topics(entities),
            "key_entities": extract_names(entities),
            "relationship_density": compute_density(entities),
            "cross_site_pattern": detect_pattern(entities),
            "rank_vectors": compress_embeddings(entities, dim=64)
        }
```

**How it works at inference time (API-compatible LLMs):**

Since ZenSEO uses API-based LLMs (OpenAI, Anthropic, OpenRouter via `LLMService`), actual weight modification is impossible. The LoRA pattern is adapted as **semantic context compression**:

1. User sends an `analyze example.com` command
2. REPL agent gathers context → LoRA layer queries semantic DB
3. Semantic DB returns the entity graph for `example.com`: topics covered, keywords targeted, competitors, content gaps, entity relationships
4. LoRA generator encodes this graph as a compact structured context:

```python
# Instead of: "Here are all the relationships..." (500+ tokens)
# LoRA encoding produces:
{
    "entity_adapter": {
        "primary_topics": ["SEO", "content_marketing"],
        "key_entities": ["Google", "Ahrefs", "example_product"],
        "relationship_density": 0.74,
        "cross_site_pattern": "high_authority_content_gap",
        "top_competitors": ["competitor_a.com", "competitor_b.com"]
    },
    "rank_vectors": [0.82, 0.65, 0.91, ...]  # Compact 64-dim representation
}
```

5. This compact encoding is injected into the system prompt as a structured `semantic_context` block — under 200 tokens regardless of graph size
6. LLM generates response with the relational structure explicitly available but compressed
7. A local sentence-transformer embedding model (all-MiniLM-L6-v2, 384-dim) serves as the "adapter backbone": entity relationships are encoded into its embedding space and used to rerank/select the most relevant semantic context before LLM injection

**The "LoRA" name comes from the architectural analogy:**
- Low-rank: entity graph → compact latent representation
- Adaptation: biases LLM reasoning toward relational structure
- Inference-time only: no weights changed, no fine-tuning
- Compositional: multiple entity types compose additively

### 3.3 Cross-Site Pattern Detection

```python
class CrossSiteAnalyzer:
    """Discovers patterns across all managed sites"""

    async def find_patterns(self) -> list[Pattern]:
        """
        - Cluster sites by topic overlap (vector similarity)
        - Identify high-performing action sequences (RL trajectory clustering)
        - Detect content gaps common across similar sites
        - Surface competitor strategies affecting multiple clients
        """
```

These patterns become "background adapters" that inject cross-site intelligence into every decision without leaking PII — the LoRA adapter encodes abstract patterns, not raw data.

---

## 4. Hermes REPL Agent (Web Terminal)

### 4.1 Backend Service

```python
class HermesAgent:
    """Hermes-style agent with ReAct loop — runs as backend service"""

    # Session management
    sessions: dict[str, REPSession]  # WebSocket session state

    async def handle_message(self, session_id: str, message: str) -> AsyncIterator[str]:
        """
        1. Parse command (analyze/optimize/train/decide/research/track/status)
        2. Retrieve session memory (working + episodic + semantic)
        3. Gather context from semantic DB + LoRA adapters
        4. Run ReAct loop:
           a. Observation: collect current site state
           b. Reasoning: evaluate state through RL policy + LoRA context
           c. Action: dispatch to SEO environment / tool call
           d. Observe result → store in episodic memory
        5. Stream response tokens back via WebSocket
        """

    # Memory
    working_memory: dict          # Current session state
    episodic_memory: dict[str, list]  # Past sessions per site
    skill_docs: dict[str, str]    # Learned workflows (markdown)
```

### 4.2 Web Terminal API

```python
# REST endpoints
POST /api/v1/repl/session          # Create new REPL session → session_id
GET  /api/v1/repl/session/{id}     # Session history
POST /api/v1/repl/session/{id}/command  # Send command (HTTP fallback)

# WebSocket
WS  /api/v1/repl/session/{id}/ws   # Bidirectional streaming terminal
```

### 4.3 Dashboard Terminal Component

A web terminal (xterm.js-based) embedded in the admin dashboard:
- Full ANSI color terminal connected via WebSocket
- Command history, tab completion, scrollback buffer
- Agent reasoning pane (expandable sidebar showing ReAct trace)
- Memory viewer (inspect what the agent remembers about this site)

### 4.4 REPL Commands

| Command | Args | Description | Backend Action |
|---------|------|-------------|----------------|
| `analyze` | `<url>` | Full technical + content audit | Runs TechnicalSEOEnv + ContentSEOEnv steps |
| `optimize` | `<url>` [--focus X] | Apply RL-optimized fixes | Queries policy, executes top-K actions |
| `train` | `<domain>` [--episodes N] | Trigger RL training | Runs environment episodes, updates policy |
| `decide` | `<question>` | Strategic decision | LoRA-enriched LLM call through decision engine |
| `research` | `<keyword>` [--deep] | Keyword + competitor research | KeywordResearchEnv + BacklinkEnv |
| `track` | `<domain>` | Ranking trends | Historical ranking data + projection |
| `status` | — | System health | All environment + trainer status |
| `explain` | `<action_id>` | Decision trace | Replay ReAct reasoning plus LoRA context |
| `skills` | [--site SITE] | List learned skills | Query skill doc repository |
| `learn` | `<url>` | Remember a workflow | Store current trajectory as skill doc |
| `forget` | `<pattern>` | Remove learned pattern | Archive low-value skill |
| `semantic` | `<query>` | Query semantic DB | Search vectors + graph, return entities |
| `compare` | `<a.com>` `<b.com>` | Cross-site comparison | Run same actions on both, diff results |
| `help` | [command] | Command reference | — |

### 4.5 Multi-Level Memory

```
┌─────────────────────────────────────────────────────────────┐
│  Working Memory (per session, in-memory dict)               │
│  - Current command context                                   │
│  - ReAct loop state (observation, reasoning, action)         │
│  - Partial results                                           │
│  - Active tool calls                                         │
├─────────────────────────────────────────────────────────────┤
│  Episodic Memory (per site, stored in PostgreSQL)            │
│  - Past REPL sessions for each site                          │
│  - Previous analyses and their outcomes                      │
│  - User preferences (e.g., "always prioritize schema")       │
├─────────────────────────────────────────────────────────────┤
│  Semantic Memory (skill docs, stored as markdown files)      │
│  - Successful workflows captured via `learn` command         │
│  - RL-discovered high-reward action sequences                │
│  - Cross-site patterns from pattern detector                 │
│  - Indexed and searchable by tags + full-text search         │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Integration Flow

### 5.1 Request Lifecycle

```
Admin Dashboard Web Terminal
  │  User types: analyze example.com
  ▼
WebSocket → FastAPI → HermesAgent.handle_message("analyze example.com")
  │
  ├─ 1. Parse command → gather URL, identify site
  ├─ 2. Retrieve episodic memory for example.com
  ├─ 3. Query semantic DB → page embeddings + entity graph
  ├─ 4. LoRA adapter generator → encode entity relationships
  ├─ 5. Apply adapters to LLM (inference-time only)
  │
  ├─ 6. TechnicalSEOEnv.reset() → fetch live page data
  ├─ 7. PPO policy evaluates state → selects action sequence
  ├─ 8. For each action:
  │     a. Execute action
  │     b. TechnicalSEOEnv.step(action) → reward + next state
  │     c. Store (state, action, reward) in ScoredData API
  │     d. Stream result token to dashboard
  │
  ├─ 9. Background: trainer samples ScoredData → policy update
  └─ 10. Return final analysis → dashboard terminal
```

### 5.2 Training Flow

```
Cron / Manual ("train technical --episodes 100")
  │
  ▼
Atropos Trainer
  │
  ├─ 1. For each episode:
  │     a. env.reset() → initial state
  │     b. For each step until done:
  │        - Policy selects action
  │        - env.step(action) → reward
  │        - Store (state, action, reward, logprobs) → ScoredData API
  │
  ├─ 2. Batch: trainer pulls batch from /api/v1/atropos/batch
  ├─ 3. Compute advantages via GAE
  ├─ 4. Update policy network (PPO clipped objective)
  ├─ 5. If teacher model available: on-policy distillation
  │
  └─ 6. Publish new policy → agents pick up automatically
```

---

## 6. File Map & Implementation Order

### Phase 1: Foundation (this build)

```
backend/app/services/atropos/
  __init__.py
  base_env.py              # Abstract SEOEnvironment + State/Action dataclasses
  scored_data_api.py        # ScoredData + API endpoints (Atropos contract)
  trainer.py                # PPO trainer (standalone, atroposlib bridge point)
  
  environments/
    __init__.py
    technical_seo_env.py   # TechnicalSEOEnv
    content_seo_env.py     # ContentSEOEnv
    keyword_env.py         # KeywordResearchEnv
    backlink_env.py        # BacklinkEnv
    cwv_env.py             # CWVEnv
    schema_env.py          # SchemaEnv

backend/app/services/semantic/
  __init__.py
  db.py                    # Semantic DB interface (wraps Qdrant + Neo4j)
  lora_adapter.py          # LoRASemanticAdapter generator
  cross_site.py            # CrossSiteAnalyzer

backend/app/services/hermes/
  __init__.py
  agent.py                 # HermesAgent (ReAct loop, command dispatch)
  memory.py                # WorkingMemory, EpisodicMemory, SemanticMemory
  commands.py              # Command handlers (analyze, optimize, etc.)

backend/app/api/v1/
  repl.py                  # WebSocket + REST endpoints for REPL
  atropos.py               # ScoredData + batch + env control endpoints
  semantic.py              # Semantic DB query endpoints

admin/src/
  components/Terminal.tsx  # Web terminal (xterm.js) component
  hooks/useREPL.ts         # WebSocket hook for REPL
  pages/AgentPage.tsx      # Agent dashboard page
```

### Phase 2: Additions (future)

- `backend/app/services/atropos/environments/community/` — community-contributed envs
- `backend/app/services/hermes/skill_compiler.py` — compiles skill docs into executable workflows
- `backend/app/services/semantic/lora_compiler.py` — GPU-accelerated adapter compilation
