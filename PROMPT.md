# ZenSEO AI — Phase Prompts

Use each prompt with an AI coding assistant to implement one phase. Each prompt is self-contained — it tells the AI what to build, where we are, and how to verify success.

Before starting any phase, run `git checkout -b phase-<N>` to work in an isolated branch.

> **Design System:** All frontend work must follow DESIGN.md — color palette, typography, spacing, border radius, and component patterns defined there. Read DESIGN.md before implementing any frontend prompt.

---

## Phase 0: Apply Design System

**Prompt:**

```
We are building ZenSEO AI's admin panel — React 18, TypeScript, Vite, TailwindCSS.

Current state: The app uses hardcoded colors and styles with no design system. The DESIGN.md file defines the complete visual language but it hasn't been applied to code.

Read DESIGN.md from the project root first. It defines:
- Color palette (Primary #6366F1 indigo, Background #FAFAFA, Surface #FFFFFF, Text #0A0A0A, etc.)
- Typography (General Sans for display, DM Sans for body, JetBrains Mono for code)
- Spacing scale (4px base: 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96)
- Border radius (4px tags, 6px buttons/inputs, 8px cards/dropdowns, 12px modals)
- Component specs (buttons, cards, inputs, chips, nav, tooltips, checkboxes)
- Do's and don'ts (indigo only for interactive, no pure black/white text, 4px grid, max 2 fonts per screen)

Files to create/modify:
- admin/tailwind.config.js — extend theme with the exact color palette, font families, spacing scale, border radius, and shadows from DESIGN.md
- admin/src/index.css — add @font-face imports for General Sans (Fontshare) and DM Sans (Google Fonts), set body font, create CSS custom properties for all design tokens
- admin/src/components/Button.tsx — reusable button component matching DESIGN.md spec (primary indigo fill, 6px radius, hover lift 1px, sizes sm/32px md/38px lg/44px)
- admin/src/components/Card.tsx — card component (white surface, 1px #E8E8EC border, 12px radius, hover lift 2px + shadow)
- admin/src/components/Input.tsx — input component (1px border, #FAFAFA bg, 6px radius, 10px/14px padding, focus: indigo border + 3px rgba(99,102,241,0.12) ring)
- admin/src/components/Navbar.tsx — sticky top nav (56px height, backdrop-blur, 1px bottom border, 14px medium weight links with bg-alt hover)

Design rules (from DESIGN.md Do's and Don'ts):
1. Indigo (#6366F1) is ONLY for interactive elements — never for decoration or static text
2. Use the 4px spacing grid everywhere
3. No pure black (#000) or pure white (#FFF) text — use #0A0A0A and #FAFAFA
4. No decorative gradients or illustrations
5. Max 2 font weights per screen
6. One primary (filled indigo) button per view section
7. Cards use 12px radius, buttons/inputs use 6px — never swap these
8. Shadows only on hover/focus — never on static elements

Rules:
1. Every color, font, spacing, radius, and shadow must come from DESIGN.md — no invention
2. Replace all existing hardcoded Tailwind classes in current pages to use the new design tokens
3. Export and use the new Button/Card/Input components everywhere instead of raw HTML elements
4. Update Layout.tsx to use the Navbar component
5. Respect the "indigo for interactive only" rule — existing code may use primary color for static text, fix that

Verify:
1. `npm run dev` starts without errors
2. Homepage shows General Sans headings and DM Sans body text
3. Buttons are indigo (#6366F1) with 6px radius, lift 1px on hover
4. Cards have 1px #E8E8EC border, 12px radius, lift 2px on hover
5. Inputs focus has indigo border + 3px ring
6. Nav is 56px with backdrop-blur
7. No #4F46E5 (old primary) appears anywhere — only #6366F1
8. No alert() or unstyled buttons remain
```

---

## Phase F: Fix Critical Bugs

**Prompt:**

```
We are building ZenSEO AI, an autonomous AI-powered SEO engine with FastAPI backend and React admin panel.

A code review identified 5 critical bugs that must be fixed before any other work. Read BUGS.md from the project root for full details.

Bug C1 — Website.connection_status crash:
File: backend/app/api/v1/websites.py:29
Problem: Filter uses Website.connection_status but the model has `status`, not `connection_status`. Any request with a status filter crashes.
Fix: Change Website.connection_status to Website.status.

Bug C2 — API key isActive string never properly handled:
Files: admin/src/pages/ManagementPage.tsx:289, backend/app/api/v1/api_keys.py:129-132
Problem: Frontend sends isActive: "false" (string). Backend checks data.get("is_active") (wrong key). Even if matched, "false" is truthy in Python.
Fix: Check both is_active and isActive keys. Coerce to bool: str(raw).lower() == "true".

Bug C3 — Docker stderr treated as failure:
File: backend/app/services/docker_manager.py:68,86,97
Problem: Docker writes warnings to stderr even on success. The not stderr check treats any stderr as failure.
Fix: Use subprocess.run(check=False) and check result.returncode == 0 instead of not stderr.

Bug C4 — _find_compose_dir can't find compose file from inside Docker:
File: backend/app/services/docker_manager.py:118-124
Problem: Searches os.getcwd() and parent — inside a container these paths won't contain docker-compose.yml. Container lifecycle buttons in admin UI will fail when backend runs in Docker.
Fix: Accept an optional env var DOCKER_COMPOSE_PATH (default None). Add startup warning if container lifecycle endpoints are used without it. Document that Docker socket must be mounted and compose file path set.

Bug C5 — No tests for new code:
~3000 lines added with zero tests.
Fix: Add tests for:
- docker_manager.py: mock subprocess.run, test status/start/stop/restart/logs parsing, success and failure paths
- ml_client.py: test get_status, toggle, recommend with mocked httpx
- client_auth.py: test ClientOriginMiddleware with valid/invalid origins, HMAC signature verification
- ml.py endpoints: test /ml/status, /ml/container/status with mocked dependencies
- api_keys.py: test isActive string-to-bool coercion, verify inactive keys don't authenticate
- websites.py: test status filter with valid/invalid status values

Backend tech: Python 3.12, FastAPI, pytest, pytest-asyncio, unittest.mock.

Verify:
1. POST /api/admin/v1/websites?status=connected returns 200, not 500
2. POST /api/admin/v1/api-keys with isActive: false creates deactivated key
3. docker_manager returns success when Docker prints warnings to stderr
4. _find_compose_dir logs warning instead of crashing when no compose file found
5. New tests all pass: pytest backend/tests/ -q --tb=short
```

---

## Phase 1: Pydantic Request Models

**Prompt:**

```
We are building ZenSEO AI, an autonomous AI-powered SEO engine with a FastAPI backend and React admin panel.

Current state: All CRUD endpoints accept `data: dict` with no validation — bad payloads cause 500 errors instead of 422.

Task: Add Pydantic request models to all admin CRUD endpoints.

Files to modify:
- backend/app/api/v1/users.py — CreateUserRequest, UpdateUserRequest
- backend/app/api/v1/websites.py — CreateWebsiteRequest, UpdateWebsiteRequest  
- backend/app/api/v1/api_keys.py — CreateApiKeyRequest, UpdateApiKeyRequest

Backend tech: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.0, PostgreSQL.

Rules:
1. Every POST/PUT endpoint must accept a Pydantic model, not `data: dict`
2. Fields that come from frontend as camelCase (userId, subscriptionStatus, rateLimit, openrouterKey) must be aliased with `Field(alias=...)` so both camelCase and snake_case work
3. String fields must have max length limits (email 255, url 2048, name 255, etc.)
4. Required fields must raise 422 with clear message when missing
5. Use `model_config = {"populate_by_name": True}` for camelCase alias support
6. Return proper error responses — never return raw 500 for validation failures

Verify:
1. `POST /api/admin/v1/users` with missing email → 422, not 500
2. `POST /api/admin/v1/websites` with no userId → 422
3. `POST /api/admin/v1/api-keys` with empty body → 422
4. All existing tests still pass
```

---

## Phase 2: Database Migrations (Alembic)

**Prompt:**

```
We are building ZenSEO AI, an autonomous AI-powered SEO engine with FastAPI, SQLAlchemy 2.0, PostgreSQL 16.

Current state: Schema is defined only in db_models.py. No migration exists. The `openrouter_key` column was added via raw SQL. Alembic is installed but not configured.

Task: Initialize Alembic and create the initial database migration.

Backend path: /path/to/backend
Models file: backend/app/core/db_models.py

Steps:
1. Configure alembic.ini to read DATABASE_URL from app.core.config (not hardcoded) — use env_var
2. Create `alembic/env.py` that imports SQLAlchemy metadata from db_models
3. Run `alembic revision --autogenerate -m "initial"` to generate the initial migration
4. Verify the migration captures all models: User, Website, APIKey, SEOResult, Task, ErrorLog, AgentLog
5. Add `alembic check` to the Makefile

Verify:
1. `make migrate` creates all tables in a fresh database
2. `alembic check` passes (no drift between models and migrations)
3. `openrouter_key` column exists in the `users` table
4. Foreign keys with CASCADE delete exist on website_id and user_id columns
```

---

## Phase 3: Auth Security (Rate Limiting + Token Refresh)

**Prompt:**

```
We are building ZenSEO AI, an autonomous AI-powered SEO engine with FastAPI.

Current state: JWT auth works but has no brute-force protection on /login, no token refresh mechanism, and no token revocation on logout.

Files:
- backend/requirements.txt — add slowapi, redis
- backend/app/api/v1/auth.py — add rate limiting + refresh endpoint
- backend/app/core/auth.py — add token creation helpers
- admin/src/hooks/useAuth.tsx — add refresh logic to 401 interceptor

Backend tech: Python 3.12, FastAPI, slowapi, Redis, python-jose.

Task:
1. Add rate limiting to /auth/login: max 5 attempts per IP per minute, 15-minute lockout. Use slowapi with Redis backend.
2. Add POST /api/admin/v1/auth/refresh — accepts current token, returns new token if within 1 hour of expiry. If expired, return 401.
3. Add token blocklist: when user calls /logout (or on 401 intercept), add token JTI to Redis set. Blocked tokens rejected at middleware level.
4. In the frontend axios interceptor: on 401, first try POST /api/admin/v1/auth/refresh with the current token. If refresh succeeds, retry the original request. If refresh fails, redirect to /login.

Verify:
1. 6 rapid POST /login calls from same IP → 429 Too Many Requests
2. POST /refresh with valid token (not expired) → new token
3. POST /refresh with expired token → 401
4. After /logout, old token cannot access any endpoint → 401
5. Frontend automatically recovers from 401 when token is refreshable
```

---

## Phase 4: Structured Logging + Health Check

**Prompt:**

```
We are building ZenSEO AI, an autonomous AI-powered SEO engine with FastAPI.

Current state: Backend uses basic Python logging (print-style). /health returns only {"status": "healthy"} without verifying DB, Redis, or ml-service. No request IDs, no JSON format.

Files:
- backend/app/core/logging.py (new) — structured logging setup
- backend/main.py — add middleware, health check
- backend/requirements.txt — add structlog

Task:
1. Replace basic logging with structlog — JSON output with keys: timestamp, level, event, request_id, user_id, endpoint, duration_ms
2. Add middleware that generates X-Request-ID for every request, attaches it to the logger context, and includes it in the response header
3. Upgrade /health to return:
   - database: ping latency in ms or "disconnected"
   - redis: ping latency in ms or "disconnected"  
   - ml_service: reachable or "unavailable" (don't fail if ml-service is down)
   - api: uptime in seconds
   - status: "healthy" only if DB and Redis are connected, else "degraded"
4. Return 200 with status "healthy", or 503 with status "degraded" if critical deps are down
5. Log every request on completion with status code and duration

Verify:
1. Every response has X-Request-ID header
2. /health returns DB latency in ms
3. /health returns 503 when Postgres is unreachable
4. Log output is JSON, parseable by Datadog/ELK
5. Request log line includes method, path, status, duration, request_id
```

---

## Phase 5: Frontend UX Polish (Empty States + Toasts + Error Boundaries)

**Prompt:**

```
We are building ZenSEO AI's admin panel — React 18, TypeScript, Vite, TailwindCSS, react-router-dom v6.22.

First, read DESIGN.md from the project root — this defines our exact design tokens.

Current state: Empty tables show nothing helpful. Errors show via alert() dialogs. A JS crash takes down the whole page.

Files:
- admin/src/components/ErrorBoundary.tsx (new)
- admin/src/components/Toast.tsx (new) — use DESIGN.md colors (Success #10B981, Error #EF4444, Warning #F59E0B), 6px radius, 12px padding
- admin/src/components/EmptyState.tsx (new) — use DESIGN.md typography (DM Sans body 15px, text-secondary #6B6B6B), centered layout
- admin/src/App.tsx — wrap routes in ErrorBoundary
- admin/src/pages/ManagementPage.tsx — replace alert() with toast, add empty states

DESIGN.md Color Reference (use these exact hex values):
- Primary: #6366F1 (indigo — interactive elements ONLY)
- Background: #FAFAFA
- Surface: #FFFFFF
- Text Primary: #0A0A0A
- Text Secondary: #6B6B6B
- Border: #E8E8EC
- Success: #10B981
- Warning: #F59E0B
- Error: #EF4444

DESIGN.md Component Specs:
- Toasts: 6px border radius, 12px padding, use semantic color for left border/accent
- Empty states: centered, icon in muted #9C9C9C, title in DM Sans 24px (subhead size from type scale), body in DM Sans 15px #6B6B6B, CTA is primary indigo button (6px radius, hover lifts 1px)
- Buttons: 6px radius, indigo (#6366F1) fill, white text, medium weight, hover lifts 1px
- Cards: 12px radius, 1px #E8E8EC border, white surface

Design rules (from DESIGN.md):
1. Indigo (#6366F1) is ONLY for interactive elements — never for decoration or static text
2. Use the 4px spacing grid for all padding/margins/gaps
3. No pure black or white for text — use #0A0A0A and #FAFAFA
4. Max 2 font weights per screen
5. One primary (filled indigo) button per view section
6. No decorative gradients or illustrations

Task:
1. Create ErrorBoundary: catches errors, shows "Something went wrong" card (white bg, 12px radius, 1px border, centered), with indigo (#6366F1) "Try Again" button. Wrap each route in App.tsx.
2. Create Toast system: stack of toasts in top-right (24px from top, 24px from right). Background white, 6px radius, 1px #E8E8EC border, left-border accent colored by type. Success auto-dismiss 3s, error stays. z-index 50.
3. Create EmptyState: centered flex column, 48px gap from top. Icon (lucide-react) in #9C9C9C (64px). Title DM Sans 24px #0A0A0A. Description DM Sans 15px #6B6B6B. Optional indigo button (6px radius, hover lift 1px).
4. Replace all alert() calls with toast.error()
5. Add toast.success() on create/edit/delete success
6. Add empty states: "No users yet. Create your first user to get started." with +Add button
7. Add loading skeleton: pulsing gray (#E8E8EC) bars with 12px radius matching table row height (48px)

Verify:
1. Disconnect network → error toast with left red border, not alert()
2. Delete a user → green success toast, auto-dismisses after 3s
3. Empty users tab shows illustration + "No users yet" heading + CTA button
4. Throw an error in ManagementPage → ErrorBoundary catches it, retry works
5. Every color used matches DESIGN.md exactly (check hex values)
6. No pure black (#000) or pure white (#FFF) in use
7. Only one indigo button per view section
```

---

## Phase 6: React Query (Caching + Dedup)

**Prompt:**

```
We are building ZenSEO AI's admin panel — React 18, TypeScript, Vite.

First, read DESIGN.md from the project root — the loading states and transitions must match our design language.

Current state: ManagementPage fires 5+ parallel GET requests on every mount. No caching — navigate away and back, all refetch. ML tab loads data even if never clicked.

DESIGN.md guidelines to follow:
- Loading/skeleton states: use #E8E8EC (Border color) for pulsing bars, 12px radius matching card style
- Transitions: 200ms ease-out (as defined for cards/buttons)
- Spacing: 4px grid for all layout gaps
- Colors: Primary #6366F1 for any loading spinners/indicators

Files:
- admin/src/pages/ManagementPage.tsx — refactor with React Query, add loading states matching design system
- admin/src/hooks/useApi.ts (new) — custom hooks per resource

Dependencies: @tanstack/react-query is already installed.

Task:
1. Create useUsers(), useWebsites(), useApiKeys(), useMlStatus(), useDockerStatus() hooks using useQuery
2. Configure staleTime: 30s for user/website/key lists, 10s for ML/docker status
3. Add QueryClientProvider at the App root
4. Lazy-load ML tab data: only call ml/container APIs when the ML tab is active
5. After mutate (create/edit/delete), call invalidateQueries to refresh the list
6. Add retry: 2 retries on failure, with exponential backoff
7. Loading states must use the design system skeleton pattern (#E8E8EC bars, 12px radius, pulsing animation at 200ms ease-out)

Verify:
1. Navigate to /management → single render triggers each query once (not 5 parallel on mount)
2. Navigate away and back within 30s → no network request (served from cache)
3. Switch to ML tab → network request fires, previous tab data doesn't refetch
4. Delete a user → users list refetches automatically
5. Turn off network → stale data shows, error toast on new mutations
6. Loading skeletons use #E8E8EC with 12px radius and 200ms ease-out pulse
```

---

## Phase 7: CI/CD Hardening

**Prompt:**

```
We are building ZenSEO AI's CI/CD pipeline — GitHub Actions, Docker, ghcr.io.

Current state: CI builds backend and frontend, runs subset of tests. No lint, no frontend build step, no signature verification.

File: .github/workflows/ci.yml

Task:
1. Add frontend build step: `cd admin && npm ci && npm run build`
2. Add Python lint: `pip install ruff && ruff check backend/app/`
3. Add frontend lint: `cd admin && npm run lint` (fix ESLint config if missing)
4. Add `alembic check` step: `cd backend && alembic check` — fails if models don't match migrations
5. Remove `--ignore` flags from pytest command — add proper mocking so all tests pass, or add a job that explicitly documents which tests are skipped and why
6. Add Docker image prune at end of workflow: `docker image prune -f`
7. Add semver tagging: when a git tag like v1.0.0 is pushed, tag images with both the version and latest

Verify:
1. Push that breaks frontend build → CI fails
2. Push with lint errors → CI fails
3. Push that changes a model without running migration → CI fails (alembic check)
4. Git tag v1.0.0 → images tagged ghcr.io/.../backend:v1.0.0 and :latest
```

---

## Phase 8: Production Deployment Script

**Prompt:**

```
We are building ZenSEO AI's deploy script for Ubuntu 24.04.

Current state: deploy.sh exists but doesn't include ml-service, doesn't validate env vars early, has no log rotation, no backup.

File: deploy.sh (bash)

Task:
1. Add pre-flight checks at the top:
   - SECRET_KEY is set and is not the default value
   - GITHUB_TOKEN is set
   - Docker is installed and running
   - docker compose plugin is available
   - Ports 5432, 6379, 8000, 8001, 3000 are free
2. Add ml-service to the compose stack (pull + service definition)
3. Add Docker log rotation to every service: max-size 10m, max-file 3
4. Add postgres backup: daily pg_dump to /var/backups/zenseo/ via a cron job comment block
5. Add non-root user warning and fix: suggest running `sudo usermod -aG docker $USER`
6. Add healthcheck verification after deploy: wait for all services to be healthy (timeout 60s)
7. Print service URLs and login credentials at the end

Use the existing deploy.sh as base. The compose stack has 5 services:
postgres, redis, backend, ml-service, frontend

Images are at ghcr.io/devrahmanbd/seoengine-{backend,frontend,ml-service}:latest

Verify (dry-run):
1. bash deploy.sh without SECRET_KEY → exits with error before pulling anything
2. bash deploy.sh without GITHUB_TOKEN → exits with error
3. All compose service definitions have logging: block with max-size/max-file
4. Healthcheck verification loop exists and times out after 60s
```

---

## Quick Start

```bash
git checkout -b phase-0
# paste Phase 0 prompt to AI assistant
# implement, test, commit
git checkout main && git merge phase-0
git branch -d phase-0
# repeat for phase-1...
```
