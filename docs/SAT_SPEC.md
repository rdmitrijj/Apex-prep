# Digital SAT Specification (as implemented by this app)

Verified on 2026-10-03 against official College Board sources. Where the project brief differed from those sources, the official source wins. Differences are listed in [§8](#8-discrepancies-vs-the-project-brief).

Sources:
- College Board, *Digital SAT Suite of Assessments Specifications Overview* (satsuite.collegeboard.org/media/pdf/digital-sat-test-spec-overview.pdf), Tables 1–4
- satsuite.collegeboard.org/sat/whats-on-the-test/structure
- satsuite.collegeboard.org/sat/whats-on-the-test/reading-writing
- Official student-produced response (SPR) directions shown in the Math section of the test
- Aalto admissions page for English-taught bachelor's programmes (high-school-diploma applicants), 2027 admissions

---

## 1. Structure and timing

| | Reading and Writing (R&W) | Math |
|---|---|---|
| Modules | 2, timed separately | 2, timed separately |
| Questions per module | 27 (25 operational + 2 pretest) | 22 (20 operational + 2 pretest) |
| Time per module | 32 min | 35 min |
| Section total | 54 questions, 64 min | 44 questions, 70 min |
| Question types | Discrete 4-option MC; one question per passage (or passage pair) | 4-option MC (about 75%) and SPR (about 25%) |
| Stimulus | 25–150 words; literature, history/social studies, humanities, science; tables, bar graphs, line graphs | Science, social science, real-world contexts; graphics allowed |

- **Order:** R&W Module 1 → R&W Module 2 → **10-minute break** → Math Module 1 → Math Module 2. Total testing time is **2 h 14 min**, not counting the break.
- **Pretest items** cannot be told apart from scored items and don't count. In the app, each module has 2 pretest slots. They are filled with fresh items, so we still collect difficulty data on them, but they are excluded from the score estimate.
- **Navigation:** you can move freely within a module. When a module's time runs out, the test advances automatically. **You cannot return to a module once it ends.**
- **Wrong answers carry no penalty.** The UI should push you to answer everything.

## 2. Multistage adaptive testing (MST)

- **Module 1** has a broad mix of easy, medium, and hard questions.
- **Module 2** is either harder or easier on average, depending on how you did in Module 1. Routing happens separately per section.
- College Board does **not** publish the routing rule or the score ceiling of the easier path. Students commonly report that the easier Module 2 caps a section score at around 600–650. **App assumption (configurable):** route to the harder Module 2 when the ability estimate after Module 1 is at least the threshold equivalent to about 60% expected correct on a medium item. The threshold and the easier-route cap (640) live in `backend/app/engine/irt.py`.
- **Within-module ordering (official):**
  - **R&W:** domains always appear in the order Craft and Structure → Information and Ideas → Standard English Conventions → Expression of Ideas. In CAS, INI, and EOI, questions on the same skill are grouped and ordered easiest to hardest. SEC questions are ordered easiest to hardest regardless of which convention they test.
  - **Math:** all four domains appear in every module, ordered easiest to hardest across the module.

## 3. Reading & Writing content

Official operational distribution across both modules (50 scored questions):

| Domain | Share | Questions | Skills (official testing points) |
|---|---|---|---|
| Craft and Structure | ≈28% | 13–15 | Words in Context; Text Structure and Purpose; Cross-Text Connections |
| Information and Ideas | ≈26% | 12–14 | Central Ideas and Details; Command of Evidence (Textual, Quantitative); Inferences |
| Standard English Conventions | ≈26% | 11–15 | Boundaries; Form, Structure, and Sense |
| Expression of Ideas | ≈20% | 8–12 | Rhetorical Synthesis; Transitions |

Sub-skills (for example the individual punctuation rules) are listed in `TAXONOMY.md`. They are our decomposition, not official categories.

**Question-stem conventions to mirror.** All items are original, so these are templates, not copied questions:
- WIC: "Which choice completes the text with the most logical and precise word or phrase?" / "As used in the text, what does the word ___ most nearly mean?"
- TSP: "Which choice best describes the function of the underlined sentence in the text as a whole?" / "...the main purpose of the text?"
- CTC: "Based on the texts, how would the author of Text 2 most likely respond to ...?"
- CID: "Which choice best states the main idea of the text?"
- COE-T: "Which finding, if true, would most directly support/weaken ...?" / "Which quotation from [work] most effectively illustrates the claim?"
- COE-Q: "Which choice most effectively uses data from the table/graph to complete the statement/example?"
- INF: "Which choice most logically completes the text?"
- SEC: "Which choice completes the text so that it conforms to the conventions of Standard English?"
- RS: "While researching a topic, a student has taken the following notes: [bullets]. The student wants to [goal]. Which choice most effectively uses relevant information from the notes to accomplish this goal?"
- TRN: "Which choice completes the text with the most logical transition?"

## 4. Math content

Official operational distribution across both modules (40 scored questions):

| Domain | Share | Questions | Skills (official testing points) |
|---|---|---|---|
| Algebra | ≈35% | 13–15 | Linear equations in one variable; linear equations in two variables; linear functions; systems of two linear equations in two variables; linear inequalities in one or two variables |
| Advanced Math | ≈35% | 13–15 | Equivalent expressions; nonlinear equations in one variable and systems of equations in two variables; nonlinear functions |
| Problem-Solving and Data Analysis | ≈15% | 5–7 | Ratios, rates, proportional relationships, and units; percentages; one-variable data (distributions, center, spread); two-variable data (models, scatterplots); probability and conditional probability; inference from sample statistics and margin of error; evaluating statistical claims (observational studies and experiments) |
| Geometry and Trigonometry | ≈15% | 5–7 | Area and volume; lines, angles, and triangles; right triangles and trigonometry; circles |

- **Calculator:** allowed on **every** Math question. A built-in Desmos graphing calculator is available, and students may bring an approved calculator.
- **Contexts:** word problems are deliberately short.

### SPR (student-produced response) entry rules, as enforced by the app

From the official directions:
1. If more than one answer is correct, enter only one.
2. A **positive** answer can be up to **5 characters**. A **negative** answer can be up to **6 characters**, including the minus sign.
3. If a fraction doesn't fit, enter its decimal equivalent.
4. If a decimal doesn't fit, **truncate or round at the fourth digit**.
5. Enter a mixed number (for example 3½) as an improper fraction (`7/2`) or a decimal (`3.5`). **`3 1/2` is not accepted.**
6. Don't enter symbols such as `%`, `,`, or `$`.

Official examples:
- For an answer of 2/3, `2/3`, `.6666`, `.6667`, `0.666`, and `0.667` are all accepted. `0.66`, `.66`, `0.67`, and `.67` are **not** accepted.
- For an answer of −1/3, `-1/3`, `-.3333`, and `-0.333` are accepted.

**Implementation:** an SPR item stores the exact answer (a SymPy rational or symbolic value) or a set of exact answers. The grader accepts the exact fraction, any equivalent fraction that fits the character limit, or a decimal that matches the exact value when truncated or rounded and **fills every available character**. Short decimals that lose precision are rejected, the same way the real test rejects them.

## 5. Testing-app features to reproduce (functional parity, original branding)

| Feature | Behavior |
|---|---|
| Timer | Counts down per module. Can be hidden. **A 5-minute alert always appears.** Auto-advances at 0:00. |
| Mark for review | Flag on any question in the current module |
| Question navigator | Grid of answered, unanswered, and flagged questions; click to jump |
| Review page | End-of-module summary before moving on |
| Annotation | Highlight passage or question text and attach a note (R&W and Math stems) |
| Option eliminator | Toggle mode that strikes out options (A–D); undo by clicking again |
| Graphing calculator | Embedded Desmos in a resizable/collapsible panel (Math only) |
| Reference sheet | Math formulas (below) |
| Line reader / zoom | Accessibility aids. Line reader is *nice-to-have*; browser zoom must not break the layout. |
| Break | 10 minutes between sections; can be ended early |
| Resilience | Work is saved if the connection drops or the device restarts, and the student resumes where they left off. Mirrored with server-side state. |

**Reference-sheet contents:** circle area πr² and circumference 2πr; rectangle area ℓw; triangle area ½bh; Pythagorean theorem c² = a² + b²; special right triangles 30-60-90 (x, x√3, 2x) and 45-45-90 (s, s, s√2); volumes of a rectangular prism ℓwh, cylinder πr²h, sphere (4/3)πr³, cone (1/3)πr²h, and pyramid (1/3)ℓwh. Also: there are 360° (2π radians) in a circle, and the angles of a triangle sum to 180°.

## 6. Scoring

- Section scores range from **200 to 800** in 10-point steps. The total, **400–1600**, is the sum of the two sections. There are no subscores.
- Raw score: 1 point per correct operational item, no penalty. Section scores come from **IRT-based scoring** that takes into account which items (and which Module 2) the student saw. Two students with the same raw score can get different scaled scores.
- **College Board publishes no raw-to-scale tables for the digital SAT**, because conversion is per form and proprietary. The app's estimate therefore has to be modeled. Implemented (`backend/app/engine/irt.py`): a Rasch ability estimate over the scored items, mapped linearly to 200–800 (θ 0 → 500, 110 points per logit; capped at 640 on the easier Module 2). The map is then **calibrated to your own official practice-test and real scores**, the only ground truth available: each is paired with the in-app exam closest in time (±14 days), and a Bayesian linear fit (prior: the default map; noise: ±30 official wobble plus the in-app estimate's error) re-maps every exam. Results show a one-SD ± margin. The UI always labels it "Estimate".

## 7. Your targets and constraints

- **Test date:** Saturday **5 December 2026**. Registration deadline is 20 Nov; late registration until 24 Nov. Scores are expected about 18 Dec.
- **Aalto, Bachelor's in Science and Technology, 2027 admission (high-school-diploma route):**
  - Total of at least **1350** *and* Math of at least **700**.
  - Ties are broken by Math. If you submit several valid tests, **the highest Math section score is used**.
  - Only tests taken **on or after 1 Jan 2025** count, and scores must arrive by **29 Jan 2027, 15:00 (UTC+2)**.
- **Implication:** the **7 Nov 2026** sitting (registration deadline 23 Oct, late deadline 27 Oct) also arrives before Aalto's deadline. It would give you two attempts. Check with Aalto whether the total must come from a single sitting.

## 8. Discrepancies vs. the project brief

| Brief said | Official / verified | Effect on the app |
|---|---|---|
| "about 2 unscored pretest items" per module | Exactly 25+2 (R&W) and 20+2 (Math) per module | Fixed module layout with 2 pretest slots |
| Domains and skills listed without order | R&W domain order is fixed (CAS → INI → SEC → EOI), skill-grouped, easy→hard; Math is easy→hard across the module | Exam assembler sorts items this way |
| Sub-skills such as coordinate adjectives, comma splices, etc. | Official spec lists only "Boundaries" and "Form, Structure, and Sense". Finer sub-skills are our decomposition. | Kept, but low-confidence weights |
| "Calibrate against published official score tables" | None exist for the digital SAT | Calibrate against your own Bluebook scores instead (see §6) |
| (not mentioned) | Aalto counts the **highest Math** across valid tests, and the Nov 7 sitting also qualifies | Recommend registering for Nov 7 as well (§7) |
