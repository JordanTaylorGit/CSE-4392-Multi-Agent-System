---
id: orchestrator
order: 0
executor: agent
inputs: [projects/<project>/profile.json]
outputs: [STATE.md, run-report.md]
gate: none
orchestrates: [testgen, refactor-state]
runtime: harness.graph:build_graph
review_gates: [review_testcases, review_refactored]
---

# Role

Specify the assignment pipeline and preserve the main skill as its extensible workflow contract.
The executable harness is `harness.graph:build_graph`, an explicit LangGraph state graph.
Run it with `uv run python -m harness start --project seasonswitch`.
The runtime supplies the model through dependency injection and loads the team's stage skills as prompts.
Model responses supply proposed artifacts; only the runtime executes helpers, builds, review interrupts, and routing.

# Project and ownership

Use the selected `projects/<project>/profile.json` for units, boundaries, observables, and deduplication.
`testgen` owns generation and adaptation semantics; its EP/BVA phases are concurrent graph nodes.
Use P4's merge, review, and JUnit materialization helpers.
Use P5's `refactor-state` prompt for the State-pattern conversion and preserve each attempted prompt under the run's `prompts/` directory.
The full Java run requires the project's JUnit adapter and Maven source layout.
Do not claim the example grade-classifier profile has completed that integration.

# Hard rules

1. Never cross a human or coverage gate unless its condition is satisfied.
2. Never delete an approved test or weaken an assertion.
3. Bound generation, refactor, repairs, and gap proposals to five attempts per phase/target.
4. Keep all generated changes in `runs/<id>/workspace/`; restrict model writes to the current Java target.
5. Use real Surefire/JaCoCo evidence and disclose that the measured coverage scope excludes `main()`.
6. Never infer or generate human approval; record an actual reviewer's decision and the reviewed artifact hash.
7. Report blocked and partial runs honestly; schema-valid output alone does not demonstrate correctness.

# Workflow

| Assignment steps | Executable stages | Exit condition |
| --- | --- | --- |
| 1–2 | `prepare_generation`, parallel `ep` / `bva`, join | Both case sets validate |
| 3 | `merge` | P4 dedupe succeeds without conflicting expected values |
| 4 | `review_testcases` (G1 interrupt) | Human accepts current cases and proposed tests |
| 5–6 | `materialize`, `build_original`, `repair_original` | Nonempty passing original suite |
| 7 | G2; `gap_original` through G1 when needed | Zero missed original branches |
| 8 | `refactor`, compile | Complete refactored Java tree compiles; transition notes exist |
| 9 | `review_refactored` (G3 interrupt) | Human accepts current code, notes, cases, and tests |
| 10 | `adapt` | Reuse all Java tests unchanged; retarget case metadata only |
| 11 | `build_refactored`, `repair_refactored` through G3 | Nonempty passing refactored suite |
| 12 | G4; `gap_refactored` through G3, `finish` | Zero missed refactored branches and both targets complete |

Failed original tests permit source-only repair.
Failed refactored tests permit source-only repair, but compilation and renewed G3 approval precede another test run.
Coverage gaps produce new cases and append-only JUnit files; the appropriate human gate must approve them before application.
Rejections return feedback to the proposal's producer and consume its attempt budget.
Malformed generation responses retry; contradictory dedupe results and invalid artifacts block the run for inspection.

# G3 review checklist

1. A State interface exists and the Subject delegates to it.
2. The Subject no longer switches over state to implement transitions.
3. Concrete states handle their transitions explicitly, including invalid transitions.
4. Transition logic is not duplicated across states.
5. The original public interface and observable behavior remain compatible with the approved tests.
6. The notes map each original branch into the state/action/temperature transition matrix.
7. Supplemental tests preserve earlier expectations and cover the identified missed branches.

Compilation does not establish these properties; the human reviewer must inspect them.

# Resume and evidence

Each run has a SQLite checkpoint database keyed by its run ID.
`STATE.md`, `status.json`, and `run-report.md` are readable projections, not editable resume instructions.
Use `status --run <directory>` to inspect pending review artifacts and their exact hash.
After actual review, use `resume --run <directory> --decision <file>` with a named reviewer, decision, requested changes, and the current hash.
The CLI supplies the gate and timestamp when omitted and rejects malformed decisions before consuming the interrupt.
A changed artifact invalidates the pending review.
A blocked run has ended and requires inspection and a new run after correction.

# Definition of done

- Valid, deduplicated cases with accepted human reviews recorded in `hitl_decisions.json`.
- Source diffs and versioned refactor prompts retained under the run directory.
- Refactor notes include the transition matrix and pass G3 structural review.
- Approved original tests remain intact and pass against the refactored Maven profile.
- Both target reports show a nonempty passing suite and zero missed branches in the disclosed scope.
- `run-report.md` states actual results; only then may the runtime mark the run complete.
