# Refactor prompt mutation study (owned by P5)

Assignment steps 8 and 9 require practising prompt engineering on the State-pattern refactor:
mutate the prompt against a web LLM until the output is satisfactory, then use the final prompt
in the agent system. This directory is that record.

| version | mutation | hypothesis | verdict | notes |
|---------|----------|------------|---------|-------|
| v01 | initial prompt | — | FAIL | produced an if/switch chain, not State |
| v02 | + exact public interface | reuse of tests | ... | |
| v03 | + forbid switch in subject | force delegation | ... | |
| v04 | + explicit invalid-transition handling | cover defensive branches | ... | |
| v05 | + require transition matrix in notes | drive 100% branch coverage | ... | |

One file per version (`v01.md` …). The version that wins is copied into
`.agents/refactor-state/SKILL.md` and referenced in the deck.
