import { useState, useCallback, useEffect } from 'react';
import { AppState, type AppStore, type ScanAreas, type ScenarioKey } from './types';
import { loadStore, saveStore, clearStore, defaultStore } from './persistence';
import { transition, createAnalysisJob, tickAnalysis, failAnalysis, resumeFailedJob } from './machine';
import { createTransaction, verifyTransaction, createEntitlement, attemptDelivery, isContentUnlocked } from './payment';
import { getScenarioPreset } from './scenarios';
import { CONSTRAINTS, EXAMPLE_PRICE } from '../data/room';

export const TICK_MS = 800;

/** One analysis tick, as a pure store → store step (also used by the unit tests). */
export function analysisStep(s: AppStore): AppStore {
  const job = s.analysisJob;
  if (s.state !== AppState.ANALYZING || !job || job.status !== 'running') return s;

  // Simulated recoverable fault: the injected task fails once while running, then the flag clears.
  const at = s.injectAnalysisFailureAt;
  if (at !== null && job.currentTaskIndex === at && job.tasks[at]?.status === 'running') {
    return { ...s, state: AppState.ANALYSIS_FAILED, analysisJob: failAnalysis(job), injectAnalysisFailureAt: null };
  }
  const next = tickAnalysis(job);
  if (next.status === 'completed') {
    const done = transition({ ...s, analysisJob: next }, AppState.FREE_ACTION);
    return done ? { ...done, selectedConstraints: [...next.constraints] } : s;
  }
  return { ...s, analysisJob: next };
}

/**
 * Central app hook. Every action is an explicit function and every state change
 * goes through transition(), so no screen can skip a step.
 */
export function useAppStore() {
  const [store, setStoreRaw] = useState<AppStore>(loadStore);

  const setStore = useCallback((next: (prev: AppStore) => AppStore) => {
    setStoreRaw((prev) => {
      const val = next(prev);
      if (val !== prev) saveStore(val);
      return val;
    });
  }, []);

  // The analysis ticker lives here, keyed on the job, not on a screen. It restarts
  // by itself after a refresh, a retry or a scenario load, and never runs twice.
  const job = store.analysisJob;
  const running = store.state === AppState.ANALYZING && job?.status === 'running';
  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => setStore(analysisStep), TICK_MS);
    return () => clearInterval(id);
  }, [running, job?.jobId, job?.attempt, setStore]);

  // ─── Scan ──────────────────────────────────────────────────

  const startScan = useCallback(() => {
    setStore((s) => {
      const checking = transition(s, AppState.DEVICE_CHECK);
      if (!checking) return s;
      return transition({ ...checking, deviceSupported: true }, AppState.SCAN_CAPTURE) ?? s;
    });
  }, [setStore]);

  const checkDeviceUnsupported = useCallback(() => {
    setStore((s) => {
      const checking = transition(s, AppState.DEVICE_CHECK);
      if (!checking) return s;
      return transition({ ...checking, deviceSupported: false }, AppState.UNSUPPORTED) ?? s;
    });
  }, [setStore]);

  const toggleConstraint = useCallback((id: string) => {
    setStore((s) => {
      const c = CONSTRAINTS.find((x) => x.id === id);
      if (!c || c.locked || s.state !== AppState.SCAN_CAPTURE) return s;
      const on = s.selectedConstraints.includes(id);
      return { ...s, selectedConstraints: on ? s.selectedConstraints.filter((x) => x !== id) : [...s.selectedConstraints, id] };
    });
  }, [setStore]);

  const submitScan = useCallback((areas: ScanAreas) => {
    setStore((s) => {
      const validating = transition(s, AppState.SCAN_VALIDATE);
      if (!validating) return s;
      const withScan: AppStore = { ...validating, scanResult: { areas: { ...areas }, timestamp: Date.now() } };
      if (areas.entry && areas.bedside_path && areas.bed_outline) {
        const analyzing = transition(withScan, AppState.ANALYZING);
        return analyzing ? { ...analyzing, analysisJob: createAnalysisJob(s.selectedConstraints) } : s;
      }
      // Insufficient input: no analysis, no plan, no sale.
      return transition(withScan, AppState.SCAN_INCOMPLETE) ?? s;
    });
  }, [setStore]);

  /** Back to capture; the areas already captured stay ticked. */
  const retryScan = useCallback(() => {
    setStore((s) => transition(s, AppState.SCAN_CAPTURE) ?? s);
  }, [setStore]);

  // ─── Analysis ──────────────────────────────────────────────

  /** Same job, same constraints, completed tasks kept — continue from the failed task. */
  const retryAnalysis = useCallback(() => {
    setStore((s) => {
      if (!s.analysisJob) return s;
      const analyzing = transition(s, AppState.ANALYZING);
      return analyzing ? { ...analyzing, analysisJob: resumeFailedJob(s.analysisJob) } : s;
    });
  }, [setStore]);

  // ─── Free action ───────────────────────────────────────────

  const applyFreeAction = useCallback(() => {
    setStore((s) => (s.state === AppState.FREE_ACTION ? { ...s, freeActionApplied: true } : s));
  }, [setStore]);

  const markFreeActionDone = useCallback(() => {
    setStore((s) => (s.state === AppState.FREE_ACTION && s.freeActionApplied ? { ...s, freeActionMarkedDone: true } : s));
  }, [setStore]);

  const proceedToUpsell = useCallback(() => {
    setStore((s) => transition(s, AppState.PAID_UPSELL) ?? s);
  }, [setStore]);

  // ─── Purchase ──────────────────────────────────────────────

  /** One transaction + one entitlement. A second tap is a no-op because the state has moved on. */
  const initiatePurchase = useCallback(() => {
    setStore((s) => {
      if (s.transaction) return s;
      const pending = transition(s, AppState.PURCHASE_PENDING);
      if (!pending) return s;
      const tx = createTransaction(EXAMPLE_PRICE);
      return { ...pending, transaction: tx, entitlement: createEntitlement(tx.transactionId) };
    });
  }, [setStore]);

  /**
   * A verification event from the (simulated) store. Safe to deliver any number
   * of times: the first moves pending → verified, later ones only count.
   */
  const receiveVerification = useCallback(() => {
    setStore((s) => {
      if (!s.transaction) return s;
      const tx = verifyTransaction(s.transaction);
      if (!tx) return s;
      if (s.state === AppState.PURCHASE_PENDING) {
        return transition({ ...s, transaction: tx }, AppState.PURCHASE_VERIFIED) ?? s;
      }
      return { ...s, transaction: tx }; // duplicate: no new purchase, no new entitlement, no state change
    });
  }, [setStore]);

  const deliverContent = useCallback((succeed: boolean) => {
    setStore((s) => {
      if (!s.entitlement || s.transaction?.status !== 'verified') return s;
      const target = succeed ? AppState.DELIVERED : AppState.DELIVERY_FAILED;
      const moved = transition(s, target);
      return moved ? { ...moved, entitlement: attemptDelivery(s.entitlement, succeed) } : s;
    });
  }, [setStore]);

  /** Retry delivery for the SAME transaction and entitlement — never a new charge. */
  const retryDelivery = useCallback(() => deliverContent(true), [deliverContent]);

  // ─── Test panel ────────────────────────────────────────────

  const loadScenario = useCallback((key: ScenarioKey) => {
    clearStore();
    setStore(() => getScenarioPreset(key));
  }, [setStore]);

  const resetApp = useCallback(() => {
    clearStore();
    setStore(() => defaultStore());
  }, [setStore]);

  return {
    store,
    contentUnlocked: isContentUnlocked(store.transaction, store.entitlement),
    startScan, checkDeviceUnsupported, toggleConstraint, submitScan, retryScan,
    retryAnalysis,
    applyFreeAction, markFreeActionDone, proceedToUpsell,
    initiatePurchase, receiveVerification, deliverContent, retryDelivery,
    loadScenario, resetApp,
  };
}
