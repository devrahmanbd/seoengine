# Bugs & Issues — Code Review

Generated from code review of commit `1c90892` against base `9a2fac0`.

---

## Critical (Must Fix)

### C1. `Website.connection_status` column does not exist

**File:** `backend/app/api/v1/websites.py:29`
**Problem:** Filter uses `Website.connection_status` but the model (`db_models.py:40`) has `status`, not `connection_status`. Crashes on first website status filter.
**Fix:** Change to `Website.status`.

### C2. API key `isActive` string never properly handled

**Files:** `admin/src/pages/ManagementPage.tsx:289`, `backend/app/api/v1/api_keys.py:129-132`
**Problem:** Frontend sends `isActive: "false"` (string) but backend checks `data.get("is_active")` (wrong key). Even if matched, `"false"` is truthy in Python.
**Fix:** Check both keys, coerce string to bool: `str(raw).lower() == "true"`.

### C3. Docker stderr treated as failure

**File:** `backend/app/services/docker_manager.py:68,86,97`
**Problem:** Docker writes warnings to stderr even on success. The `not stderr` check treats any stderr as failure.
**Fix:** Check `result.returncode == 0` instead of stderr.

### C4. `_find_compose_dir` can't find compose file from inside Docker

**File:** `backend/app/services/docker_manager.py:118-124`
**Problem:** Searches `os.getcwd()` and parent — inside a container these paths won't contain `docker-compose.yml`.
**Fix:** Mount compose file into container or use env var for path.

### C5. No tests for any new code

~3000 lines added. Zero tests.
**Files needing tests:** `docker_manager.py`, `ml_client.py`, `client_auth.py`, all `ml.py` endpoints, all new CRUD operations, ml-service endpoints, ManagementPage.

---

## Important (Should Fix)

### I1. ManagementPage fetches all tabs' data on mount

**File:** `admin/src/pages/ManagementPage.tsx:125-143`
**Fix:** Lazy-load per tab.

### I2. No pagination in frontend

**File:** `admin/src/pages/ManagementPage.tsx:131-135`
**Fix:** Send `page`/`limit` params, render pagination controls.

### I3. API key "delete" is actually deactivate — misleading UX

**File:** `backend/app/api/v1/api_keys.py:146`
**Fix:** Change UI to say "Revoke" or hard-delete.

### I4. HMAC signature check fails when `client_secret` unset

**File:** `backend/app/core/client_auth.py:49-60`
**Fix:** Log warning at startup, return clear 403.

### I5. `deploy.sh` missing `ML_API_KEY` validation

**File:** `deploy.sh:19-22`
**Fix:** Add `ML_API_KEY="${ML_API_KEY:?Set ML_API_KEY}"`.

### I6. docker-compose memory limits use Swarm-only syntax

**File:** `docker-compose.yml:66-70`
**Fix:** Use `mem_limit: 4G` for compose v2 compatibility.

### I7. ml-service missing PostgreSQL healthcheck condition

**File:** `docker-compose.yml:62-64`
**Fix:** Change to `condition: service_healthy`.

---

## Minor (Nice to Have)

### M1. `lora.py` module-level imports

**File:** `ml-service/app/lora.py:6`

### M2. `alert()` still used in ManagementPage

**File:** `admin/src/pages/ManagementPage.tsx:204,226`

### M3. Docker command timeout too short (15s)

**File:** `backend/app/services/docker_manager.py:16`

### M4. Unused parameter in `semantic.py`

**File:** `backend/app/api/v1/semantic.py:62-64`

### M5. No Docker manager tests (subprocess mocking)

**File:** `backend/app/services/docker_manager.py`
