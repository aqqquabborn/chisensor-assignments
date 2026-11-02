# AI usage log — Assignment 1

Tool: Claude (Cowork). The code was generated with AI assistance, then checked against the
original brief, the TypeScript build, unit tests and browser checks.

## Prompt 1 — architecture

> "Translate the assignment PDF, then design the full architecture: state machine with all
> states, TypeScript types, idempotency rules, persistence strategy, and scenario-to-state
> mapping."

**Kept:** the explicit `TRANSITIONS` map (invalid transitions return `null`), the separation of
`core/` logic from `components/`, and one screen per state.

**Changed:** the proposed `useReducer` + action types became explicit action functions in one
hook (`useAppStore`) — easier to trace in a 10-minute walkthrough. A proposed compass
orientation field in the room data was removed, because the brief forbids inventing value
through compass readings, imaginary windows or guaranteed results.

## Prompt 2 — final validation against the brief

> "Run a final validation and give me the final files for both assignments."

I re-read the brief line by line and checked each item in the running app.

**Defects found and fixed:**

1. `npm run build` failed: `enum` is not allowed under `erasableSyntaxOnly`. `AppState` is now
   a `const` object with a union type.
2. `analysis_failed_recoverable` never recovered: the failure was tied to the scenario name
   and re-injected on every retry. It is now a one-shot persisted fault, and retry resumes the
   same job from the failed task.
3. The room goal and constraints were not shown at the start (brief item 1); constraints could
   not be selected, so "restore the selected constraints" meant nothing.
4. The incomplete-scan screen did not say which area was missing, and a re-scan cleared the
   areas already captured.
5. The analysis screen did not show the room (brief item 3).
6. The free action forced the user to say "I moved the chair" before seeing the paid plan, so
   suggested and completed changes were not truly separate.
7. Scan, analysis and payment were not consistently labelled as simulated.
8. There was no way to send a duplicate verification event, so that check could not be
   reproduced; there were no automated checks at all.
9. The paid plan text used "south wall" (a compass direction) and a fixed order that ignored
   constraints.

**Adopted:** const-object states, a store-level analysis ticker keyed on the job, a
constraint-aware plan builder, the debug export, 21 unit checks and 8 browser checks.

## Issue found by checking

Running `npm run build` — not just `npm run dev` — exposed the `enum` compile error. Vite's
dev server strips types without checking them, so the prototype appeared to work while a
clean production build was broken. `npm run check` now runs the build first.
