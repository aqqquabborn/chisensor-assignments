# ChiSensor — recoverable room-to-plan prototype (Assignment 1)

A mobile-width web prototype of the ChiSensor bedroom flow. A renter's bed cannot move; the
goal is to make the room easier to walk through without buying furniture. The flow:
room goal and constraints → simulated scan quality check → real-looking wait (deterministic
simulated analysis) → one complete free action → understanding and obtaining the optional
paid plan. It stays consistent when the scan is incomplete, the analysis fails, the payment is
pending, or the report cannot be delivered after a verified payment.

Everything that would touch a device or money is **simulated and labelled as such**. The app
never asks for camera access, payment details or photos of a real room. `$9.99` is the
exercise's example price, not an approved ChiSensor price.

## Run

Node 20+.

```bash
npm install
npm run dev          # http://localhost:5173 — open at 390 px width (device toolbar)
npm run build        # type-check + production build
npm test             # 21 unit checks (Vitest)
npm run test:e2e     # 9 browser checks at 390 px (needs a build; see below)
npm run check        # build + unit + browser checks
```

The browser checks use Playwright. If it is not installed globally:
`npm i -D playwright && npx playwright install chromium`.

## Test panel and debug view

The **Test panel** bar at the bottom switches between the six scenarios from the brief —
`happy`, `unsupported`, `scan_incomplete`, `analysis_failed_recoverable`, `purchase_pending`,
`verified_payment_delivery_failed`. When opened, it shows the live debug view: `job_id`, job
status and attempt, constraints, `transaction_id`, payment status, verification events,
purchases, entitlement, delivery status and attempts, and whether content is unlocked.
**Copy debug JSON** copies the same snapshot to the clipboard. **Send duplicate verification** replays the
store's verification event for the current transaction.

## State model

Fourteen states. Every allowed transition is listed in `src/core/machine.ts`; anything else
returns `null`, so no screen can skip a step.

```
idle → device_check ─┬→ unsupported (stops before the scan)
                     └→ scan_capture → scan_validate ─┬→ scan_incomplete → scan_capture (captured areas kept)
                                                      └→ analyzing ─┬→ analysis_failed → analyzing (same job, resumes)
                                                                    └→ free_action → paid_upsell → purchase_pending
purchase_pending → purchase_verified ─┬→ delivered
                                      └→ delivery_failed → delivered (same transaction)
```

Payment, entitlement and delivery are separate: a transaction is `pending → verified`, its
single entitlement is `granted` only on delivery, and content unlocks only when the payment is
verified **and** the report was delivered for that same transaction (`isContentUnlocked`).

## Persistence

The whole store is saved to `localStorage` on every change and restored on load
(`src/core/persistence.ts`). That includes the analysis job (ID, task statuses, attempt,
constraints), the selected constraints, the scan result, the transaction and the entitlement.
A refresh during analysis continues the same job: the ticker lives in `useAppStore` and is
keyed on the job, not on a screen. A refresh during a pending payment shows the same pending
transaction. Corrupt storage falls back to a fresh start; a store saved by an older build is
merged over the defaults.

## Duplicate verification and retries

- `verifyTransaction` is idempotent. The first event moves `pending → verified`. Later events
  return the same transaction — same ID, status and `verifiedAt` — and only increase
  `verificationEvents`, so a duplicate is visible but creates no purchase and no entitlement.
- **Unlock plan** creates a transaction only if none exists, so a double tap is a no-op.
- Retrying delivery calls `attemptDelivery` on the existing entitlement. It never touches the
  transaction, so a retry cannot become a new charge.

## What native iOS and a backend would still need

| Area | Prototype | Production |
| --- | --- | --- |
| Device support | Button simulates the check | ARKit `supportsSceneReconstruction` / LiDAR capability check before onboarding |
| Scan | Checkboxes per area | RoomPlan capture, with per-area coverage and quality from the scan |
| Analysis | Five deterministic timed tasks | Server job with an ID; the app polls or subscribes and resumes by job ID |
| Payment | Buttons simulate StoreKit | StoreKit 2 purchase plus server-side verification of the signed transaction (and App Store Server Notifications for later refunds) |
| Idempotency | In-memory per transaction | Server keyed on `originalTransactionId`; unique constraint on the entitlement |
| Delivery | Button simulates success/failure | Report generation queue with retries; delivery status stored server-side |
| Persistence | `localStorage` | Server account state; local cache for offline resume |

## Limits I verified

- The room geometry is the prototype's own 4 m × 3.5 m bedroom (data in `src/data/room.ts`);
  unit checks confirm that the chair sits on the entry path, that the suggested position is
  inside the room and overlaps no furniture, and that the bed never moves.
- The paid plan is a fixed rule set: its order changes with the selected constraints (keeping
  the dresser removes its step), but it is not a real layout model.
- Payment cancellation is not modelled as a state yet. `TransactionStatus` already has
  `cancelled` and `verifyTransaction` refuses to revive it; adding the state means one entry in
  `TRANSITIONS`, one action in `useAppStore`, and one screen case.

## AI issue I fixed

The AI-written version compiled under `npm run dev` but **`npm run build` failed**: `enum
AppState` is rejected by the project's `erasableSyntaxOnly` setting, and Vite's dev server does
not type-check. It also had a scenario bug: in `analysis_failed_recoverable` the failure was
re-injected on every retry, so the "recoverable" failure never recovered. Both were found by
running the build and a browser check, and both are now covered by tests. Details in
`AI_USAGE_LOG.md`.

## Language

The UI is available in English and Chinese: **EN / 中文** in the header. The choice is kept
after a refresh; `#zh` or `#en` in the URL selects it directly. All strings live in
`src/i18n/strings.ts`; both dictionaries have the same keys (enforced by the type), and browser
check 8 walks every screen in Chinese and fails on any untranslated key.

## Project structure

```
src/core/       types, state machine, payment, persistence, scenarios, store hook, debug snapshot, unit tests
src/data/       room, constraints, free action, paid plan builder, report sections
src/components/ one screen per state, room diagram, test panel
tests/e2e.cjs   browser checks for the six flows at 390 px
```
