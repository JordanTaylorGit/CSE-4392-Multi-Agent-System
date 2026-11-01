# Architecture

The skills are the source of truth. `python3 scripts/validate_skills.py` checks the graph;
`.agents/orchestrator/SKILL.md` is the program that executes it.

## Components

| Component | Responsibility | Input | Output |
|-----------|----------------|-------|--------|
| orchestrator | dispatch three skills, own the gates, own `STATE.md` | profile | `runs/<ts>/` |
| the harness | runtime: runs the orchestrator, spawns subagents, surfaces HITL | the skills | transcripts |
| project profile | units, boundaries, observables, dedupe key, coverage command | `projects/<p>/profile.json` | vocabulary for testgen |
| **testgen** | whole test lifecycle for one target | profile, target, mode | passing suite + coverage |
| ↳ ep-tests | subagent: EP cases | profile | `testcases_ep.json` |
| ↳ bva-tests | subagent: BVA cases | profile | `testcases_bva.json` |
| refactor-state | State pattern + prompt mutation | original source | refactored source, `refactor-notes.md` |

`testgen` is the only composite skill: it spawns the two case-generation subagents concurrently,
joins them, dedupes, holds the G1 human gate, writes JUnit, runs and repairs the suite, and gates on
branch coverage — all internally. The orchestrator invokes it twice:

| invocation | mode | target | assignment steps |
|-----------|------|--------|------------------|
| 1 | generate | original | 1–7 |
| — | refactor-state | — | 8 |
| gate | G3 review | — | 9 |
| 2 | adapt | refactored | 10–12 |

## Where the control flow lives

The graph is a document, not code. Guarantees a runner would enforce are instead enforced by skill
text:

| guarantee | mechanism | weakness |
|-----------|-----------|----------|
| parallel fan-out | testgen spawns both subagents in one turn | depends on the harness's subagent primitive |
| join | wait for both subagents before Phase B | structural, not a memory barrier |
| gates | written exit conditions + refusal rules | enforcement lives in text, not code |
| bounded retry | 5-iteration cap per loop | needs discipline to enforce |
| resume | `STATE.md` read on entry, written after every step | depends on the file being written |

That is the trade: no runner to install, at the cost of enforcement living in text.

## Data flow

Single JSON case shape end to end (`schemas/testcase.schema.json`), so no stage needs to know how
another produced its input. The run directory is the only shared state.
