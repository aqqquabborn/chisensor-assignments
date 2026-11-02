import { AppState, type AppStore, type ScenarioKey } from './types';
import { defaultStore } from './persistence';
import { createAnalysisJob } from './machine';
import { createTransaction, createEntitlement } from './payment';

const FULL_SCAN = () => ({ areas: { entry: true, bedside_path: true, bed_outline: true }, timestamp: Date.now() });

/** Snapshot after a completed analysis, used by the payment scenarios. */
function afterAnalysis(base: AppStore): AppStore {
  const job = createAnalysisJob(base.selectedConstraints, 42);
  return {
    ...base,
    deviceSupported: true,
    scanResult: FULL_SCAN(),
    analysisJob: {
      ...job,
      status: 'completed',
      progress: 100,
      currentTaskIndex: job.tasks.length,
      tasks: job.tasks.map((t) => ({ ...t, status: 'completed' as const })),
    },
    freeActionApplied: true,
    freeActionMarkedDone: false,
  };
}

/** The six scenarios named in the brief. Each returns a complete store snapshot. */
export function getScenarioPreset(key: ScenarioKey): AppStore {
  const base: AppStore = { ...defaultStore(), activeScenario: key };

  switch (key) {
    case 'happy':
      return base;

    case 'unsupported':
      return { ...base, state: AppState.UNSUPPORTED, deviceSupported: false };

    case 'scan_incomplete':
      return {
        ...base,
        state: AppState.SCAN_INCOMPLETE,
        deviceSupported: true,
        scanResult: { areas: { entry: true, bedside_path: false, bed_outline: true }, timestamp: Date.now() },
      };

    // Runs live: tasks 1–2 complete, task 3 fails once, Retry continues the same job to the end.
    case 'analysis_failed_recoverable':
      return {
        ...base,
        state: AppState.ANALYZING,
        deviceSupported: true,
        scanResult: FULL_SCAN(),
        analysisJob: createAnalysisJob(base.selectedConstraints, 42),
        injectAnalysisFailureAt: 2,
      };

    case 'purchase_pending': {
      const tx = createTransaction(9.99);
      return { ...afterAnalysis(base), state: AppState.PURCHASE_PENDING, transaction: tx, entitlement: createEntitlement(tx.transactionId) };
    }

    case 'verified_payment_delivery_failed': {
      const tx = { ...createTransaction(9.99), status: 'verified' as const, verifiedAt: Date.now(), verificationEvents: 1 };
      const ent = { ...createEntitlement(tx.transactionId), deliveryStatus: 'failed' as const, deliveryAttempts: 1, lastAttemptAt: Date.now() };
      return { ...afterAnalysis(base), state: AppState.DELIVERY_FAILED, transaction: tx, entitlement: ent };
    }

    default:
      return base;
  }
}

export const SCENARIO_LIST: { key: ScenarioKey; label: string }[] = [
  { key: 'happy', label: '① happy' },
  { key: 'unsupported', label: '② unsupported' },
  { key: 'scan_incomplete', label: '③ scan_incomplete' },
  { key: 'analysis_failed_recoverable', label: '④ analysis_failed_recoverable' },
  { key: 'purchase_pending', label: '⑤ purchase_pending' },
  { key: 'verified_payment_delivery_failed', label: '⑥ verified_payment_delivery_failed' },
];
