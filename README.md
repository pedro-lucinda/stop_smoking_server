Sweet—let’s modernize your README to match the **async** stack, **separate scheduler**, and Auth0/OpenAI bits. Here’s a drop-in replacement:

# 🚭 Stop Smoking API

API for a quit-smoking app built with **FastAPI**, **SQLAlchemy 2.0 (async)**, and **Auth0**. Includes a background **scheduler** for daily motivation and badge assignment.

# 🚀 Project Overview

* **Language & Framework:** Python 3.11, FastAPI
* **DB & ORM:** PostgreSQL · SQLAlchemy 2.0 **async** (`AsyncSession`) · Alembic
* **Driver:** `asyncpg`
* **Auth:** Auth0 (OAuth2 Authorization Code + PKCE, RS256)
* **Background jobs:** APScheduler (separate container)
* **AI (optional):** OpenAI for daily motivation text
* **Containers:** Docker + Docker Compose

# 📦 Prerequisites

* Docker & Docker Compose (v2)
* (Optional) Python 3.11 + virtualenv for local, non-Docker runs

# ⚙️ Setup & Run (Docker)

1. **Clone**

```bash
git clone {repo_url}
cd {repo_dir}
```

2. **Configure environment**
   Copy `.env.example` → `.env` and set:

```ini
# Database (async driver)
DATABASE_URL=postgresql+asyncpg://postgres:example@db:5432/db

# CORS (JSON list)
BACKEND_CORS_ORIGINS=["http://localhost:3000"]

# Auth0
AUTH0_DOMAIN=dev-xyz123.auth0.com
AUTH0_API_AUDIENCE=https://api.myapp.com
AUTH0_CLIENT_ID=YourAuth0ClientID
# Management API (only needed for email updates)
AUTH0_MGMT_CLIENT_ID=YourMgmtClientID
AUTH0_MGMT_CLIENT_SECRET=YourMgmtClientSecret

# OpenAI (needed for motivation generation)
OPENAI_API_KEY=sk-...

# Scheduler / timezone
TIMEZONE=UTC
# If you ever run the scheduler inside the API process (dev only)
SCHEDULER_ENABLED=false
```


3. **Build & start**

```bash
docker compose up --build -d
```

4. **Migrate DB**

```bash
docker compose run --rm api alembic upgrade head
```

5. **Docs**

```
http://localhost:8000/api/v1/docs
```

# 🔐 Auth0 Configuration

1. **Create API**

   * Auth0 → **APIs** → *Create API*
   * **Identifier:** `https://api.myapp.com` (must match `AUTH0_API_AUDIENCE`)
   * **Signing Algorithm:** RS256

2. **Create Application**

   * Auth0 → **Applications** → *Create Application* → SPA or Regular Web App
   * **Allowed Callback URLs:**

     ```
     http://localhost:8000/api/v1/docs/oauth2-redirect
     ```
   * **Allowed Web Origins / Logout URLs:**

     ```
     http://localhost:8000
     ```

3. **Permissions / Scopes**

   * OIDC scopes used for login in Swagger: `openid`, `profile`, `email`
   * API permissions used by the backend (example):

     * `manage:badges` (for admin badge endpoints)

# 🗂 Alembic Migrations

```bash
# New revision
docker compose run --rm api alembic revision --autogenerate -m "describe change"

# Upgrade
docker compose run --rm api alembic upgrade head

# Downgrade one
docker compose run --rm api alembic downgrade -1

# Reset to base
docker compose run --rm api alembic downgrade base
```

# 🧭 Services (Compose)

* **api** – FastAPI app (`uvicorn`)
* **scheduler** – APScheduler runner (`python -m app.tasks.run_scheduler`)
* **db** – PostgreSQL 15

> Don’t scale the `scheduler` service beyond 1 replica unless you add a distributed lock.

# ⚡ Using the API

1. **Authorize in Swagger**

   * Open `/api/v1/docs` → **Authorize** → complete Auth0 login (PKCE)
   * Swagger will attach `Authorization: Bearer <token>` automatically

2. **Secured routes**

   * `/api/v1/preference`, `/api/v1/motivation`, `/api/v1/user`, etc.
   * Some admin endpoints (e.g. `/api/v1/badge`) require `manage:badges`

# 🧰 Development Notes

* This codebase uses **SQLAlchemy async**. In handlers/services:

  * Inject `AsyncSession`
  * Use `select(...)` + `await db.execute(...)`
  * `await db.commit()`, `await db.refresh(obj)`, `await db.delete(obj)`
  * **Do not** access lazy relationships (e.g. `current_user.diaries`) — query explicitly or use `selectinload(...)`.

* Background jobs:

  * Implemented in `app/tasks/*`
  * The scheduler service registers:

    * Motivation generation **every 8 hours**
    * Badge assignment **every 24 hours**

# 🛡 Security & Best Practices

* Secrets via Pydantic Settings (`.env`)
* RS256 validation against Auth0 JWKS
* HTTPS in production (terminate TLS at the proxy)
* Rate limiting recommended (e.g. `slowapi`)
* Structured logging with request IDs
* DB uniqueness constraints for critical invariants (e.g., one diary entry per user per day)

# 🧪 Smoke Tests (quick)

```bash
# API is up
curl -s http://localhost:8000/api/v1/openapi.json | head -n 2

# Healthcheck (if you add one)
# curl -i http://localhost:8000/api/v1/healthcheck
```

# 🐞 Troubleshooting

* **`MissingGreenlet`**: You triggered an async lazy-load. Don’t do `user.relationship` directly. Query with `select(...)` and `join/selectinload`.
* **`asyncpg` not found**: Add `asyncpg` to `requirements.txt`, rebuild with `--no-cache`.
* **Deletes do nothing**: With `AsyncSession`, use `await db.delete(obj)` then `await db.commit()`.
