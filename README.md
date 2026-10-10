# Group Photo Collector with Duplicate Detection

A web app for collecting and sharing photos within groups. Users create or join
albums, manage members, and (eventually) upload photos with automatic duplicate
detection.

## Status

Early MVP. Working today:

- User registration and login (JWT bearer auth)
- Album creation with shareable join codes
- Album membership: roles (owner/member), promotion, removal, leaving
- Album listing, detail, title editing, deletion

Not yet implemented:

- Photo upload, storage, and duplicate detection (the `photos` table and model
  exist, but there are no endpoints)
- Object storage (Cloudflare R2 / S3) integration

See `backend/docs/api-contract.md` for the authoritative API behavior.

## Structure

```
backend/    FastAPI + SQLAlchemy + Postgres API (managed with uv + alembic)
frontend/   Vanilla HTML/CSS/JS client (no build step)
scripts/    Tooling, including the API-contract watcher
```

## Backend

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/). Configure a
`.env` with `DATABASE_URL` and `JWT_SECRET`, run migrations, then start the
server:

```bash
cd backend
uv sync
uv run alembic upgrade head
uv run uvicorn src.main:app --reload
```

API docs (Swagger UI): http://127.0.0.1:8000/docs

## Frontend

Serve the static files over HTTP (ES modules need a real server), then open
http://localhost:5173:

```bash
cd frontend
python3 -m http.server 5173
```

The frontend talks to the backend at `http://127.0.0.1:8000` (set in
`frontend/js/config.js`). See `frontend/README.md` for details.

## Development

`scripts/watch-api-contract.sh` watches `backend/docs/api-contract.md` and uses
an opencode agent to keep the frontend in sync whenever the contract changes.
See `scripts/README.md` for usage.
