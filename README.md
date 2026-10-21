# Apex Prep

https://apex-prep.onrender.com

Personal Digital SAT prep app, built around one goal: 1450+ total and 700+ Math on **5 December 2026**.

- **Practice Exam:** full test or one section, at Official-level, Hard, or Brutal difficulty. Adaptive Module 2, server-run timer, break, autosave and resume. Exam tools: highlighter and notes, eliminator, mark for review, navigator, calculator, reference sheet.
- **Results:** score estimates with ± margins, calibrated to the official scores you log. Breakdown by domain and skill, pace against test timing, and a full question review.
- **Weekly plan:** a day-by-day schedule to test day. Exams step up in the final three weeks and taper at the end. Tasks tick themselves off as you practise.
- **Weakness Training:** adaptive questions on the skills costing you the most points (misses, slow answers, overdue reviews), with Math weighted 1.3×.
- **Topic Drill:** pick any skill and difficulty, with instant worked solutions. Math questions are generated without limit.
- **Mistake Notebook:** every miss, tagged by why you missed it, with "retry similar".
- **Dashboard:** countdown, estimate against the Aalto bar, today's tasks, top weaknesses, score trend, mastery heatmap.

Docs: [`docs/SAT_SPEC.md`](docs/SAT_SPEC.md) (test spec), [`docs/SCORING.md`](docs/SCORING.md) (every model), [`docs/TAXONOMY.md`](docs/TAXONOMY.md), [`docs/DEPLOY.md`](docs/DEPLOY.md), [`PLAN.md`](PLAN.md).

## Local development

```bash
cp .env.example .env          # defaults work for local dev
docker compose up             # Postgres :5432, API :8000, web :5173
```
Open <https://apex-prep.onrender.com>

Or without Docker for the app processes (Postgres still from compose):
```bash
docker compose up -d db
cd backend && uv sync && uv run alembic upgrade head && uv run python -m app.seed && uv run uvicorn app.main:app --reload
cd frontend && yarn && yarn dev
```

## Questions

- **Math:** generated on demand by `backend/app/generators/` (SymPy-computed keys, distractors from named error models).
- **Reading & Writing:** a hand-written seed bank in `backend/app/seed/rw/*.json` (validated by `RWItem`), loaded by `python -m app.seed`. More items: `uv run python -m app.generate rw --skill RW.SEC --n 3` (needs `ANTHROPIC_API_KEY`; see `docs/DEPLOY.md` §5).

## Checks

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy && uv run pytest
cd frontend && yarn lint && yarn typecheck && yarn test
cd frontend && BASE_URL=http://localhost:5173 yarn e2e   # needs the app running
```
