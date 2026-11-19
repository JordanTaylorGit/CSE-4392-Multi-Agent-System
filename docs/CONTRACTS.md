# Frozen contracts

Change these only by group sign-off. Everything else is negotiable.

## 1. Skill frontmatter

Each stage directory under `.agents/` except `_template` declares its skill contract.
`scripts/validate_skills.py` checks those declarations in CI.
The orchestrator skill specifies the workflow, and `harness/graph.py` executes it with LangGraph.
Existing required fields and JSON schemas remain unchanged.

| key | required | meaning |
|-----|----------|---------|
| `id` | yes | unique; matches the stage directory |
| `order` | yes | integer; execution order |
| `executor` | yes | `agent` or `llm` |
| `inputs` | yes | paths, `root:`-prefixed for repo files, otherwise run-dir relative |
| `outputs` | yes | paths written into the run dir, or `root:`-prefixed for source files |
| `gate` | yes | `none` or `human` |
| `gate_id` | no | `review_testcases` / `review_refactored` |
| `on_reject` | no | stage id to loop back to |
| `parallel_group` | no | stages sharing a group are declared concurrent |
| `schema` | no | JSON schema the outputs must validate against |
| `orchestrates` | no | stage ids this stage dispatches (orchestrator only) |
| `subskills` | no | skill ids this stage may spawn as subagents |
| `parameters` | no | named inputs the dispatcher supplies (e.g. `target`, `mode`) |
| `runtime` | no | orchestrator Python entry point (`module:function`) |
| `review_gates` | no | human gates implemented by the runtime |

Rules:
- A stage writes only its own `outputs`. Anything else is a contract violation.
- Subagents must not read each other's outputs — the parent joins them.
- Loop routing is explicit in the orchestrator specification and executable graph; models do not control retries.
- Source outputs are resolved within the per-run workspace; model writes are restricted to the current Java source target.
- EP/BVA remain the two generation phases of `testgen`; the runtime schedules them as parallel graph nodes.

## 2. Test case shape

See `schemas/testcase.schema.json`. It is deliberately project-agnostic: `setup`, `inputs`, and
`expected` are free-form objects whose vocabulary comes from the project profile. That is what lets
one schema describe a stateless function and a stateful object.

## 2a. Project profile

`projects/<project>/profile.json` supplies everything a test skill needs to know about a project:
`units`, `state_variables`, `observable`, `boundaries`, `dedupe_key`, `coverage`, `constraints`.
Contract and rationale: `projects/README.md`.

`dedupe_key` is the important one. Duplicate detection is only correct if it compares the fields that
fully determine the outcome, and that set differs per project — `["inputs"]` for a pure function,
`["unit", "setup", "inputs"]` for a stateful object.

Rules:
- A test skill must not name a unit, threshold, or domain. If it does, it is project-specific and
  broken.
- `scripts/validate_skills.py` checks every profile for required keys and a matching `project` name.

## 3. Run directory

```text
runs/<UTC>-<unique-suffix>/
  run.json                     # project and source-repository metadata
  checkpoints.sqlite           # authoritative LangGraph state and pending interrupts
  STATE.md  status.json         # regenerated state projections
  run-report.md  coverage.txt   # measured results and disclosed scope
  workspace/                   # isolated copy of skills, profiles, schemas, and Java
    java/src/{original,refactored,test}/java/
  testcases_ep.json  testcases_bva.json  testcases_final.json
  testcases_refactored.json     # approved cases with refactored target metadata
  testcases_proposed.json       # pending supplemental cases; not approval
  dedupe-report.md  hitl_decisions.json
  refactor-notes.md  changelog.md
  prompts/refactor-vN.json
  transcripts/<stage>-<id>.json
  changes/<id>.diff
  <target>/attempt-<N>/        # Maven log, Surefire reports, jacoco.xml
  compile-<attempt>.log         # refactor compilation evidence
```

`hitl_decisions.json` and `STATE.md` are evidence; do not hand-edit them.
The runtime creates artifacts when their stages execute, so a paused run will not contain later-stage outputs.
The target-specific directories preserve each attempt rather than overwriting a single top-level coverage report.

## 4. Runtime and decisions

Run `uv run python -m harness start --project seasonswitch`.
Use `status --run <directory>` to inspect and `resume --run <directory> --decision <file>` to submit an actual human review.
See the README for installation and decision examples.
SQLite checkpoints replace manual step-number resume.
The main skill remains the workflow specification and is retained for future expansion.

The decision shape remains `schemas/hitl_decision.schema.json`.
The harness additionally requires a nonblank reviewer and an exact current `artifact_sha256`.
An acceptance has an empty `requested_changes` array; a rejection requires nonblank change requests.
G1 hashes the reviewed case bytes, matching P4's helper, and separately guards the surrounding artifacts with a checkpointed fingerprint.
G3 hashes source, notes, tests, and case files together.
No model can supply a human approval, and a stale pending review cannot authorize changed files.

GAP proposals use the existing `GAP` method and schema.
They may refer to uncovered callback methods identified in JaCoCo beyond the initial EP/BVA profile vocabulary.
New JUnit files must end in `Test.java`, remain append-only, and pass the appropriate G1/G3 review before use.
Cases and expected values approved earlier remain intact through adaptation and subsequent retries.

## 5. Build and completion

- JDK 17 and Maven; the harness runs `mvn -B -P <target> clean test jacoco:report`.
- `scripts/coverage.sh <target>` remains P3's standalone helper.
- Both targets require actual passing tests and zero missed method-level branches, excluding `main()` as in P3's scope.
- Missing reports, skipped tests, an empty suite, or zero measurable branches cannot pass.
- The original JUnit suite is reused unchanged against the refactored source root.
- Generation, refactor, repairs, and gap proposals each have a five-attempt budget per applicable phase/target.
- A run is complete only after both measured coverage gates pass and required human reviews have been recorded.

The lint script checks declarations, schemas, profiles, and the declared runtime function.
It does not execute stages or prove that the assignment pipeline has completed.
