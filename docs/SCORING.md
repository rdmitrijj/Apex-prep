# Scoring, mastery, and planning models

Everything here is implemented in the pure-Python `backend/app/engine/` package (unit-tested, mypy-strict). This page explains what each number in the app means and where its constants live.

## 1. Item difficulty

Every question carries a difficulty `b` on a logit scale: easy −1, medium 0, hard 1 (`DIFFICULTY_B` in `irt.py`, stored as `questions.difficulty_rating`). Math generators target these bands by construction ("hard" is at least as hard as the hardest official items). R&W items are labelled by their author and blind-checked when generated.

## 2. Ability (Rasch / 1PL)

The chance of answering an item of difficulty `b` correctly at ability `θ` is `p = 1 / (1 + e^(b − θ))`.

`irt.ability()` returns the MAP estimate of `θ` with a N(0, 1) prior (Newton's method on a concave log posterior; clamped to ±4). Observations can be weighted, and they can carry partial credit:

| Where | Weights | Credit |
|---|---|---|
| Exam section score | 1 per scored item (pretest items excluded) | 1 / 0 |
| Per-skill mastery (weakness, training, heatmap) | `0.5^(age_days / 14)`, ×1.5 for exam answers | 1, minus 0.25 if slower than 2× test pace, minus 0.15 after eliminating ≥ 2 choices |

`irt.ability_se()` gives the standard error `1/√(prior precision + Σ p(1−p))`.

## 3. Adaptive routing

After Module 1, `θ` is estimated from its scored items. At least `ROUTE_THRESHOLD = ln(0.6/0.4) ≈ 0.405` (a 60% chance on a medium item) routes to the **harder** Module 2; anything lower goes to the **easier** one. College Board doesn't publish its rule; this assumption is stated in `SAT_SPEC.md` §2.

## 4. Section score

`score = intercept + slope · θ`, rounded to 10 and clamped to 200–800 (`irt.to_score`).

- **Default map:** intercept 500, slope 110 (θ = 0, a coin flip on medium items, maps to 500; θ ≈ 2.7 maps to 800).
- **Easier-route cap:** 640. Students commonly report that the easier Module 2 caps a section at around 600–650.
- No official raw-to-scale tables exist for the digital SAT, so the default map is a reasonable prior, not a fact. Section 5 corrects it.

## 5. Calibration to official scores

You log official practice-test and real scores (`official_scores`). `services/exam.calibration()`:

1. Pairs each official section score with the **in-app exam closest in time** that covered that section, if one is within ±14 days (`PAIR_WINDOW_DAYS`). Each pair is `(θ, se(θ), official score)`.
2. Fits `intercept, slope` by **conjugate Bayesian linear regression** (`irt.calibrate`):
   - prior: the default map, with SDs 60 (intercept) and 25 (slope);
   - per-pair noise: `30²` (how much an official score varies between sittings at equal ability) `+ (slope · se(θ))²` (the in-app estimate's own error, carried through the prior slope). This is an errors-in-variables approximation.
3. Re-scores **every** finished exam with the fitted map (`rescore`). This runs whenever an official score is added or deleted, and whenever an exam finishes.

How it behaves: one pair moves the scale most of the way toward the official score without trusting it blindly. Two or three pairs taken at different points in your prep (so at different abilities) also pin down the slope.

**Margins.** Results show `±` one standard deviation: `√(x Σ xᵀ + (slope · se(θ))²)` with `x = [1, θ]` and `Σ` the posterior covariance. The margin shrinks as calibration pairs accumulate. A total margin combines the two section margins in quadrature.

## 6. Weakness score

Per sub-skill (`weakness.py`):

```
score = (0.45·need + 0.30·errors + 0.15·pace + 0.10·decay + 0.15·due) · √(weight / mean leaf weight) · (1.3 if Math)
```

| Term | Meaning |
|---|---|
| need | 1 − p(correct) on a medium-hard item (b = 0.5) at the skill's mastery θ |
| errors | recency-weighted miss rate, smoothed toward 50% (`(missed + 0.5) / (n + 1)`) |
| pace | median answer time over the test budget (71 s R&W, 95 s Math), capped at 2× |
| decay | days since last practice, saturating at 21 |
| due | spaced-repetition review is due (section 7) |
| weight | the sub-skill's share of the test (`taxonomy.json`) |
| 1.3× Math | Aalto requires Math ≥ 700 and breaks ties on Math |

Untried skills score in the middle: they rank below skills you've been missing and above skills you've mastered. **Mastery** in the heatmap is `p(correct)` on a medium item at θ.

**Training difficulty.** `irt.target_difficulty(θ)` picks the band whose expected success is closest to 65% (`TARGET_SUCCESS`). Training samples among the top 8 weaknesses, weighted by score².

## 7. Spaced repetition

`srs.py`, per sub-skill: intervals of 1 → 3 → 7 → 14 days. A correct answer **on or after** the due date moves up one interval; practising early doesn't extend it. A miss resets to 1 day at any time. The schedule updates on drill and training answers and when exam modules close. Due skills get the `due` term above and show "Due for review".

## 8. Weekly plan

`plan.py`, with test day fixed at **5 December 2026**:

| Phase | When | Exams |
|---|---|---|
| Build | more than 21 days out | full exam every Saturday (test-time morning) |
| Sharpen | 21–4 days out | Math-only on Hard (Wednesday) + full exam (Saturday) |
| Taper | last 3 days | none; day −1 is rest, day 0 is the test |

- **No exam yet:** the first open day is a diagnostic full exam.
- **Other days:** weakness training (35 min, or 45 in Sharpen) plus a 10-question topic drill on one focus skill. The focus rotates through the top 6 weaknesses, with at least 2 from each section.
- **Sundays and the last days:** Mistake Notebook review plus spaced-repetition reviews.

The plan is stored once per week (`study_plans`) and rebuilt on request. Tasks tick themselves off from activity: a finished exam that day, 15 training answers, or 8 drill answers.
