# GlowAI Backend

FastAPI backend for the GlowAI app — auth, user profiles, makeup/skin analysis, looks diary, tutorials, and AI generation endpoints backed by Groq/Gemini vision.

## Stack

- FastAPI + Uvicorn
- PostgreSQL via SQLAlchemy, migrations with Alembic
- JWT auth (access + refresh tokens)
- Groq / Google Gemini for AI vision analysis

## Setup (local, no Docker)

1. Create and activate a virtualenv, then install dependencies:

   ```
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. Copy the env template and fill in your own values:

   ```
   cp .env.example .env
   ```

   | Variable | Required | Notes |
   |---|---|---|
   | `DATABASE_URL` | yes | `postgresql://user:pass@host:5432/dbname` |
   | `JWT_SECRET` / `JWT_REFRESH_SECRET` | yes | generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` |
   | `GROQ_API_KEY` | recommended | free tier at [groq.com](https://groq.com) — fast text analysis |
   | `GOOGLE_API_KEY` | recommended | free tier at [aistudio.google.com](https://aistudio.google.com) — Gemini vision, used over Groq when both are set |
   | `UPLOAD_DIR` | no | defaults to `uploads` |

   At least one of `GROQ_API_KEY` / `GOOGLE_API_KEY` is needed for AI analysis features to work; the API still runs without them (check `/health` to see which are active).

3. Create a matching Postgres role + database (adjust to your `DATABASE_URL`):

   ```
   createuser glowai -P   # set the password to match DATABASE_URL
   createdb -O glowai glowai
   ```

4. Run it:

   ```
   uvicorn main:app --reload
   ```

   Tables are created automatically on startup (`Base.metadata.create_all`). Alembic migrations are available under `alembic/` if you need to evolve the schema afterward:

   ```
   alembic upgrade head
   ```

5. Verify:

   ```
   curl http://localhost:8000/health
   ```

   Interactive API docs are at `http://localhost:8000/docs`.

## Deploy (Docker)

The included `Dockerfile` + `docker-compose.yml` bring up the API and a Postgres instance together:

```
cp .env.example .env   # fill in real values first
docker compose up -d --build
```

This starts:
- `db` — Postgres 18, data persisted in a named volume, only reachable from inside the compose network (not exposed to the host)
- `backend` — built from the `Dockerfile`, reads secrets from `.env` via `env_file`, listens on `:8000`, `uploads/` bind-mounted so files persist across restarts

Check it's healthy:

```
curl http://localhost:8000/health
```

### Deploying to a host (Railway / Render / Fly / a VPS, etc.)

- Point the platform at this repo; it will build from the `Dockerfile`.
- Provision a managed Postgres (or run the `db` service alongside) and set `DATABASE_URL` to point at it.
- Set `JWT_SECRET`, `JWT_REFRESH_SECRET`, `GROQ_API_KEY`, `GOOGLE_API_KEY` as environment variables/secrets in the platform's dashboard — do not commit real values to `.env` in this repo, it's gitignored for exactly that reason.
- Expose port `8000`.
