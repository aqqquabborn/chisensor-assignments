# AI usage log — Assignment 2

Tool: Claude (Cowork). All code was generated with AI assistance, then checked
against the original brief, a hand count of the data, and the test suite.

## Prompt 1 — first build

> "Here is the data for the second assignment (Data.docx). Build it carefully,
> professionally and concisely."

**What came back:** a single `analyze.py` that de-duplicated events, built a
per-channel funnel, allocated all costs by first-open share, keyword-matched
feedback into three themes and emitted two experiment cards with hard-coded
readiness flags.

**What I kept:** event de-duplication by `event_id`; transaction-level
reconciliation (double verification = one sale, pending ≠ paid, refund removes
the payer from "unrefunded delivered"); the per-channel funnel.

**What I changed:** almost everything else, after prompt 2.

## Prompt 2 — review against the original brief

> "Review the solution again. Check for bugs, propose and make UX/UI
> improvements. It must be a perfect solution; give me the improved solution and
> a doc describing what was done and why."

I re-read the Chinese brief line by line (PDF pages 2–4) instead of the earlier
summary, turned every requirement into a checkable item and compared the tool
with it. 20 defects were found. The main ones:

- ASO card said "READY — all flags green" while 2 paid reports were undelivered
  — the brief says a card must stay draft/blocked until delivery is ready.
- Shared inference and tool costs were spread across channels; the brief says
  they are counted once.
- Production hours were invented (18 sessions × 0.5 h); they are now an
  explicit, labelled assumption in `params.json`.
- "$1,500 budget 209% used" misread the cap — it is a ceiling for the *next*
  14 days, so it is now checked against the two cards' budgets.
- Priorities counted sessions instead of participants and matched researcher
  inferences; cards lacked most required fields (prerequisites, copy,
  denominator, guardrails, stop/continue, owner, keyword groups, 3-shot script).

**What I adopted:** the restructure into `inputs / metrics / evidence / cards /
render`, config-driven priorities and cards with citations resolved from the
CSVs, computed readiness, a copy-compliance check, and 27 unittest checks.

**What I modified by hand:** cost presentation (cash CAC per channel, shared
costs only in Overall), priority ranking rule (participants first, event
evidence as tie-break, minimum two participants), and the decision to report
budget reach (≈7 and ≈5 first opens) instead of implying the experiments can
reach significance.

## A problem found by checking

The original `data/feedback_sessions.csv` had been hand-quoted when it was
saved. Rebuilding it byte-for-byte from Data.docx showed that **12 of 18 rows
have unquoted commas**. On the real file the first version silently shifted
columns: S01's quote landed in `researcher_inferences` and the inference in an
unnamed column, with no error. The loader now repairs such rows around the one
quoted field, reports which rows it repaired, and the test
`test_raw_feedback_with_unquoted_commas_is_repaired` locks it in.

A second check — mutation testing — confirmed the suite catches real mistakes:
six deliberately injected bugs (double verification counted twice, commission
not reversed, refund after cutoff counted, sessions counted as participants,
readiness ignoring data, zero payers giving a number) each made at least one
test fail.
