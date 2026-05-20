# ZenSEO AI — Production Stabilization Plan

## Priority Legend

| Icon | Meaning |
|------|---------|
| 🔴 | Critical — ship-blocking, data loss, security hole |
| 🟠 | High — breaks core workflows, degrades UX significantly |
| 🟡 | Medium — important but workaround exists |
| 🔵 | Low — nice to have, polish |

---

## 1. Testing Gaps

### 1.1 Backend Tests

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🔴 | CI runs all tests | CI ignores `test_semantic/test_lora_adapter.py`, `test_atropos/test_trainer.py`, `test_learning/test_decision_integrator.py` — these could be silently broken | Remove `--ignore` flags or add proper mocking so they pass in CI |
| 🟠 | Input validation tests | All admin CRUD endpoints accept `data: dict` with no Pydantic validation — a bad payload causes 500 instead of 422 | Add Pydantic request models for every POST/PUT and test validation |
| 🟠 | Auth edge cases | No tests for expired tokens, malformed tokens, missing Authorization header, cross-user access | Write `tests/test_core/test_auth.py` covering all JWT failure modes |
| 🟠 | Cascade delete tests | User delete now cascades to websites/api_keys — no test proves it works or that orphaned data doesn't occur | Write test: create user → website → API key → delete user → assert all gone |
| 🟡 | ML client error handling | `_get_ml_client()` returns 503 if ml_client not initialized — no test that the frontend handles this gracefully | Unit test the fallback paths |
| 🟡 | Docker manager tests | `docker_manager.py` shells out to Docker CLI — no tests at all. A Docker CLI change could silently break container control | Mock subprocess calls and test status/start/stop/restart/logs parsing |
| 🔵 | Rate limiting edge cases | API key rate limiting isn't tested | Integration test: exceed rate limit → assert 429 |
| 🔵 | Concurrent access | Multiple admins editing same resource | Locking/optimistic concurrency test |

### 1.2 Frontend Tests

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | No frontend tests exist | Zero test files in `admin/`. Any refactor risks silent regressions | Add at minimum: `npm test` with vitest + happy-dom, test auth flow (login → token storage → 401 redirect) |
| 🟠 | ManagementPage is untested | 690 lines, all CRUD operations, no test coverage | Component tests for: render each tab, create modal form submission, delete confirmation, error states |
| 🟡 | Axios interceptor tests | 401 auto-redirect is critical path logic with no tests | Test: 401 response → localStorage cleared → redirect to /login |
| 🔵 | Login page edge cases | Invalid credentials, network error, already logged in | Test each state renders correctly |

### 1.3 E2E Tests

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟡 | Login → CRUD flow | Full stack integration never tested end-to-end | Playwright/Cypress test: login → navigate management → create user → create website → verify listing |
| 🔵 | Container lifecycle | ML tab start/stop/restart/logs never tested in integration | E2E with Docker available |

---

## 2. Security Hardening

### 2.1 Authentication & Authorization

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🔴 | JWT has no refresh mechanism | Token expires in 24h with no refresh token. User gets logged out with no way to extend session. | Add `/auth/refresh` endpoint that issues new token if current is within grace period (e.g., 1h before expiry). Frontend intercepts 401 but first tries refresh. |
| 🔴 | No password reset flow | Admin has one hardcoded password. If forgotten, no recovery. | Add `/auth/forgot-password` and `/auth/reset-password` endpoints (email-based) |
| 🟠 | Rate limiting on auth endpoints | `/auth/login` has no brute-force protection | Add `slowapi` or middleware: max 5 attempts per IP per minute, 15min lockout |
| 🟠 | Token not invalidated on logout | Logout only clears localStorage — the JWT is still valid until expiry | Add token blocklist (Redis set of revoked JWT IDs) |
| 🟠 | Weak default SECRET_KEY | Default `your-secret-key-change-in-production` — if deploy script forgets `SECRET_KEY`, JWT can be forged | Make SECRET_KEY required at startup (raise if default). Add startup check. |
| 🟡 | No session audit trail | No record of who logged in, when, from what IP | Log all auth events (login, logout, failed attempts) to `admin_audit_log` table |
| 🟡 | Admin registration is open | `/auth/register` endpoint exists — anyone can register an admin account | Remove or protect with an invite-only token |

### 2.2 API Security

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | No request body validation | All endpoints use `data: dict` — no type checking, no required field enforcement, no max-length limits | Replace every `data: dict` with a Pydantic `BaseModel`. Add string length limits (e.g., email max 255, url max 2048). |
| 🟠 | SQL injection surface | Raw query params in filter/sort — `user_id`, `search`, etc. passed directly to ORM filters | Validate all query params as UUIDs where applicable. Add regex patterns. |
| 🟠 | No API-wide rate limiting | An attacker can hammer any endpoint without limit | Add per-IP rate limiting middleware (1000 req/min per IP, configurable) |
| 🟡 | CORS too permissive | `ClientOriginMiddleware` may not cover all abuse vectors | Audit all allowed origins. Ensure production only allows the actual frontend domain. |
| 🟡 | Error messages leak internals | Stack traces and internal paths can appear in 500 responses | Set `show_traceback=False` in production. Return generic "Internal server error". |
| 🟡 | No request size limit | Large payloads can exhaust memory | Add `max_request_size` middleware (e.g., 10MB) |

### 2.3 Infrastructure Security

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | Secrets in docker-compose.yml | DB password, ML API key hardcoded in compose files | Move all secrets to `.env` file. Compose reads from env vars. |
| 🟠 | No TLS on internal traffic | Redis, Postgres passwords sent in clear over Docker network | Enable TLS for Postgres and Redis in production, or at minimum use Docker's internal network isolation |
| 🟡 | Docker runs as root | All containers run as root — container breakout escalates to host | Add `USER` directives in Dockerfiles, use non-root users |
| 🟡 | No image signing | ghcr.io images could be tampered with between CI build and deploy | Add Docker Content Trust (DCT) or cosign signature verification in deploy.sh |

---

## 3. Backend Stability

### 3.1 API Reliability

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🔴 | Endpoints return 500 instead of validation errors | All CRUD endpoints use `data: dict` — missing required fields, wrong types, FK violations all produce 500 | Pydantic request models on every POST/PUT. Consistent error format: `{"error": {"code": "...", "message": "...", "details": {...}}}` |
| 🟠 | No request ID tracking | Errors can't be correlated across logs | Add middleware that generates `X-Request-ID` for every request, logs it, and returns it in response headers |
| 🟠 | No pagination metadata consistency | Some endpoints return `meta.total`, some don't. Frontend can't render pagination reliably | Standardize all list endpoints to return `{"data": [...], "meta": {"total": int, "page": int, "limit": int, "totalPages": int}}` |
| 🟡 | Health check is minimal | `/health` returns `{"status":"healthy"}` but doesn't verify DB or Redis connectivity | Add per-service health checks: database ping, Redis ping, ml-service reachability |
| 🟡 | No graceful shutdown for background tasks | Training pipeline, growth tracker, feedback loop — all running as asyncio tasks. On shutdown, they're killed mid-operation. | Add proper cancellation: catch `asyncio.CancelledError`, save state, close DB connections. |
| 🔵 | No OpenAPI docs for admin endpoints | `docs` endpoint shows auto-generated schema but endpoint grouping is messy | Organize routers with proper `tags`, `summary`, `description`. Add `responses` for error codes. |

### 3.2 Database

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🔴 | No Alembic migrations in place | `alembic.ini` exists but `alembic/` directory has no versions. Schema changes require manual SQL. | Run `alembic init`, create initial migration from current models, add migration to CI (fails if uncommitted changes). |
| 🟠 | No connection pooling limits | SQLAlchemy defaults to 5 pool connections — under load this exhausts quickly | Explicitly configure `pool_size=10, max_overflow=20, pool_pre_ping=True` |
| 🟠 | No retry logic for transient DB failures | Network blips kill the request | Add SQLAlchemy pool retry: `PoolPrePing`, retry on OperationalError |
| 🟡 | No index on foreign key columns | `user_id` on websites/api_keys, `website_id` on results/tasks — full table scans on JOINs | Add explicit indexes on all FK columns |
| 🟡 | Seed script may not match current schema | `seed.py` creates sample data but hasn't been updated for `openrouter_key` column | Update seed to reflect current model. Add a `seed:fresh` Makefile target that drops and recreates. |
| 🔵 | No read replicas | DB handles both writes and reads — under heavy scan loads, admin queries slow down | Document read-replica architecture for future scaling |

---

## 4. Frontend Stability

### 4.1 UX & Error Handling

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | No loading skeletons | Pages flash from empty to loaded. On slow connections, user sees blank space. | Add skeleton loaders matching table/card layouts. Use Suspense boundaries. |
| 🟠 | No empty states | Empty tables show only a header row with "0 results" — confusing and unhelpful | Add empty state illustrations: "No users yet. Create your first user to get started." |
| 🟠 | No error boundaries | A JS crash in any page blows up the entire app | Add React ErrorBoundary at route level. Show "Something went wrong" with retry button. |
| 🟡 | No toast notifications | Success/error feedback is `alert()` dialogs — jarring and unstyled | Add toast system (success: green, error: red, info: blue). Auto-dismiss success after 3s. |
| 🟡 | Forms don't show field-level errors | If API returns `{"detail": "email: field required"}`, user sees generic "Failed to save" | Parse API errors and display inline field validation messages |
| 🟡 | No confirmation on page leave with unsaved form | User can navigate away mid-edit and lose changes | Add `beforeunload` handler and React Router `blur` blocker when form is dirty |
| 🔵 | No keyboard shortcuts | Power users can't navigate efficiently | Add `?` cheatsheet: `g u` → users, `g m` → management, `n` → new item, `/` → search |

### 4.2 Performance

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟡 | No request deduplication | ManagementPage fires 5+ parallel GET requests on every mount. If user navigates away and back, all refire. | Add React Query (TanStack Query) for caching, dedup, stale-while-revalidate |
| 🟡 | No lazy loading for tabs | ML Service tab loads Docker info and ML status even if user never clicks it | Lazy-load tab content. Only fetch ML/docker data when ML tab is active. |
| 🔵 | No virtualization for large tables | If a user has 10K websites, the DOM will have 10K rows | Use `@tanstack/react-virtual` for windowed rendering |

---

## 5. Infrastructure & Deployment

### 5.1 Docker & CI

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | ml-service has no healthcheck in docker-compose.yml | Backend depends on ml-service but doesn't wait for it to be ready | Add healthcheck to ml-service (curl /health). Add depends_on condition in backend. |
| 🟠 | dev-backend uses SECRET_KEY=dev-key in Makefile | Inconsistent with production key → token mismatch when switching contexts | Use `SECRET_KEY=$(shell openssl rand -hex 32)` in production commands, keep dev-key for dev only |
| 🟠 | Frontend VITE_API_URL in production | In docker-compose, frontend uses `VITE_API_URL=http://backend:8000` but vite proxy only helps in dev — production build connects directly | In production Dockerfile, build with correct `VITE_API_URL` build arg. Or serve frontend from nginx that proxies /api to backend. |
| 🟠 | deploy.sh doesn't validate env vars early | If SECRET_KEY or GITHUB_TOKEN is missing, user gets half-deployed broken state | Add pre-flight checks at the top of deploy.sh: check all required vars, check Docker is installed, check ports aren't in use |
| 🟡 | CI doesn't test frontend build | CI only tests backend — frontend build could break silently | Add frontend build step in CI: `cd admin && npm ci && npm run build` |
| 🟡 | CI doesn't run lint | No style enforcement on either frontend or backend | Add `ruff check` (backend) and `eslint` (frontend) to CI |
| 🟡 | Docker images not tagged by version | Only `latest` and `sha-<short>` tags — can't rollback to a specific release | Add semver tagging: `v1.0.0`, `v1.0.1`, etc. via git tags in CI |
| 🟡 | No Docker image prune | CI accumulates old images on the runner | Add `docker image prune -f` at end of CI workflow |

### 5.2 Monitoring & Observability

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | No structured logging | Current logging is `print()`-style — no JSON, no correlation IDs, no queryable format | Switch to structlog or Python's `logging` with JSON formatter. Include request_id, user_id, endpoint, duration. |
| 🟠 | No metrics endpoint | No way to monitor request rates, error rates, latency percentiles | Add `/metrics` endpoint (Prometheus format) using `prometheus_fastapi_instrumentator`. Track: request count, latency p50/p95/p99, error rate by endpoint, DB pool size, active WebSocket connections. |
| 🟠 | No health check endpoint for Docker | Docker depends_on healthchecks rely on `/health` but it doesn't verify DB | `/health` should check: DB ping, Redis ping, at least one model loaded. Return 503 if any critical dependency is down. |
| 🟡 | No alerting | No one gets paged when the system goes down or error rate spikes | Document recommended alerting setup: Uptime Kuma (simple), Grafana OnCall, or Better Uptime with /metrics endpoint |
| 🟡 | No log retention policy | Docker logs grow unbounded — will fill the disk | Add log rotation in docker-compose: `logging: driver: "json-file" options: { max-size: "10m", max-file: "3" }` for every service |

### 5.3 Backup & Recovery

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🟠 | No PostgreSQL backup | Database loss = total data loss. No automated backup. | Add `pg_dump` to cron (daily). Store in `/var/backups/zenseo/`. Document restore procedure in deploy.sh or separate ops docs. |
| 🟡 | No restore testing | Backup exists but has never been restored — it could be corrupt | Add restore drill to release checklist |
| 🟡 | No disaster recovery plan | If the server dies, what's the procedure? | Document: provision new Ubuntu 24.04 → install Docker → pull images → restore DB from latest backup → start stack |

---

## 6. Database Migrations

| Priority | What | Why | How |
|----------|------|-----|-----|
| 🔴 | No initial Alembic migration | Schema is defined only in `db_models.py`. No migration exists to recreate the DB from scratch. | `cd backend && alembic init alembic`, configure `alembic.ini` for DATABASE_URL, run `alembic revision --autogenerate -m "initial"`, commit the migration. |
| 🟠 | Seed migration for openrouter_key | `openrouter_key` column was added via raw SQL — not captured in any migration | Create migration: `ALTER TABLE users ADD COLUMN openrouter_key VARCHAR`. Run it in CI seed step. |
| 🟡 | No `alembic check` in CI | Schema drift can go undetected | Add `alembic check` to CI — fails if models don't match latest migration |

---

## 7. Immediate Fixes (First Week)

Ordered by impact. Do these before anything else:

```
1. [🔴] Add Pydantic request models to all CRUD endpoints
   → backend/app/api/v1/users.py, websites.py, api_keys.py
   → Replace data: dict with CreateUser/UpdateUser/CreateWebsite/etc.
   → Stops 500s from bad payloads

2. [🔴] Create initial Alembic migration
   → backend: alembic init + initial revision
   → Schema is version-controlled from this point

3. [🔴] Fix CI to not skip tests
   → Add proper mocking so lora/trainer/decision_integrator tests pass
   → Remove --ignore flags or document why they're skipped

4. [🟠] Add JWT refresh endpoint
   → backend/app/api/v1/auth.py: /refresh
   → frontend: interceptor tries refresh before redirecting to login

5. [🟠] Add rate limiting on auth endpoints
   → slowapi: 5 attempts/min/IP, 15min lockout

6. [🟠] Add input validation tests
   → Tests for every CRUD endpoint: missing fields, wrong types, FK violations

7. [🟠] Frontend error boundaries + toast notifications
   → Replace alert() with toasts
   → Wrap routes in ErrorBoundary

8. [🟠] Add proper health check
   → /health checks DB + Redis + ml-service
   → Docker healthchecks use this

9. [🟡] Add frontend tests
   → vitest + happy-dom
   → Auth flow, ManagementPage render, form submission
```

---

## 8. Architecture Decisions for Stability

| Decision | Rationale |
|----------|-----------|
| Pydantic over dict | Catches payload errors at the API layer before they reach DB. Consistent 422 responses. Self-documenting via OpenAPI. |
| Alembic over raw SQL | Schema changes are reviewable, reversible, and reproducible. CI enforces drift detection. |
| TanStack Query over manual fetch | Request dedup, caching, stale-while-revalidate, retry — all the things we'd hand-roll poorly. |
| slowapi over DIY rate limit | Battle-tested, Redis-backed, decorator-based. No need to build rate limit buckets from scratch. |
| structlog over print | JSON logs are parseable by Datadog/ELK/Grafana. Searchable, filterable, correlateable. |
| prometheus over custom metrics | Industry standard. Grafana dashboards exist. One decorator gets us p50/p95/p99 latency, error rates, request counts. |
| Non-root containers | Least privilege. Container breakout doesn't give host root. |

---

## Summary by Layer

| Layer | 🔴 Critical | 🟠 High | 🟡 Medium | 🔵 Low |
|-------|-------------|---------|-----------|--------|
| **Testing** | CI skips tests | Missing auth+cascade tests, no frontend tests | E2E tests | Performance tests |
| **Security** | No refresh token, no password reset | No rate limiting, no token revocation, weak SECRET_KEY | CORS audit, no request size limit | Image signing |
| **Backend** | Pydantic models missing | No request IDs, pagination inconsistency | Graceful shutdown, health check depth | OpenAPI polish |
| **Database** | No migrations | No pool config, no retry | Missing indexes, stale seed | Read replicas |
| **Frontend** | — | No loading/empty/error states, alert() instead of toasts | No React Query, no lazy tabs | Virtual scrolling, keyboard shortcuts |
| **Infra** | — | ml-service healthcheck, env validation, VITE_API_URL in prod | CI lint + frontend build, semver tags | Log rotation, backup |
| **Observability** | — | Structured logging, metrics, real health check | Alerting setup | — |
