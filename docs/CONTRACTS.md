# Frozen contracts

Change these only by group sign-off. Everything else is negotiable.

## 1. Skill frontmatter

Every file in `.agents/` except `_TEMPLATE.md` declares the graph. `scripts/validate_skills.py`
checks it in CI; the orchestrator skill (`.agents/orchestrator/SKILL.md`) executes it.

| key | required | meaning |
|-----|----------|---------|
| `id` | yes | unique; matches the filename stem |
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

Rules:
- A stage writes only its own `outputs`. Anything else is a contract violation.
- Subagents must not read each other's outputs — the parent joins them.
- Loops are declared with `on_reject`, never implemented ad hoc inside a skill.
- `root:` outputs are the only way a stage may touch `java/src/`.
- `ep-tests` and `bva-tests` are only ever invoked by `testgen`, never by the orchestrator.

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

```
runs/<UTC>/
  STATE.md                   <- resume point, updated after every step
  run-report.md
  testcases_ep.json  testcases_bva.json  testcases_final.json
  testcases_refactored.json  testcases_extra.json
  surefire/          jacoco.xml  coverage.txt
  changelog.md       hitl_decisions.json  refactor-review.md
  refactor-notes.md  dedupe-report.md
```

`hitl_decisions.json` and `STATE.md` are graded evidence. Do not hand-edit them.

## 4. Running it

```
open your agentic harness, point it at .agents/orchestrator/SKILL.md, and let it run
```

That one skill is the go button. There is no runner to install or invoke.

## 5. Build contract

- `mvn -P original test` / `mvn -P refactored test`
- `scripts/coverage.sh <target>` prints `target covered missed pct`
- JDK 17. Nothing else.
