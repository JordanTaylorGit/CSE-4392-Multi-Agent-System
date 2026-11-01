# Changelog format (owned by P4)

`changelog.md` is graded evidence for assignment step 6 ("modify the code and/or the test cases,
log the changes"). One row per mutation, newest last.

| # | iteration | file | change | before | after | reason | test delta |
|---|-----------|------|--------|--------|-------|--------|------------|
| 1 | 1 | SeasonSwitchTest.java | relaxed assertion | `assertEquals("Spring", …)` | `assertEquals("Spring", …)` | spec says March is Spring | 3 failing -> 2 failing |

Rules:
- One row per mutation. No squashed rows.
- `before`/`after` are the actual snippets, not descriptions of them.
- `test delta` is `N failing -> M failing`, so a reader can see each change actually helped.
- Code fix and test fix never share a row.
