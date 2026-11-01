---
id: testgen
order: 10
executor: agent
inputs: [projects/<project>/profile.json]
outputs: [testcases_final.json, dedupe-report.md, surefire/, coverage.txt, coverage-report.md, test-run.md]
gate: none
subskills: [ep-tests, bva-tests]
parameters: [project, target, mode]
---

# Role

You are the overarching test-generation skill. Given a project profile, a target, and a mode, you
produce a test suite that **passes with 100% branch coverage** — the complete testing lifecycle for
one target, not a slice of it. The orchestrator invokes you twice:

- `mode=generate, target=original` — derive the case set from scratch (assignment steps 1–7).
- `mode=adapt, target=refactored` — reuse the approved set against the refactored code (steps 10–12).

Two skills exist only as your subagents: `ep-tests` and `bva-tests`. Everything else — dedupe, the
human review gate, materializing JUnit, running, repairing, and the coverage gate — is a phase of
this skill.

# Parameters

| param | values | notes |
|-------|--------|-------|
| `project` | dir under `projects/` | default `seasonswitch` |
| `target` | `original` \| `refactored` | which code the tests hit |
| `mode` | `generate` \| `adapt` | see below |
| `feedback` | text | appended when re-run after a gate rejection |

# Hard rules

- Never weaken an assertion or delete a test to reach green. A failing test is input to the repair
  phase, never an obstacle.
- Apply every entry in `profile.constraints` to the tests you write.
- Never advance past a gate whose condition is false.
- Bounded loops: repair ≤ 5 iterations, gap-fill ≤ 5. On the sixth, stop and escalate to the human.
- Artifacts go to the run dir. Only `.java` sources go to `profile.test_root`.

# mode=generate

### Phase A — concurrent generation (assignment steps 1–2)

Spawn TWO subagents **in a single turn** so they run concurrently:

- `.agents/ep-tests/SKILL.md` → `testcases_ep.json`
- `.agents/bva-tests/SKILL.md` → `testcases_bva.json`

Neither reads the other's output. Waiting for both is the join. If your harness cannot run subagents
concurrently, run them in order and record that in `test-run.md` — never describe it as parallel.

### Phase B — join and dedupe (step 3)

Validate both outputs against `schemas/testcase-set.schema.json`. Merge into `testcases_final.json`,
removing duplicates under the profile's `dedupe_key`. Two cases with the same key but different
`expected` = a conflict, not a duplicate: record it and stop. `dedupe-report.md` lists every removed
case and its survivor, with counts in/out/removed.

### Gate G1 — human review (step 4)

Stop. Present `testcases_final.json` + `dedupe-report.md`. Record the decision in
`hitl_decisions.json` per `schemas/hitl_decision.schema.json`.

- accept → Phase C.
- request changes → Phase A again, feedback appended to both subagent briefs.

### Phase C — materialize (step 5, part)

Write JUnit to `profile.test_root`. One `@Test` per case, `@DisplayName` = id + partition. Assert
from the case's `expected`, never re-derived from the implementation.

### Phase D — run and repair (steps 5–6)

Run the suite via `profile.coverage.command` with `{target}` substituted. While tests fail: change
the code OR the tests — never both in one iteration — append one row per mutation to `changelog.md`,
re-run. Bound: 5.

### Phase E — coverage gate + gap-fill (step 7)

Compute branch coverage. Below `profile.coverage.threshold`: write `coverage-report.md`, derive one
`GAP-xx` case per uncovered branch, append to the case set, regenerate, back to Phase D. Bound: 5.

**Exit:** suite passes AND `pct >= threshold` on `target=original`.

# mode=adapt

### Phase A' — re-target, do not regenerate (step 10)

Take `testcases_final.json` and the existing test source. Produce `testcases_refactored.json`
(`target: refactored`) and a second test class. Test **logic is unchanged**; only the target,
imports, and setup wiring may change. Any change to an `expected` value needs a justification in
`refactor-notes.md`. The EP/BVA subagents are NOT spawned here — the approved set already exists.

### Phases D and E, on `target=refactored` (steps 11–12)

Same run/repair loop, same gate. For gap-fill, derive cases from the transition matrix in
`refactor-notes.md` rather than from scratch — every uncovered `(state, action)` cell needs a case.

**Exit:** suite passes AND `pct >= threshold` on `target=refactored`.

# Definition of done

- [ ] case files exist and are schema-valid
- [ ] `dedupe-report.md` accounts for every removed case (generate only)
- [ ] G1 recorded in `hitl_decisions.json` (generate only)
- [ ] `changelog.md` has one row per mutation, before/after + reason
- [ ] `coverage.txt` shows >= threshold for the target
- [ ] `test-run.md` states plainly what ran concurrently vs sequentially
