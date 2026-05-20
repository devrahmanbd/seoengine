# AtroposRL SEO Engine — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** Build production-grade AtroposRL SEO Engine with Hermes REPL, LoRA semantic layer, and admin dashboard integration.

**Architecture:** 5 phases — (1) Atropos env server, (2) semantic DB + LoRA layer, (3) Hermes REPL, (4) dashboard terminal, (5) integration & hardening. Each phase: 3 code agents, 1 test agent, 1 review/improve agent.

**Tech Stack:** Python 3.11+, FastAPI, Pydantic, asyncio, sentence-transformers, Qdrant, Neo4j, React/TypeScript, xterm.js

**Spec:** `docs/superpowers/specs/2026-05-20-atropos-rl-seo-engine.md`

---

## File Structure

```
backend/app/services/atropos/
  __init__.py
  base_env.py                # Abstract SEOEnvironment, State, Action
  scored_data_api.py         # ScoredData dataclass + API router
  trainer.py                 # PPO trainer (standalone, atroposlib bridge)

  environments/
    __init__.py
    technical_seo_env.py     # TechnicalSEOEnv
    content_seo_env.py       # ContentSEOEnv
    keyword_env.py           # KeywordResearchEnv
    backlink_env.py          # BacklinkEnv
    cwv_env.py               # CWVEnv
    schema_env.py            # SchemaEnv

backend/app/services/semantic/
  __init__.py
  db.py                      # SemanticDB interface (wraps Qdrant + Neo4j)
  lora_adapter.py            # LoRASemanticAdapter generator
  cross_site.py              # CrossSiteAnalyzer

backend/app/services/hermes/
  __init__.py
  agent.py                   # HermesAgent (ReAct loop, command dispatch)
  memory.py                  # WorkingMemory, EpisodicMemory, SemanticMemory
  commands.py                # Command handlers (analyze, optimize, etc.)

backend/app/api/v1/
  repl.py                    # WebSocket + REST endpoints for REPL
  atropos.py                 # ScoredData + batch + env control endpoints
  semantic.py                # Semantic DB query endpoints

admin/src/
  components/Terminal.tsx    # Web terminal (xterm.js)
  hooks/useREPL.ts           # WebSocket hook
  pages/AgentPage.tsx        # Agent dashboard page
```

## Key Shared Interfaces

```python
# base_env.py
@dataclass
class SEOAction:
    action_type: str
    params: dict
    confidence: float = 0.0

@dataclass
class State:
    site_id: str
    metrics: dict
    timestamp: float
    features: np.ndarray | None = None

class SEOEnvironment(ABC):
    @abstractmethod
    async def reset(self) -> State: ...
    @abstractmethod
    async def step(self, action: SEOAction) -> tuple[State, float, bool, dict]: ...

# scored_data_api.py
@dataclass
class ScoredData:
    state: dict
    action: dict
    reward: float
    next_state: dict
    done: bool
    logprobs: dict | None = None
    distill_data: dict | None = None
```
