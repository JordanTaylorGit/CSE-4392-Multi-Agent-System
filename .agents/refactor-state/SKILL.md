---
id: refactor-state
order: 60
executor: agent
inputs: [root:java/src/original/java/cse4392/SeasonSwitch.java]
outputs: [root:java/src/refactored/java/cse4392/, refactor-notes.md]
gate: none
---

# Purpose
Apply the State pattern to `SeasonSwitch`.

# Contract
- Writes the refactored sources under `src/refactored/java`.
- **Hard constraint (assignment hint):** the Subject class is named exactly `SeasonSwitch` and
  keeps the original public interface, so the existing tests are reusable via the
  `refactored` Maven profile.
- `refactor-notes.md` maps original branch -> state/transition, so the transition matrix for
  testing can be derived mechanically.

# Acceptance criteria (feeds the G3 gate)

The output is not "satisfactory" — the assignment's word — until ALL of these hold. These are what
the review gate checks:

1. A `SeasonState` interface exists and `SeasonSwitch` delegates to it.
2. No `if`/`switch` chain over state remains in the Subject.
3. Each concrete state handles its own transition.
4. Invalid transitions are handled explicitly, not by falling through.
5. No duplicated transition logic across states.
6. Public interface identical to the original — same class name `SeasonSwitch`, same methods.
7. Every original branch maps to a state or transition in `refactor-notes.md`.

# Prompt

Version: v05 (final). Run in ChatGPT on 2026-11-16: compiles, 21/21 existing tests pass.
Mutation history and verdicts: `docs/prompt-mutations/`.

The text between the markers is the prompt sent to the model. It was tested with chat input and
output; the two parts that mention reading and writing files were adapted for the harness, and
nothing else was changed.

<!-- PROMPT:BEGIN -->
You are a senior Java engineer refactoring existing code with the GoF State design pattern.

## Task

Refactor the Java class below (`cse4392.SeasonSwitch`) to use the State pattern. The refactoring must
preserve behavior exactly. It is verified by an existing JUnit 5 test suite that must pass without
any modification.

## Pattern requirements

- Define a `SeasonState` interface with one method for every state-dependent operation: `cool`,
  `heat`, `off`, `timerOff`, and one for the room temperature drift currently implemented by
  `Room.actionPerformed`.
- Create one concrete class per state: `OffState`, `CoolState`, `HeatState`. Also create one no-op
  state used for unrecognized state values (see the constraint on `state` below).
- `SeasonSwitch` is the Context. Every state-dependent call is delegated to the current state object.
- After the refactoring there must be NO `switch (state)` and no if/else chain on the state anywhere,
  including inside `Room`.
- Each concrete state owns its own behavior: device on/off calls, timer start/stop, console messages,
  and the transition to the next state.
- State objects are stateless and shared (`static final` instances). They receive the context as a
  method parameter.

## Hard constraints (existing tests depend on these)

1. Keep package `cse4392`, class name `SeasonSwitch`, and `implements ActionListener`.
2. Keep exactly as they are, with the same names, types, initial values and package-private
   visibility: `static int state`, the constants `OFF=0, COOL=1, HEAT=2`, and the fields `ac`,
   `heater`, `timer`, `room`, `coolTemp`, `heatTemp`. Keep inner classes `AC`, `Heater` and `Room`
   with their members (`isOn`, `on()`, `off()`, `temp`, `timer`, `actionPerformed`).
3. Keep the signatures of `cool()`, `heat()`, `off()`, `timerOff()` and `actionPerformed(ActionEvent)`
   on `SeasonSwitch`, and `actionPerformed(ActionEvent)` on `Room`.
4. Copy `main` verbatim, character for character.
5. Preserve the exact order of side effects and the exact text of every `System.out.println`.
6. `SeasonSwitch.state` (the int) remains the single source of truth for the current state. The tests
   assign it directly, including an invalid value such as 3, and then call methods. So the context
   must look up the state object from the int on every call, using a
   `static final Map<Integer, SeasonState>` and `getOrDefault(state, <no-op state>)`. An unrecognized
   value must be ignored silently, with no exception. A state transition is an assignment of
   `SeasonSwitch.state` to one of the constants.
7. Do not add any new conditional logic: no null checks, no extra `if`, ternary or `&&`/`||`, beyond
   the conditionals that already exist in the original. The suite must reach 100% branch coverage, and
   every new branch would need new tests.
8. Java 17. No external libraries.

## Output format

For each file, give a heading with its path, `src/refactored/java/cse4392/<Name>.java`, followed by
the complete source in a code block. After the files, give a table mapping each original
`switch` case to the state class and method that now implements it. Do not write tests. Do not add
other commentary.

## Original code

Read the original source from `java/src/original/java/cse4392/SeasonSwitch.java`.

## Output

Write each class to `java/src/refactored/java/cse4392/<Name>.java`. Also write `refactor-notes.md`
containing a table that maps each original `switch` case to the state class and method that now
implements it. Do not modify any other file, including tests and `pom.xml`. Do not write tests.
<!-- PROMPT:END -->
