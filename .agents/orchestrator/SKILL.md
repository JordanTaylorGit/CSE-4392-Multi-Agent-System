---
id: orchestrator
order: 0
executor: agent
inputs: [projects/<project>/profile.json]
outputs: [STATE.md, run-report.md]
gate: none
orchestrates: [testgen, refactor-state]
---

# Role

You are the go button for the assignment-3 pipeline. This file is the program. You dispatch exactly
three skills and own the gates between them:

- `.agents/testgen/SKILL.md` — invoked **twice**: `mode=generate` on the original code, `mode=adapt`
  on the refactored code.
- `.agents/refactor-state/SKILL.md` — invoked once, between the two testgen runs.

You do not write tests or Java yourself. You do not spawn the EP/BVA subagents — `testgen` does that
internally, and its two subagents read `.agents/ep-tests/SKILL.md` and `.agents/bva-tests/SKILL.md`
directly.

# Project

The run targets the project named in `projects/<project>/profile.json`. Default: `seasonswitch`.
The test-generation skills read the profile for units, observable outputs, boundaries, and the
dedupe key, and name no domain of their own. To demonstrate that generality, `testgen` may be pointed
at `projects/grade-classifier` unchanged — record the result in `run-report.md`.

# Hard rules

1. **Never cross a gate whose condition is false.** The gates are G1 (inside testgen), G2 (inside
   testgen), and G3 (yours, step 3 below).
2. **Never delete a test or weaken an assertion.** Pass this down to every stage you dispatch.
3. **Bounded loops.** No phase or gate exceeds 5 iterations; on the sixth, stop and ask the human.
4. **Artifacts go to `runs/<RUN_ID>/`.** Only generated `.java` files go into `java/src/`.
5. **Report what you did.** If anything was skipped or run sequentially that should have been
   parallel, `run-report.md` says so.

# Run setup

```
RUN_ID   = current UTC time, format YYYYMMDDTHHMMSSZ
RUN_DIR  = runs/<RUN_ID>
```

Create `RUN_DIR`, then create `STATE.md` from `templates/STATE.md` and fill in the run id. Update it
after every step — it is the resume point if the session dies.

# Resume protocol

Before step 1: if the human names a run dir, use it; else if `runs/` has a `STATE.md` with
`status: in_progress`, ask whether to resume it. On resume, continue from `current_step`.

# The pipeline

### Step 1 — `testgen(mode=generate, target=original)`

Internally: spawns `ep-tests` and `bva-tests` subagents concurrently, joins, dedupes, stops at **G1**
for the human review of test cases, writes JUnit, runs, repairs, and gates on 100% branch coverage.

**Exit:** passing suite + `pct >= profile.coverage.threshold` on `target=original`.

### Step 2 — `refactor-state`

Applies the State pattern via the prompt-mutation protocol in `docs/prompt-mutations/`.

**Exit:** refactored sources compile under `mvn -P refactored`, and `refactor-notes.md` contains the
full `(state, action, temp-regime)` transition matrix.

### Step 3 — Gate G3: human review of the refactored code

Run the checklist below against the refactored sources, then present `refactor-review.md` to the
human. Record in `hitl_decisions.json`.

1. A `SeasonState` interface exists and `SeasonSwitch` delegates to it.
2. No `if`/`switch` chain over state remains in the Subject.
3. Each concrete state handles its own transition.
4. Invalid transitions are handled explicitly, not by falling through.
5. No duplicated transition logic across states.
6. Public interface identical to the original — same class name, same methods.
7. Every original branch maps to a state or transition in `refactor-notes.md`.

- accept → step 4.
- request changes → step 2 with the reviewer's notes as a new prompt mutation. Bound: 5.

### Step 4 — `testgen(mode=adapt, target=refactored)`

Reuses the approved case set. **Exit:** passing suite + 100% branch coverage on `target=refactored`.

### Step 5 — Halt

Write `run-report.md`, set `STATE.md` to `status: complete`, and report: test counts and coverage for
both targets, gate iteration counts, the winning refactor prompt version, and anything skipped.

# Mapping to the assignment's 12 steps

| assignment step | where it happens |
|-----------------|------------------|
| 1–2 EP + BVA parallel, join | testgen Phase A/B |
| 3 dedupe | testgen Phase B |
| 4 HITL test review | G1 inside testgen |
| 5–6 run tests, repair loop | testgen Phase C/D |
| 7 original coverage == 100% | testgen Phase E |
| 8 state-pattern refactor | refactor-state |
| 9 HITL refactor review | G3, this file |
| 10 adapt tests | testgen mode=adapt Phase A' |
| 11 refactored coverage | testgen Phase E |
| 12 gap-fill until 100% | testgen Phase E |

# Definition of done

- [ ] `testcases_ep.json` + `testcases_bva.json` valid against the set schema
- [ ] `testcases_final.json` has no duplicate `dedupe_key` tuples
- [ ] `hitl_decisions.json` records accepts at G1 and G3
- [ ] `changelog.md` has one row per mutation
- [ ] `coverage.txt` shows 100.0 for `original` and `refactored`
- [ ] `refactor-notes.md` contains the full transition matrix
- [ ] `docs/prompt-mutations/` holds every prompt version tried
- [ ] the original tests pass re-targeted against the refactored code
- [ ] `run-report.md` states what was skipped, if anything

Any unchecked box means the run is not done. Say so.
