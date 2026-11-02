import type { AppStore } from './types';

/** Debug view for reviewers: job ID, transaction ID, entitlement and delivery status, plus an export. */
export function debugSnapshot(store: AppStore, contentUnlocked: boolean) {
  return {
    state: store.state,
    scenario: store.activeScenario,
    job_id: store.analysisJob?.jobId ?? null,
    job_status: store.analysisJob?.status ?? null,
    job_attempt: store.analysisJob?.attempt ?? null,
    constraints: store.analysisJob?.constraints ?? store.selectedConstraints,
    transaction_id: store.transaction?.transactionId ?? null,
    payment_status: store.transaction?.status ?? null,
    verification_events: store.transaction?.verificationEvents ?? 0,
    purchases: store.transaction ? 1 : 0,
    entitlement_granted: store.entitlement?.granted ?? null,
    delivery_status: store.entitlement?.deliveryStatus ?? null,
    delivery_attempts: store.entitlement?.deliveryAttempts ?? 0,
    content_unlocked: contentUnlocked,
    free_action: store.freeActionMarkedDone ? 'done by user' : store.freeActionApplied ? 'suggested' : 'not opened',
  };
}
