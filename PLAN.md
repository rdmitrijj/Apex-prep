# PLAN: Personal Digital SAT Prep Platform

Status: approved 2026-10-03. M1–M5 shipped 2026-10-04 (see notes under M4/M5); M6 partly. Specs: `docs/SAT_SPEC.md`, `docs/TAXONOMY.md`, `backend/app/seed/taxonomy.json`.

## 0. Before any code: what actually raises your score

You have 9 weeks and need about +290 to reach Aalto's bar (1350 total / 700 Math), or +490 for 1550. **Building this app must not eat study time.** Three things to do this week, independent of the app:

1. **Take an official Bluebook practice test now** (free, real adaptive, real scoring). It is a better diagnostic than anything we can build in week 1. Log the result; it becomes the app's first score-calibration point.
2. **Register for 7 Nov as well as 5 Dec** (deadline 23 Oct). Aalto takes your highest Math across sittings, so two attempts cost little and remove single-day risk.
3. **Until milestone 2 is live, drill Math in College Board's free Student Question Bank and Khan Academy.** They have real items, filterable by skill and difficulty.

## 1. Proposed changes to the brief (please approve, reject, or edit each)

| # | Brief | Proposal | Why |
|---|---|---|---|
| P1 | 7 full Practice Exams + 2/week in final 3 weeks, all in-app | **Use official Bluebook tests first** (real items, real scoring). In-app Practice Exams cover the extra volume once those run out. Add a tiny "log official test result" form that feeds the score trend and calibration. | Official items beat generated ones for score prediction. The in-app exam is still built (M4), but nothing depends on it early. |
| P2 | Background batch LLM generation inside the web service with a live buffer | **Generation is a CLI command** (`python -m app.generate rw --skill … --n …`), run locally or from a manual GitHub Action, writing into Neon. The web app only serves stored questions. | Render free tier sleeps, so in-process background workers die. A CLI is simpler, cheaper, and the exam never waits on the API either way. |
| P3 | Score estimation "calibrated to published tables" | Not possible: no official digital-SAT conversion tables exist. **Calibrate to your own Bluebook scores** + published benchmarks. | See SAT_SPEC §6/§8. |
| P4 | Seed bank: ≥10 R&W questions per sub-skill | Taxonomy has **35 R&W sub-skills → ≥350 hand-written items**. I'll write them in batches per milestone, prioritising high-weight sub-skills (WIC, SEC, RS, TRN, COE) first. | Quality > speed; 350 careful items is real work. |
| P5 | Line reader, keyboard shortcuts for every tool | Keyboard shortcuts for answer/flag/navigate/eliminate only; line reader skipped. | Rarely used; add later if you miss them. |

Everything else from the brief stays as written.

## 2. Architecture (one-paragraph version)

Monorepo. **Backend:** FastAPI + async SQLAlchemy 2 + asyncpg + Alembic, Pydantic v2. Pure-Python `app/engine/` (rating updates, weakness score, SRS, item selection, score estimate) and `app/generators/` (SymPy math generators), both with no web/DB imports and mypy-strict. **Frontend:** React 18 + TS + Vite, Tailwind, TanStack Query, Zustand for exam state, KaTeX, Recharts. **Prod:** FastAPI serves the built SPA; one Render web service; Neon Postgres (URL normalisation + PgBouncer handling + `DATABASE_URL_DIRECT` for Alembic). **Auth:** email+password (argon2), JWT in httpOnly cookie, `ALLOW_REGISTRATION` flag. **Timer:** server stores module `started_at`/`deadline`; client only renders; server rejects answers after deadline and auto-closes stale modules on next request.

Data model per the brief (users, skills, questions, exam_sessions, exam_modules, responses, skill_mastery + history, review_schedule, study_plans, question_reports, plus `official_scores` for P1).

## 3. Milestones

Each milestone ends with: all tests green, app run and clicked through (Playwright where relevant), commit, and a short "what works / how to try it" note to you.

### M1: Skeleton + deploy
- Repo, `CLAUDE.md`, docker-compose (Postgres + backend + Vite), `.env.example`.
- FastAPI app, `/api/health`, auth (register/login/logout/me), Alembic baseline with the full schema.
- React shell: login, protected layout, "waking up server…" retry state.
- CI: ruff, mypy (engine/generators), eslint, tsc, pytest, vitest.
- `render.yaml`, `docs/DEPLOY.md`; **deployed to Render + Neon with a green health check.**
- *Needs from you:* GitHub repo, Neon project, Render account (I'll walk you through it in DEPLOY.md).

### M2: Taxonomy + Math generators + Topic Drill  ← *you start practising in-app here*
- Seed command loads taxonomy.
- Generator framework: `generate(subskill_id, difficulty, rng) -> Question`; SymPy-computed key; distractors from named error models (sign flip, wrong formula, partial solution, unit slip). One generator family per Math sub-skill (56), each covering easy/medium/hard; hard ≥ hardest official items.
- Tests per generator: key verified independently, 4 distinct options, no distractor equals key, SPR answers pass the SPR validator, fixed-seed reproducibility, ~200 random seeds each.
- SPR input + validator (official rules, SAT_SPEC §4), KaTeX rendering, SVG charts/figures for data and geometry items.
- Topic Drill: skill-tree browser with per-node counts, pick nodes/difficulty/count, immediate feedback + step-by-step explanation + why each distractor is wrong. Responses stored from day one (they feed M5).
- Simple per-sub-skill accuracy shown in the tree (the full rating model lands in M5).

### M3: R&W seed bank + LLM pipeline
- Seed bank batch 1 (≥10 per sub-skill for high-weight sub-skills; rest completed by M5), JSON schema validated in tests.
- R&W renderer: passage/question split pane, tables/graphs for COE-Q, notes list for RS, Text 1/Text 2 for CTC.
- `app/generate` CLI: Anthropic API, strict JSON schema → independent blind-solve verification → reject on mismatch/ambiguity → near-duplicate filter (character n-gram Jaccard over stored passages) → insert. Uses seed items as style examples.
- "Report problem" button → quarantine.

### M4: Practice Exam
- Exam assembler: official module layout and ordering, pretest slots, difficulty profile per setting (Official-level / Hard / Brutal), never-seen-before items.
- Adaptive routing after Module 1 (threshold documented and configurable).
- Server-authoritative timer, autosave per change, module lock, break screen, resume after refresh/close.
- Tools: timer hide + unhideable 5-min warning, mark for review, navigator, review page, eliminator with undo, highlighter + notes, Desmos (`VITE_DESMOS_API_KEY`) with a math.js fallback, reference sheet.
- Results: section/total estimate (provisional mapping until M6), per-skill breakdown, time per question, full review.
- Playwright E2E: full exam flow including refresh mid-module and timer expiry.
- Dark mode is disabled here.
- *Shipped 2026-10-04.* Also: section choice (full / R&W only / Math only). Skipped: highlighter + notes. Weights/profiles/routing live in `backend/app/engine/exam.py` and `irt.py`.

### M5: Engine + Weakness Training + SRS + Mistake Notebook
- `engine/`: Elo/IRT-lite rating updates (ability per sub-skill, difficulty per item; time and eliminator-use adjustments), history; weakness score = f(mastery, exam weight, recent error rate, pace, decay) × 1.3 for Math; SRS intervals 1/3/7/14 days (correct extends, miss resets); selector targeting 60–70 % expected success.
- Weakness Training mode (untimed, stopwatch, miss-reason tags).
- Mistake Notebook with filters and "retry similar" (fresh generator variant or unseen same-sub-skill item).
- Seed bank completed to ≥10 per R&W sub-skill.
- *Shipped 2026-10-04:* everything above. Mastery is computed from responses on demand (Rasch with recency weights and partial credit), so `skill_mastery`/`mastery_history` stay unused; `review_schedule` holds the SRS state. Seed bank: ≥10 per R&W sub-skill.

### M6: Dashboard, score estimate, 9-week plan
- `docs/SCORING.md` + estimator calibrated to logged Bluebook results.
- Dashboard: countdown, score-estimate trend, mastery heatmap, top-5 weaknesses, progress bars to 1350 / Math 700 / 1550.
- Plan generator (rules-based from weakness scores and days remaining; weekly recompute; full exam weekly, twice weekly in final 3 weeks).
- Diagnostic offer on first login (Bluebook result entry *or* in-app exam).

### M7: Polish
- Network-loss queueing for autosave, edge cases (double-submit, expired module on resume), accessibility pass (focus order, ARIA on tools, contrast), performance, final docs.

## 4. Decisions I need from you

1. Approve/reject **P1–P5**.
2. App name (default: **"Apex Prep"**; no CB/Bluebook marks anywhere).
3. Do you already have a Desmos API key? (Without one, the math.js calculator fallback ships; Desmos requires a key for non-demo use.)
4. Anthropic API key available for M3? (Without one, R&W runs entirely on the seed bank.)
