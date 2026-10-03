# Skill Taxonomy

Source of truth: `backend/app/seed/taxonomy.json` (this file mirrors it; change the JSON first).

Every question, response, and mastery row references a **leaf** (`subskill`) ID. Domains and skills aggregate their leaves.

- **ID format:** `SECTION.DOMAIN.SKILL.SUBSKILL`, e.g. `MATH.ADV.NLF.VERTEX`.
- **weight** = estimated share of that section's operational questions. Domain weights are official (College Board spec). Skill weights are *our estimates* from official practice-test frequency and are meant to be refined with real data. Sub-skill weights split their skill evenly.
- **Difficulty bands:** every leaf is targeted at `easy`, `medium`, and `hard`. Band boundaries on the rating scale are defined in `docs/SCORING.md` (milestone 5).
- **Formats:** R&W leaves are 4-option MC only. Math leaves allow MC and SPR (target mix about 75/25).
- **Math priority:** the engine multiplies Math weakness scores by `math_priority_multiplier` (default 1.3).


## Reading and Writing (`RW`)


### Craft and Structure (`RW.CAS`): 28% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Words in Context** | `RW.CAS.WIC` | 16.0% |
| &nbsp;&nbsp;↳ Most logical and precise word/phrase (blank) | `RW.CAS.WIC.FILL` | 8.00% |
| &nbsp;&nbsp;↳ Meaning of a word as used in the text | `RW.CAS.WIC.MEANING` | 8.00% |
| **Text Structure and Purpose** | `RW.CAS.TSP` | 8.0% |
| &nbsp;&nbsp;↳ Main purpose of the text | `RW.CAS.TSP.PURPOSE` | 2.67% |
| &nbsp;&nbsp;↳ Overall structure of the text | `RW.CAS.TSP.STRUCTURE` | 2.67% |
| &nbsp;&nbsp;↳ Function of an underlined sentence/portion | `RW.CAS.TSP.FUNCTION` | 2.67% |
| **Cross-Text Connections** | `RW.CAS.CTC` | 4.0% |
| &nbsp;&nbsp;↳ How author of Text 2 would respond to Text 1 | `RW.CAS.CTC.RESPONSE` | 4.00% |

### Information and Ideas (`RW.INI`): 26% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Central Ideas and Details** | `RW.INI.CID` | 6.0% |
| &nbsp;&nbsp;↳ Main idea | `RW.INI.CID.MAIN` | 3.00% |
| &nbsp;&nbsp;↳ Supporting detail | `RW.INI.CID.DETAIL` | 3.00% |
| **Command of Evidence: Textual** | `RW.INI.COET` | 6.0% |
| &nbsp;&nbsp;↳ Finding that supports a claim | `RW.INI.COET.SUPPORT` | 2.00% |
| &nbsp;&nbsp;↳ Finding that weakens a claim | `RW.INI.COET.WEAKEN` | 2.00% |
| &nbsp;&nbsp;↳ Quotation that illustrates a claim (literary) | `RW.INI.COET.QUOTE` | 2.00% |
| **Command of Evidence: Quantitative** | `RW.INI.COEQ` | 7.0% |
| &nbsp;&nbsp;↳ Data from a table | `RW.INI.COEQ.TABLE` | 2.33% |
| &nbsp;&nbsp;↳ Data from a bar graph | `RW.INI.COEQ.BAR` | 2.33% |
| &nbsp;&nbsp;↳ Data from a line graph | `RW.INI.COEQ.LINE` | 2.33% |
| **Inferences** | `RW.INI.INF` | 7.0% |
| &nbsp;&nbsp;↳ Most logical completion of the text | `RW.INI.INF.COMPLETE` | 7.00% |

### Standard English Conventions (`RW.SEC`): 26% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Boundaries** | `RW.SEC.BND` | 13.0% |
| &nbsp;&nbsp;↳ End-of-sentence punctuation | `RW.SEC.BND.END` | 1.44% |
| &nbsp;&nbsp;↳ Linking independent clauses (comma splice, run-on, semicolon, conjunction) | `RW.SEC.BND.LINK` | 1.44% |
| &nbsp;&nbsp;↳ Supplementary/nonessential elements (comma, dash, parenthesis pairs) | `RW.SEC.BND.SUPP` | 1.44% |
| &nbsp;&nbsp;↳ Colons and dashes before lists/explanations | `RW.SEC.BND.COLON` | 1.44% |
| &nbsp;&nbsp;↳ Items in a series | `RW.SEC.BND.SERIES` | 1.44% |
| &nbsp;&nbsp;↳ Introductory elements | `RW.SEC.BND.INTRO` | 1.44% |
| &nbsp;&nbsp;↳ Coordinate adjectives | `RW.SEC.BND.COORDADJ` | 1.44% |
| &nbsp;&nbsp;↳ Unnecessary punctuation (subject-verb, verb-object, before restrictive clause) | `RW.SEC.BND.UNNEC` | 1.44% |
| &nbsp;&nbsp;↳ Fragments | `RW.SEC.BND.FRAG` | 1.44% |
| **Form, Structure, and Sense** | `RW.SEC.FSS` | 13.0% |
| &nbsp;&nbsp;↳ Subject-verb agreement (intervening phrases, inverted order, collective/indefinite subjects) | `RW.SEC.FSS.SVA` | 1.86% |
| &nbsp;&nbsp;↳ Pronoun-antecedent agreement | `RW.SEC.FSS.PAA` | 1.86% |
| &nbsp;&nbsp;↳ Pronoun case | `RW.SEC.FSS.PCASE` | 1.86% |
| &nbsp;&nbsp;↳ Verb tense and aspect | `RW.SEC.FSS.TENSE` | 1.86% |
| &nbsp;&nbsp;↳ Finite vs. nonfinite verb forms | `RW.SEC.FSS.FINITE` | 1.86% |
| &nbsp;&nbsp;↳ Plurals and possessives | `RW.SEC.FSS.POSS` | 1.86% |
| &nbsp;&nbsp;↳ Modifier placement / dangling modifiers | `RW.SEC.FSS.MOD` | 1.86% |

### Expression of Ideas (`RW.EOI`): 20% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Rhetorical Synthesis** | `RW.EOI.RS` | 12.0% |
| &nbsp;&nbsp;↳ Use notes to accomplish a stated goal | `RW.EOI.RS.GOAL` | 12.00% |
| **Transitions** | `RW.EOI.TRN` | 8.0% |
| &nbsp;&nbsp;↳ Contrast / concession | `RW.EOI.TRN.CONTRAST` | 2.67% |
| &nbsp;&nbsp;↳ Cause and effect | `RW.EOI.TRN.CAUSE` | 2.67% |
| &nbsp;&nbsp;↳ Continuation (addition, example, restatement, sequence) | `RW.EOI.TRN.CONT` | 2.67% |

## Math (`MATH`)


### Algebra (`MATH.ALG`): 35% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Linear equations in one variable** | `MATH.ALG.LIN1` | 6.0% |
| &nbsp;&nbsp;↳ Solve a linear equation | `MATH.ALG.LIN1.SOLVE` | 2.00% |
| &nbsp;&nbsp;↳ No / infinitely many solutions | `MATH.ALG.LIN1.NSOL` | 2.00% |
| &nbsp;&nbsp;↳ Create/interpret from context | `MATH.ALG.LIN1.MODEL` | 2.00% |
| **Linear equations in two variables** | `MATH.ALG.LIN2` | 6.0% |
| &nbsp;&nbsp;↳ Interpret slope/intercept in context | `MATH.ALG.LIN2.INTERP` | 2.00% |
| &nbsp;&nbsp;↳ Solutions satisfying the equation | `MATH.ALG.LIN2.SOLN` | 2.00% |
| &nbsp;&nbsp;↳ Create from context | `MATH.ALG.LIN2.MODEL` | 2.00% |
| **Linear functions** | `MATH.ALG.LINF` | 10.0% |
| &nbsp;&nbsp;↳ Slope/intercept from points, table, or graph | `MATH.ALG.LINF.SLOPE` | 2.50% |
| &nbsp;&nbsp;↳ Function notation and evaluation | `MATH.ALG.LINF.NOTATION` | 2.50% |
| &nbsp;&nbsp;↳ Parallel and perpendicular lines | `MATH.ALG.LINF.PARPERP` | 2.50% |
| &nbsp;&nbsp;↳ Interpret/create linear function in context | `MATH.ALG.LINF.MODEL` | 2.50% |
| **Systems of two linear equations** | `MATH.ALG.SYS` | 7.0% |
| &nbsp;&nbsp;↳ Solve (substitution/elimination) | `MATH.ALG.SYS.SOLVE` | 2.33% |
| &nbsp;&nbsp;↳ Number of solutions (none/infinite) | `MATH.ALG.SYS.NSOL` | 2.33% |
| &nbsp;&nbsp;↳ Create/interpret from context | `MATH.ALG.SYS.MODEL` | 2.33% |
| **Linear inequalities in one or two variables** | `MATH.ALG.INEQ` | 6.0% |
| &nbsp;&nbsp;↳ Solve a linear inequality | `MATH.ALG.INEQ.SOLVE` | 2.00% |
| &nbsp;&nbsp;↳ Solution regions / points satisfying | `MATH.ALG.INEQ.GRAPH` | 2.00% |
| &nbsp;&nbsp;↳ Create from context | `MATH.ALG.INEQ.MODEL` | 2.00% |

### Advanced Math (`MATH.ADV`): 35% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Equivalent expressions** | `MATH.ADV.EQX` | 10.0% |
| &nbsp;&nbsp;↳ Expand/factor polynomials | `MATH.ADV.EQX.POLY` | 2.50% |
| &nbsp;&nbsp;↳ Exponent and radical rules | `MATH.ADV.EQX.EXP` | 2.50% |
| &nbsp;&nbsp;↳ Rational expressions | `MATH.ADV.EQX.RATIONAL` | 2.50% |
| &nbsp;&nbsp;↳ Rearrange formulas (isolate a quantity) | `MATH.ADV.EQX.REARR` | 2.50% |
| **Nonlinear equations in one variable and systems** | `MATH.ADV.NLEQ` | 11.0% |
| &nbsp;&nbsp;↳ Solve quadratics (factor, formula, completing square) | `MATH.ADV.NLEQ.QUAD` | 2.20% |
| &nbsp;&nbsp;↳ Discriminant / number of solutions | `MATH.ADV.NLEQ.DISC` | 2.20% |
| &nbsp;&nbsp;↳ Radical and rational equations (extraneous roots) | `MATH.ADV.NLEQ.RADRAT` | 2.20% |
| &nbsp;&nbsp;↳ Absolute value equations | `MATH.ADV.NLEQ.ABS` | 2.20% |
| &nbsp;&nbsp;↳ Linear-quadratic systems | `MATH.ADV.NLEQ.SYS` | 2.20% |
| **Nonlinear functions** | `MATH.ADV.NLF` | 14.0% |
| &nbsp;&nbsp;↳ Quadratic forms: vertex, standard, factored | `MATH.ADV.NLF.VERTEX` | 2.33% |
| &nbsp;&nbsp;↳ Exponential growth/decay models | `MATH.ADV.NLF.EXPF` | 2.33% |
| &nbsp;&nbsp;↳ Polynomial zeros, factors, remainder theorem | `MATH.ADV.NLF.POLYZ` | 2.33% |
| &nbsp;&nbsp;↳ Function notation and composition | `MATH.ADV.NLF.NOTATION` | 2.33% |
| &nbsp;&nbsp;↳ Graph transformations | `MATH.ADV.NLF.TRANSF` | 2.33% |
| &nbsp;&nbsp;↳ Rational/radical function behavior | `MATH.ADV.NLF.RATRAD` | 2.33% |

### Problem-Solving and Data Analysis (`MATH.PSD`): 15% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Ratios, rates, proportional relationships, and units** | `MATH.PSD.RAT` | 2.5% |
| &nbsp;&nbsp;↳ Ratios and proportions | `MATH.PSD.RAT.PROP` | 1.25% |
| &nbsp;&nbsp;↳ Unit rates and conversions | `MATH.PSD.RAT.UNITS` | 1.25% |
| **Percentages** | `MATH.PSD.PCT` | 3.0% |
| &nbsp;&nbsp;↳ Percent of / percent change | `MATH.PSD.PCT.BASIC` | 1.50% |
| &nbsp;&nbsp;↳ Successive percent changes, reverse percent | `MATH.PSD.PCT.SUCC` | 1.50% |
| **One-variable data: distributions, center and spread** | `MATH.PSD.ONEVAR` | 2.5% |
| &nbsp;&nbsp;↳ Mean/median, effect of changes/outliers | `MATH.PSD.ONEVAR.CENTER` | 0.83% |
| &nbsp;&nbsp;↳ Range / standard deviation comparison | `MATH.PSD.ONEVAR.SPREAD` | 0.83% |
| &nbsp;&nbsp;↳ Histograms, dot plots, box plots | `MATH.PSD.ONEVAR.DISPLAY` | 0.83% |
| **Two-variable data: models and scatterplots** | `MATH.PSD.TWOVAR` | 2.5% |
| &nbsp;&nbsp;↳ Line of best fit: predict and interpret | `MATH.PSD.TWOVAR.FIT` | 1.25% |
| &nbsp;&nbsp;↳ Linear vs. exponential models | `MATH.PSD.TWOVAR.MODELTYPE` | 1.25% |
| **Probability and conditional probability** | `MATH.PSD.PROB` | 2.5% |
| &nbsp;&nbsp;↳ Simple probability | `MATH.PSD.PROB.BASIC` | 1.25% |
| &nbsp;&nbsp;↳ Conditional probability from two-way tables | `MATH.PSD.PROB.COND` | 1.25% |
| **Inference from sample statistics and margin of error** | `MATH.PSD.INFER` | 1.0% |
| &nbsp;&nbsp;↳ Margin of error and population inference | `MATH.PSD.INFER.MOE` | 1.00% |
| **Evaluating statistical claims: observational studies and experiments** | `MATH.PSD.CLAIMS` | 1.0% |
| &nbsp;&nbsp;↳ Random sampling vs. random assignment; generalization and causation | `MATH.PSD.CLAIMS.DESIGN` | 1.00% |

### Geometry and Trigonometry (`MATH.GEO`): 15% of section

| Skill / sub-skill | ID | Weight |
|---|---|---|
| **Area and volume** | `MATH.GEO.AV` | 4.0% |
| &nbsp;&nbsp;↳ Area and perimeter of plane figures | `MATH.GEO.AV.AREA` | 1.33% |
| &nbsp;&nbsp;↳ Volume and surface area of solids | `MATH.GEO.AV.VOL` | 1.33% |
| &nbsp;&nbsp;↳ Effect of scaling on area/volume | `MATH.GEO.AV.SCALE` | 1.33% |
| **Lines, angles, and triangles** | `MATH.GEO.LAT` | 4.0% |
| &nbsp;&nbsp;↳ Parallel lines and angle relationships | `MATH.GEO.LAT.ANGLES` | 1.33% |
| &nbsp;&nbsp;↳ Triangle angle sums, isosceles/equilateral | `MATH.GEO.LAT.TRI` | 1.33% |
| &nbsp;&nbsp;↳ Similarity and congruence | `MATH.GEO.LAT.SIMCONG` | 1.33% |
| **Right triangles and trigonometry** | `MATH.GEO.RTT` | 4.0% |
| &nbsp;&nbsp;↳ Pythagorean theorem and special right triangles | `MATH.GEO.RTT.PYTH` | 1.33% |
| &nbsp;&nbsp;↳ Sine, cosine, tangent | `MATH.GEO.RTT.TRIG` | 1.33% |
| &nbsp;&nbsp;↳ sin(x) = cos(90° − x) and related identities | `MATH.GEO.RTT.COFUNC` | 1.33% |
| **Circles** | `MATH.GEO.CIR` | 3.0% |
| &nbsp;&nbsp;↳ Arc length, sectors, radians | `MATH.GEO.CIR.ARC` | 1.00% |
| &nbsp;&nbsp;↳ Equation of a circle (incl. completing the square) | `MATH.GEO.CIR.EQN` | 1.00% |
| &nbsp;&nbsp;↳ Central/inscribed angles, tangents, chords | `MATH.GEO.CIR.ANGLE` | 1.00% |

**Totals:** 30 skills, 91 sub-skills (35 R&W, 56 Math).
