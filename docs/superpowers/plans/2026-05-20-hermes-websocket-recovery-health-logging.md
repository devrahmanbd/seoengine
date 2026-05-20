# Hermes REPL: WebSocket Recovery, Health Endpoints & Structured Logging

> **For agentic workers:** Inline execution in current session.

**Goal:** Add WebSocket resilience, health monitoring, and structured logging to the Hermes REPL system.

**Architecture:** Extend existing WebSocket handler with idle timeout, ping/pong, graceful disconnect, and reconnect. Add HTTP health endpoints. Add structured logging to agent and API layers.

**Tech Stack:** FastAPI, asyncio, Python logging, Pydantic

---

## Files to Modify

| File | Change |
|------|--------|
| `backend/app/api/v1/repl.py` | WebSocket resilience + health endpoints + logging |
| `backend/app/services/hermes/agent.py` | `HermesAgent.health()` method + structured logging |
| `backend/app/services/hermes/memory.py` | `HermesMemory.health()` method |
| `backend/app/services/semantic/db.py` | `SemanticDB.health()` with latency |
| `backend/app/services/semantic/lora.py` | `LoRASemanticAdapter.health()` method |

## Implementation Tasks

### Task 1: Health check methods on service classes

**Files:**
- Modify: `backend/app/services/semantic/db.py:128-129`
- Modify: `backend/app/services/semantic/lora.py:130`
- Modify: `backend/app/services/hermes/memory.py:295-322`
- Modify: `backend/app/services/hermes/agent.py:56-192`

### Task 2: Health & monitoring endpoints + startup timestamp

**Files:**
- Modify: `backend/app/api/v1/repl.py`

### Task 3: Structured logging

**Files:**
- Modify: `backend/app/services/hermes/agent.py`
- Modify: `backend/app/api/v1/repl.py`

### Task 4: WebSocket resilience

**Files:**
- Modify: `backend/app/api/v1/repl.py`
