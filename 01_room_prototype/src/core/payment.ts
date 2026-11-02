import type { Transaction, Entitlement } from './types';

let txCounter = 0;

function generateTxId(): string {
  txCounter += 1;
  return `tx_${Date.now().toString(36)}_${txCounter}`;
}

/** A new pending transaction. Pending never unlocks content. */
export function createTransaction(amount: number): Transaction {
  return {
    transactionId: generateTxId(),
    status: 'pending',
    amount,
    createdAt: Date.now(),
    verificationEvents: 0,
  };
}

/**
 * Apply one verification event — idempotent.
 * pending   → verified (verifiedAt set once)
 * verified  → same transaction: same ID, status and verifiedAt; only the event
 *             counter moves, so a duplicate event is visible but creates no purchase
 * cancelled → null (a cancelled transaction cannot be revived)
 */
export function verifyTransaction(tx: Transaction): Transaction | null {
  if (tx.status === 'cancelled') return null;
  const events = (tx.verificationEvents ?? 0) + 1;
  if (tx.status === 'verified') return { ...tx, verificationEvents: events };
  return { ...tx, status: 'verified', verifiedAt: Date.now(), verificationEvents: events };
}

/** One entitlement per transaction, created with the purchase. */
export function createEntitlement(transactionId: string): Entitlement {
  return { transactionId, granted: false, deliveryStatus: 'pending', deliveryAttempts: 0 };
}

/**
 * Attempt report delivery for an existing entitlement. Never touches the
 * transaction, so a retry can never become a second charge.
 */
export function attemptDelivery(ent: Entitlement, succeed: boolean): Entitlement {
  const attempts = ent.deliveryAttempts + 1;
  if (succeed) {
    return { ...ent, granted: true, deliveryStatus: 'delivered', deliveryAttempts: attempts, lastAttemptAt: Date.now() };
  }
  return { ...ent, deliveryStatus: 'failed', deliveryAttempts: attempts, lastAttemptAt: Date.now() };
}

/** Content unlocks only when payment is verified AND the report was delivered for that same transaction. */
export function isContentUnlocked(tx: Transaction | null, ent: Entitlement | null): boolean {
  if (!tx || !ent) return false;
  return (
    tx.status === 'verified' &&
    ent.transactionId === tx.transactionId &&
    ent.granted &&
    ent.deliveryStatus === 'delivered'
  );
}
