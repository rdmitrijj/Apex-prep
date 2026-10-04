# CLAUDE.md

Personal Digital SAT prep app (FastAPI + React + PostgreSQL). Owner tests on 2026-12-05 (also eligible: 2026-11-07); Aalto bar is 1350 total / 700 Math, ties broken by Math, so Math is weighted 1.3× in the engine.

## Status
Plan approved (app name: Apex Prep; no Desmos key yet, so the math.js fallback is used). Anthropic key lives only in the gitignored root `.env`; the R&W pipeline reads it from env and the app works on the seed bank without it. M1–M5 done (M4 exam + M5 weakness training; SRS/mistake notebook/miss-reason tags skipped); M6 partly done (dashboard, score estimate; no Bluebook calibration or study plan yet).

## Key docs
- `docs/SAT_SPEC.md`: verified test spec (structure, ordering, SPR rules, tools, scoring). Official source wins over the brief.
- `docs/TAXONOMY.md` mirrors `backend/app/seed/taxonomy.json` (**source of truth**). IDs: `SECTION.DOMAIN.SKILL.SUBSKILL`. Questions, responses, and mastery reference leaf IDs only.
- `PLAN.md`: milestones M1–M7.

## Conventions
- No College Board / Bluebook names, logos, or verbatim official questions in the app.
- `backend/app/engine/` and `backend/app/generators/` are pure Python (no FastAPI/SQLAlchemy imports), mypy-strict, heavily unit-tested.
- Math answer keys are computed with SymPy, never hard-coded; distractors come from named error models and must never equal the key.
- Server is authoritative for exam timing: `services/exam.tick` closes an expired module on the next request; autosaves are accepted until deadline + 3 s.
- Responses are graded when a module closes; in-progress exam responses have `correct = NULL` and are excluded from stats and weaknesses.
- Never commit secrets; every env var goes in `.env.example`.

## Layout
- `backend/`: FastAPI app (`app/main.py`), uv-managed, Python 3.12. `app/core` (config, db, security), `app/api` (routers under `/api`), `app/models` (all tables, one module), Alembic in `alembic/` (hand-named revisions `0001_…`).
- `frontend/`: React 18 + Vite + Tailwind v4, yarn. TypeScript is pinned to 6.x (typescript-eslint doesn't support TS 7 yet).
- Prod: root `Dockerfile` builds the SPA and serves it from FastAPI. `render.yaml` describes the Render service. The container start runs `alembic upgrade head`.

## Commands
- DB: `docker compose up -d db` (tests create/wipe `apex_test` themselves)
- Backend: `cd backend && uv run pytest -q` (`GEN_SEEDS=20` speeds up the generator suite; CI runs the default 200), `uv run ruff check . && uv run ruff format --check .`, `uv run mypy`
- New migration: `uv run alembic revision --autogenerate -m <slug>`, then rename the file to `NNNN_<slug>.py` and set `revision = "NNNN"`.
- Frontend: `cd frontend && yarn lint && yarn typecheck && yarn test`
- E2E: start the app (compose, or `docker build -t apex-prep . && docker run …`), then `BASE_URL=… yarn e2e`

## Gotchas
- Generators: SymPy auto-distributes `3*(x+2)` into `3x+6`, so stems that must show the unexpanded form build their LaTeX by hand. Compare SymPy numbers with `==` only against Rationals (`Integer(2) == 2.0` is False in SymPy ≥1.13).
- R&W generation (`app/generate.py`): a structured-output field named like `reasoning` trips the reasoning-extraction safeguard (refusal); keep the blind-solve field a short `justification`. Choices are reshuffled after generation because the model favors certain letters.
- Seed data (`python -m app.seed`) runs on every container start and is idempotent via `questions.content_hash`.
- Session cookie is always `Secure`. Browsers allow that on http://localhost, but httpx tests must use an `https://` base URL.
- Neon URLs go through `normalize_db_url` (strips sslmode/channel_binding; `-pooler` host disables statement caches).
- On Render (`RENDER=true`), startup fails unless `SECRET_KEY` is set to 32+ characters.
