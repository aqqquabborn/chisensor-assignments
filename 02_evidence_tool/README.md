# ChiSensor — evidence → experiments tool

A small command-line tool that reads the synthetic feedback, event and channel
files and writes one auditable HTML report plus two experiment cards. It answers
three questions: which product problems to fix first, what value to express on
the App Store and in short content, and whether the observed cohorts bring
qualified users and delivered paid outcomes at an acceptable cost.

It is not a promotion platform, a content factory or a channel integration.

## Run

Python 3.9+ and the standard library only — nothing to install, no network,
keys or accounts.

```bash
python analyze.py                 # data/ + config/ → out/
python -m unittest -v             # 27 repeatable checks
python analyze.py --strict        # exit 1 if any error-level input issue
python analyze.py --data my_data --out my_out
```

Open `out/report.html` in any browser. Exit codes: `0` ok, `1` strict mode found
input errors, `2` fatal input problem (missing file, missing column, bad JSON).

## Inputs and outputs

| Path | What it is |
| --- | --- |
| `data/event_log.csv`, `data/channel_data.csv`, `data/feedback_sessions.csv` | The three files exactly as supplied in Data.docx |
| `config/params.json` | Price, commission, labor rate and hours, inference and tool costs, next-trial cap, cutoff, readiness flag, forbidden claims |
| `config/priorities.json` | Editable priority codebook (match terms, proposed change, pass/fail) |
| `config/experiments.json` | Wording of the two cards; quotes and numbers are filled from data |
| `out/report.html` | The report: input checks, funnel, payments, cost and CAC, priorities, cards, source records |
| `out/experiment_cards.json`, `out/experiment_cards.md` | The two cards |
| `out/analysis.json` | Every computed number, with user and transaction IDs, for audit |

Replace any input and re-run: every figure is recomputed. Running twice on the
same input produces byte-identical files (the footer carries input SHA-256
fingerprints instead of a timestamp).

## Pipeline

`evidence_tool/` follows the order in the brief:

1. `inputs.py` — read and validate; keep the source line of every record;
   remove exact duplicate events by `event_id` (a reused ID with different
   content is an error, not a merge); repair the supplied feedback file, whose
   free-text fields contain unquoted commas.
2. `metrics.py` — first-touch attribution, transaction reconciliation, user
   stages, money, cost, CAC and contribution.
3. `evidence.py` — first observation vs re-test per participant; match
   candidate priorities against observed behavior and user statements only;
   rank and select up to three.
4. `cards.py` — exactly two cards; fill citations and baselines from data;
   check prerequisites, readiness, budget and copy.
5. `render.py` / `pipeline.py` — HTML, Markdown and JSON.

## Counting rules

- Users by `user_id`, research participants by `participant_id`, purchases by
  `transaction_id`. Research participants are a separate cohort from event
  users; they are linked by theme, never by person.
- A user's channel is the channel of their first `first_open` (first touch). It
  is not a measure of incrementality.
- The first four stages are cumulative: a qualified scan needs `first_open` and
  `qualified` too.
- A transaction is a sale once it has a verification event at or before the
  cutoff; extra verification events add nothing. Pending purchases are shown
  but are not collected cash.
- Unrefunded delivered payer = verified + delivered + no full refund known at
  the cutoff (default cutoff: the latest event).
- Net after commission = collected − full refunds − 15% on kept sales
  (commission is reversed on a full refund).

## Costs

Three cost types are labelled and counted once: channel cash (CSV), converted
production labor (hours × $25/h) and shared processing (100 × $0.08 inference
+ $12 tools), which appears only in the Overall row. CAC is `N/A` when its
payer denominator is zero. Contribution is an exercise metric, not company
profit.

**Assumption:** the input has no production hours. `params.json` holds
placeholder hours per channel and the report marks them as an assumption.
Replace them with real hours.

## Readiness

`readiness.commercial_delivery_ready` in `params.json` is the given flag. A card
is `BLOCKED` while the flag is false **or** the data still shows verified
payments without delivery or pending purchases; `DRAFT` while any prerequisite
is open; at best `READY FOR REVIEW`. No card is ever marked approved for launch.

## Editing priorities

In the report, **Edit priorities** makes the texts editable; **Export
priorities.json** shows them in the config format and copies them to the
clipboard (no file download, so it also works in sandboxed hosting). Save it as
`config/priorities.json` and re-run — evidence, participants and ranking are
recomputed from the data, so an edit can never invent evidence.

## Limits

- Data volumes are small (largest channel: 18 first opens); channel comparisons
  are directional. At observed costs each card's budget buys only 5–7 first
  opens, so the cards define an inconclusive outcome explicitly.
- Theme matching is keyword-based and transparent (the matched words are shown).
  It is a reviewable first pass, not semantic analysis.
- No keyword search volumes, industry benchmarks or virality claims are used;
  the copy check rejects them.
- `$9.99` is the exercise's example price, not an approved ChiSensor price.

## 3-minute demo

```bash
bash scripts/demo.sh
```

The script runs the tool, the tests, then three input changes (a new refund, a
cost-parameter change, a duplicate re-import) and shows the effect of each.
