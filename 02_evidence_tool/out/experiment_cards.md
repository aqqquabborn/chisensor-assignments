# ChiSensor experiment cards

Combined budget caps: $900.00 of $1,500.00 for the next 14 days (within cap).

## EXP-ASO-01 — Store page that shows the before/after layout and states the LiDAR requirement

**Status: BLOCKED.** Commercial delivery is not ready: given flag is false; 2 verified payments undelivered; 2 purchases pending. Draft only — not approved for launch.

- **Type:** ASO / store value expression
- **Channel:** App Store custom product page, served to ASA_Category search ads
- **Owner:** Growth PM, ASO (name to be assigned before launch)
- **Budget cap:** $500.00
- **Linked priorities:** PR-SCAN-ENTRY (BASELINE SET), PR-PAYWALL-CLARITY (BASELINE SET), PR-DELIVERY (FAIL)

### Target problem

In ASA_Category traffic, 78% (14/18) of first opens reach a qualified scan and 25% (1/4) of verified purchases were fully refunded. The store page has to set the device requirement and the free-then-paid split before install, and show the before/after result people respond to.

### Hypothesis

If the ASA_Category custom product page leads with a real before/after layout and states the iPhone Pro (LiDAR) requirement in the first screenshot, then more of the people who install will reach a qualified scan, because they self-select on device and understand the free-then-paid value before installing.

### Product prerequisites

- [ ] Given readiness flag: commercial delivery ready — given flag is false
- [ ] No verified payment left undelivered at cutoff — 2 verified payments undelivered
- [ ] No purchase stuck in pending at cutoff — 2 purchases pending
- [ ] PR-DELIVERY passes its acceptance check — PR-DELIVERY currently FAIL
- [ ] Custom product page analytics (impressions, installs) available in App Store Connect — needs human confirmation
- [ ] Screenshot is a real in-app before/after render, not a mock-up — needs human confirmation

### Copy

- **Title concept:** ChiSensor: Room Layout Scan
- **Subtitle:** See a better desk and bed layout
- **Screenshot caption:** Your room, rearranged — before you move anything
- **Device badge:** Requires iPhone Pro with LiDAR
- **Footnote:** First suggestion free · full guide is a paid upgrade

### Screenshot concept

Screenshot 1 of the custom product page: Split view of one real scan: the current layout on the left, the green ghosted 'after' position of the desk on the right

### Keyword intent groups (no search volumes — not provided, not estimated)

| Group | Intent | Example terms | Evidence |
| --- | --- | --- | --- |
| Desk and home-office layout | Fix a work-from-home desk that feels draining | desk layout, home office setup, desk facing door | S11, S03 |
| Bedroom layout | Rearrange a bedroom without buying furniture | bedroom layout, furniture arrangement, room layout planner | S13 |
| Feng shui, explained | Feng shui with a practical, non-mystical explanation | feng shui bedroom, feng shui desk, room energy | S10 |

### Product facts

- A free first suggestion is shown before any payment (S03)
- The app shows a before/after ghosted preview of the new layout (S05)
- Users can re-scan after a change and see the score move (S13)

### Not supported — do not claim

- Scanning on iPhones without LiDAR (S02)
- Several rooms in one pass (S09)
- Direct shopping links for recommended furniture (S04)

### Marketing hypotheses (unproven)

- A visible before/after on the store page raises install intent the way the in-app preview raised purchase intent for one participant.
- Stating the LiDAR requirement up front may lower installs but raise the share of installs that reach a qualified scan.
- Saying 'first suggestion free, full guide paid' before install reduces refunds caused by mismatched expectations.

### Measurement

- **Primary metric:** Qualified scans per product page impression = First opens from the custom product page that reach a qualified scan (event log) ÷ Custom product page impressions (App Store Connect). Store impressions only — no video plays.
- **Primary baseline:** Not in the input data: measure the default page over the same 14 days as the control.
- **Guardrail — Qualified scan ÷ first open** (÷ First opens from the page): Not below the ASA_Category baseline (78% (14/18))
- **Guardrail — Refund share** (÷ Verified purchases from the page cohort): Not above the ASA_Category baseline (25% (1/4))
- **Guardrail — Cash cost per qualified scan** (÷ Qualified scans from the page cohort): Not above the ASA_Category baseline ($85.71)
- Baseline — Qualified scan ÷ first open: 78% (14/18)
- Baseline — Verified first-time payer ÷ free suggestion viewed: 31% (4/13)
- Baseline — Fully refunded ÷ verified purchases: 25% (1/4)
- Baseline — Cash cost per qualified scan: $85.71
- Baseline — First opens the budget buys at the observed cost: ≈7 first opens at $66.67 cash each

**Stop:** Stop when the $500.00 cap is spent or after 14 days. Stop early if any verified payment from this cohort stays undelivered for more than 24 hours, or if the refund share rises above 25% (1/4). If fewer than 20 first opens are reached (budget reach: ≈7 first opens at $66.67 cash each), report the result as inconclusive and make no rate claims.

**Continue:** Roll the page out to all ASA traffic only if, with at least 20 first opens, qualified scans per impression beat the default page over the same period, qualified scan ÷ first open is at or above 78% (14/18), and no guardrail is breached.

### Evidence citations

- S05 (Said, P05, first observation): “Seeing the green ghosting preview made me want to buy the furniture.”
- S02 (Observed, P02, first observation): “Encountered LIDAR error on standard iPhone, dropped off”
- S01 (Said, P01, first observation): “Why do I have to pay before seeing the full report?”
- S11 (Said, P11, first observation): “This helped me fix my desk facing the door issue.”

Copy check: passed.

---

## EXP-CONTENT-01 — 3-shot 'desk facing the door' fix with a KOC creator

**Status: BLOCKED.** Commercial delivery is not ready: given flag is false; 2 verified payments undelivered; 2 purchases pending. Draft only — not approved for launch.

- **Type:** Short content · 3-shot script
- **Channel:** TikTok, existing KOC creators (TikTok_KOC), one tracking link per video
- **Owner:** Content lead, KOC program (name to be assigned before launch)
- **Budget cap:** $400.00
- **Linked priorities:** PR-SCAN-ENTRY (BASELINE SET), PR-PAYWALL-CLARITY (BASELINE SET), PR-DELIVERY (FAIL)

### Target problem

In TikTok_KOC traffic, 50% (5/10) of first opens reach a qualified scan and 50% (1/2) of verified purchases were fully refunded. Content should attract people with a concrete desk problem and a LiDAR iPhone, and set the free-then-paid expectation.

### Hypothesis

If KOC videos show one concrete desk-facing-the-door fix with the real before/after preview and say the app needs an iPhone Pro, then TikTok_KOC first opens will reach a qualified scan more often than the current baseline (50% (5/10)), because the video pre-qualifies people on problem and device.

### Product prerequisites

- [ ] Given readiness flag: commercial delivery ready — given flag is false
- [ ] No verified payment left undelivered at cutoff — 2 verified payments undelivered
- [ ] No purchase stuck in pending at cutoff — 2 purchases pending
- [ ] PR-DELIVERY passes its acceptance check — PR-DELIVERY currently FAIL
- [ ] Creator brief approved; creator shows the real app screen, no staged results — needs human confirmation
- [ ] One tracking link per video so first opens can be attributed — needs human confirmation

### Copy

- **Hook:** Your desk is facing the door. Here's the 10-second fix.
- **Caption:** Scanned my room with ChiSensor. First suggestion is free, the full guide is paid. Needs iPhone Pro (LiDAR).
- **Call to action:** Scan your desk — first suggestion free

### Three-shot script

| Shot | Seconds | Visual | On screen | Voice | Evidence |
| --- | --- | --- | --- | --- | --- |
| 1 | 0–3 | Creator at a work-from-home desk with their back to the door, glancing over their shoulder | Why does my desk feel draining? | My desk faced the door and I never felt focused. | S03, S11 |
| 2 | 3–9 | Screen recording: LiDAR scan of the same room, then the green ghosted 'after' position of the desk | Real scan · iPhone Pro with LiDAR | I scanned the room and it showed me where the desk should go, without buying anything. | S05, S02 |
| 3 | 9–15 | Desk moved; creator re-scans and the app's real score change is shown on screen (no number promised in advance) | First suggestion free · full guide paid | Moved it, re-scanned, and my score went up. Try the free suggestion first. | S13, S01 |

### Product facts

- A free first suggestion is shown before any payment (S03)
- The app shows a before/after ghosted preview of the new layout (S05)
- The app gives desk-setup tips (S11)
- Users can re-scan after a change and see the score move (S13)

### Not supported — do not claim

- Scanning on iPhones without LiDAR (S02)
- A guaranteed score increase (one participant reported +20; it is not a promise) (S13)
- Several rooms in one pass (S09)

### Marketing hypotheses (unproven)

- A specific desk problem attracts higher-intent viewers than general feng shui content.
- Saying 'needs iPhone Pro' in the video reduces installs that cannot scan.
- Showing the real re-test score change makes the video worth saving; reach is not assumed or promised.

### Measurement

- **Primary metric:** Qualified scan rate = First opens from the video tracking links that reach a qualified scan (event log) ÷ First opens from those links (event log). Video views are never used as this denominator.
- **Primary baseline:** 50% (5/10) (TikTok_KOC, current data)
- **Guardrail — Refund share** (÷ Verified purchases from the tracked links): Not above the TikTok_KOC baseline (50% (1/2))
- **Guardrail — Cash cost per qualified scan** (÷ Qualified scans from the tracked links): Not above the TikTok_KOC baseline ($160.00)
- **Guardrail — Content diagnostic (separate funnel)** (÷ Video impressions → 3-second views → link clicks, from TikTok analytics): Reported on its own; never mixed into app-funnel denominators
- Baseline — Qualified scan ÷ first open: 50% (5/10)
- Baseline — Fully refunded ÷ verified purchases: 50% (1/2)
- Baseline — Cash cost per qualified scan: $160.00
- Baseline — First opens the budget buys at the observed cost: ≈5 first opens at $80.00 cash each

**Stop:** Stop when the $400.00 cap is spent or after 14 days. Pause a creator's video if its cohort's refund share rises above 50% (1/2). If fewer than 20 tracked first opens are reached (budget reach: ≈5 first opens at $80.00 cash each), report the result as inconclusive and make no rate claims.

**Continue:** Brief new creators with the same script only if, with at least 20 tracked first opens, qualified scan ÷ first open is above 50% (5/10), cash cost per qualified scan is at or below $160.00, and no guardrail is breached.

### Evidence citations

- S03 (Said, P03, first observation): “This actually explained why my WFH setup feels draining.”
- S11 (Said, P11, first observation): “This helped me fix my desk facing the door issue.”
- S05 (Said, P05, first observation): “Seeing the green ghosting preview made me want to buy the furniture.”
- S13 (Said, P01, re-test #1): “I re-tested after moving my bed, score went up 20 points!”
- S02 (Observed, P02, first observation): “Encountered LIDAR error on standard iPhone, dropped off”

Copy check: passed.

---
