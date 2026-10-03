# Apex Prep

Personal Digital SAT practice platform: realistic adaptive practice exams, weakness training, topic drills.

- Spec and plan: [`docs/SAT_SPEC.md`](docs/SAT_SPEC.md), [`docs/TAXONOMY.md`](docs/TAXONOMY.md), [`PLAN.md`](PLAN.md)
- Deploying: [`docs/DEPLOY.md`](docs/DEPLOY.md)

## Local development

```bash
cp .env.example .env          # defaults work for local dev
docker compose up             # Postgres :5432, API :8000, web :5173
```
Open <http://localhost:5173>.

Or without Docker for the app processes (Postgres still from compose):
```bash
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head && uv run uvicorn app.main:app --reload
cd frontend && yarn && yarn dev
```

## Checks

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd frontend && yarn lint && yarn typecheck && yarn test
cd frontend && BASE_URL=http://localhost:5173 yarn e2e   # needs the app running
```
