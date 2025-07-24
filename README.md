## 🚀 Project Overview

- **Language & Framework:** Python 3.11, FastAPI
- **Database:** PostgreSQL (SQLAlchemy + Alembic)
- **Auth:** Auth0 — OAuth2 Authorization Code (PKCE)
- **Containerization:** Docker & Docker Compose

---

## 📦 Prerequisites

- Docker & Docker Compose (v2+)
- (Optional) Python 3.11 + virtualenv, if running locally

---

## ⚙️ Setup & Running with Docker

1. **Clone the repo**

   ```bash
   git clone {repo_url}
   cd {repo_dir}
   ```

2. **Configure environment**  
   Copy `.env.example` → `.env` and fill in these values:

   ```ini
   # Database & cache
   DATABASE_URL=postgresql+psycopg2://postgres:example@db:5432/db
   REDIS_URL=redis://redis:6379/0

   # CORS origins (e.g. frontend URL)
   BACKEND_CORS_ORIGINS=["http://localhost:3000"]

   # Auth0 settings
   AUTH0_DOMAIN=dev-xyz123.auth0.com
   AUTH0_CLIENT_ID=YourAuth0ClientID
   AUTH0_CLIENT_SECRET=YourAuth0ClientSecret   # only needed if you use client credentials flow
   AUTH0_API_AUDIENCE=https://api.myapp.com

   # Scheduler / timezone
   TIMEZONE=UTC
   ```

3. **Build & start containers**

   ```bash
   docker-compose up --build -d
   ```

4. **Apply migrations**

   ```bash
   docker-compose run --rm api alembic upgrade head
   ```

5. **Open API docs**  
   Visit in your browser:
   ```
   http://localhost:8000/api/v1/docs
   ```

---

## 🔐 Auth0 Configuration

1. **Create Auth0 API**

   - In **Auth0 Dashboard → APIs → Create API**
   - **Identifier** = `https://api.myapp.com` (matches `AUTH0_API_AUDIENCE`)
   - **Signing Algorithm** = RS256

2. **Create Auth0 Application**

   - In **Applications → Create Application**
   - **Type:** Regular Web App (or Single Page App)
   - **Allowed Callback URLs:**
     ```
     http://localhost:8000/api/v1/docs/oauth2-redirect
     ```
   - **Allowed Web Origins:**
     ```
     http://localhost:8000
     ```
   - **Allowed Logout URLs:**
     ```
     http://localhost:8000
     ```
   - **Save**, then copy **Client ID** → `AUTH0_CLIENT_ID`
   - Copy **Client Secret** if you need the credentials (for backend flows)

3. **Enable Scopes**  
   Make sure the API defines at least these scopes under **Permissions → Scopes → Add Scope**:
   - `openid`
   - `profile`
   - `email`

---

## 🗂 Alembic Migrations

- **Create a new revision**

  ```bash
  docker-compose run --rm api alembic revision --autogenerate -m "describe change"
  ```

- **Apply migrations**

  ```bash
  docker-compose run --rm api alembic upgrade head
  ```

- **Rollback one step**

  ```bash
  docker-compose run --rm api alembic downgrade -1
  ```

- **Reset to base**
  ```bash
  docker-compose run --rm api alembic downgrade base
  ```

---

## ⚡️ Using the API

1. **Authorize in Swagger UI**

   - Open `/api/v1/docs`
   - Click **Authorize**
   - Log in via Auth0 (PKCE flow)
   - Swagger will store your access token automatically

2. **Call protected endpoints**  
   All routes under `/api/v1/preference`, `/api/v1/motivation`, `/api/v1/user` are secured.  
   Swagger will send `Authorization: Bearer <token>` for you.

---

## 🛡 Security & Best Practices

- Secrets loaded from `.env` via Pydantic’s `BaseSettings`
- OAuth2 tokens with expiry and RS256 verification against Auth0’s JWKS
- Enforce HTTPS in production
- Rate‑limit endpoints (e.g. with `slowapi`)
- Structured logging & monitoring

---

## 🐳 Dockerfile & Compose Highlights

- **Dockerfile**

  - Python 3.11‑slim base
  - Leverages layer caching for `requirements.txt`
  - Uses `uvicorn --reload` for development

- **docker-compose.yml**
  - Services: `api`, `db` (Postgres), `redis`
  - Named volume for Postgres data
  - `.env` injected into the `api` service
