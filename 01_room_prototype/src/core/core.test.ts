import { beforeEach, describe, expect, it } from 'vitest';
import { AppState, type AppStore } from './types';
import { transition, createAnalysisJob, resumeFailedJob } from './machine';
import { analysisStep } from './useAppStore';
import { createTransaction, createEntitlement, verifyTransaction, attemptDelivery, isContentUnlocked } from './payment';
import { defaultStore, loadStore, saveStore } from './persistence';
import { getScenarioPreset, SCENARIO_LIST } from './scenarios';
import { BEDROOM, FREE_ACTION, DEFAULT_CONSTRAINTS, buildAdjustmentPlan } from '../data/room';

// Minimal localStorage for the node test environment.
beforeEach(() => {
  const m = new Map<string, string>();
  globalThis.localStorage = {
    getItem: (k: string) => m.get(k) ?? null, setItem: (k: string, v: string) => void m.set(k, v),
    removeItem: (k: string) => void m.delete(k), clear: () => m.clear(), key: () => null, length: 0,
  } as Storage;
});

const runAnalysis = (s: AppStore, maxTicks = 50) => {
  for (let i = 0; i < maxTicks && s.state === AppState.ANALYZING; i++) s = analysisStep(s);
  return s;
};

describe('state machine', () => {
  it('rejects skipped steps', () => {
    const s = defaultStore();
    expect(transition(s, AppState.ANALYZING)).toBeNull();
    expect(transition(s, AppState.DELIVERED)).toBeNull();
    expect(transition({ ...s, state: AppState.SCAN_VALIDATE }, AppState.FREE_ACTION)).toBeNull();
    expect(transition({ ...s, state: AppState.PURCHASE_PENDING }, AppState.DELIVERED)).toBeNull();
  });
});

describe('analysis', () => {
  const analyzing = (): AppStore => ({
    ...defaultStore(), state: AppState.ANALYZING, analysisJob: createAnalysisJob(['bed_fixed', 'dresser_fixed'], 7),
  });

  it('runs the deterministic tasks to the free action and keeps the constraints', () => {
    const s = runAnalysis(analyzing());
    expect(s.state).toBe(AppState.FREE_ACTION);
    expect(s.analysisJob?.tasks.every((t) => t.status === 'completed')).toBe(true);
    expect(s.selectedConstraints).toEqual(['bed_fixed', 'dresser_fixed']);
  });

  it('shows each task as running before it completes', () => {
    const s = analysisStep(analyzing());
    expect(s.analysisJob?.tasks[0].status).toBe('running');
  });

  it('injected failure happens once; retry resumes the SAME job from the failed task', () => {
    let s = runAnalysis({ ...analyzing(), injectAnalysisFailureAt: 2 });
    expect(s.state).toBe(AppState.ANALYSIS_FAILED);
    expect(s.analysisJob?.tasks.map((t) => t.status)).toEqual(['completed', 'completed', 'failed', 'pending', 'pending']);
    const jobId = s.analysisJob!.jobId;
    s = { ...transition(s, AppState.ANALYZING)!, analysisJob: resumeFailedJob(s.analysisJob!) };
    s = runAnalysis(s);
    expect(s.state).toBe(AppState.FREE_ACTION);
    expect(s.analysisJob?.jobId).toBe(jobId);
    expect(s.analysisJob?.attempt).toBe(2);
  });

  it('a job restored from storage continues where it stopped', () => {
    let s = analyzing();
    for (let i = 0; i < 4; i++) s = analysisStep(s);
    saveStore(s);
    const restored = loadStore();
    expect(restored.analysisJob).toEqual(s.analysisJob);
    expect(runAnalysis(restored).state).toBe(AppState.FREE_ACTION);
  });
});

describe('payment', () => {
  it('duplicate verification creates no purchase and changes nothing but the event count', () => {
    const tx = createTransaction(9.99);
    const v1 = verifyTransaction(tx)!;
    const v2 = verifyTransaction(v1)!;
    const v3 = verifyTransaction(v2)!;
    expect(v3.transactionId).toBe(tx.transactionId);
    expect(v3.status).toBe('verified');
    expect(v3.verifiedAt).toBe(v1.verifiedAt);
    expect(v3.verificationEvents).toBe(3);
  });

  it('cancelled transactions cannot be verified', () => {
    expect(verifyTransaction({ ...createTransaction(9.99), status: 'cancelled' })).toBeNull();
  });

  it('pending never unlocks; verified unlocks only after delivery of the same transaction', () => {
    const tx = createTransaction(9.99);
    const ent = createEntitlement(tx.transactionId);
    expect(isContentUnlocked(tx, attemptDelivery(ent, true))).toBe(false); // pending
    const v = verifyTransaction(tx)!;
    expect(isContentUnlocked(v, ent)).toBe(false); // not delivered
    expect(isContentUnlocked(v, attemptDelivery(ent, false))).toBe(false); // delivery failed
    expect(isContentUnlocked(v, attemptDelivery(ent, true))).toBe(true);
    expect(isContentUnlocked(v, attemptDelivery(createEntitlement('other'), true))).toBe(false);
  });

  it('delivery retry keeps one entitlement and counts attempts', () => {
    const ent = createEntitlement('tx_1');
    const retried = attemptDelivery(attemptDelivery(ent, false), true);
    expect(retried.transactionId).toBe('tx_1');
    expect(retried.deliveryAttempts).toBe(2);
    expect(retried.deliveryStatus).toBe('delivered');
  });
});

describe('persistence', () => {
  it('corrupt storage falls back to a fresh store', () => {
    localStorage.setItem('chisensor_app_store', '{not json');
    expect(loadStore().state).toBe(AppState.IDLE);
  });

  it('a store saved by an older build is upgraded with defaults', () => {
    localStorage.setItem('chisensor_app_store', JSON.stringify({ state: 'idle', freeActionApplied: false, activeScenario: 'happy' }));
    const s = loadStore();
    expect(s.selectedConstraints).toEqual(DEFAULT_CONSTRAINTS);
    expect(s.injectAnalysisFailureAt).toBeNull();
  });
});

describe('scenarios', () => {
  it.each(SCENARIO_LIST.map((x) => x.key))('%s is a consistent snapshot', (key) => {
    const s = getScenarioPreset(key);
    expect(s.activeScenario).toBe(key);
    if (s.transaction) expect(s.entitlement?.transactionId).toBe(s.transaction.transactionId);
  });

  it('maps each scenario to the expected starting state', () => {
    const states = Object.fromEntries(SCENARIO_LIST.map(({ key }) => [key, getScenarioPreset(key).state]));
    expect(states).toEqual({
      happy: 'idle', unsupported: 'unsupported', scan_incomplete: 'scan_incomplete',
      analysis_failed_recoverable: 'analyzing', purchase_pending: 'purchase_pending',
      verified_payment_delivery_failed: 'delivery_failed',
    });
  });
});

describe('room data and paid plan', () => {
  const overlap = (a: { x: number; y: number; w: number; h: number }, b: typeof a) =>
    a.x < b.x + b.w && b.x < a.x + a.w && a.y < b.y + b.h && b.y < a.y + a.h;
  const chair = BEDROOM.items.find((i) => i.id === 'chair')!;
  const moved = { ...chair, ...FREE_ACTION.suggestedPosition };

  it('the chair is on the entry path now and off it after the free action', () => {
    const onPath = (r: typeof chair) => BEDROOM.entryPath.some(([x, y]) => x >= r.x && x <= r.x + r.w && y >= r.y && y <= r.y + r.h)
      || (r.x <= 0.8 && 0.8 <= r.x + r.w && r.y < 1.5 && r.y + r.h > 0.5);
    expect(onPath(chair)).toBe(true);
    expect(onPath(moved)).toBe(false);
  });

  it('the suggested position is inside the room and overlaps no furniture; the bed is not moved', () => {
    expect(moved.x + moved.w).toBeLessThanOrEqual(BEDROOM.width);
    expect(moved.y + moved.h).toBeLessThanOrEqual(BEDROOM.height);
    for (const other of BEDROOM.items.filter((i) => i.id !== 'chair')) expect(overlap(moved, other)).toBe(false);
    expect(FREE_ACTION.targetItemId).not.toBe('bed');
    expect(BEDROOM.items.find((i) => i.id === 'bed')?.movable).toBe(false);
  });

  it('the adjustment order respects the selected constraints', () => {
    expect(buildAdjustmentPlan(DEFAULT_CONSTRAINTS).steps.map((s) => s.itemId)).toEqual(['chair', 'dresser', 'nightstand']);
    const keepDresser = buildAdjustmentPlan([...DEFAULT_CONSTRAINTS, 'dresser_fixed']);
    expect(keepDresser.steps.map((s) => s.itemId)).toEqual(['chair', 'nightstand']);
    expect(keepDresser.fixed).toEqual(['bed', 'dresser']);
  });
});
