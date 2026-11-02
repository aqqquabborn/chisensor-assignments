import type { Transaction, Entitlement } from '../core/types';
import { Chip, Row, Sim } from './ui';
import { btn, card, h2, lead } from './styles';

interface Props {
  transaction: Transaction | null;
  entitlement: Entitlement | null;
  onVerify: () => void;
  onDeliver: (succeed: boolean) => void;
}

/** Payment pending, payment verification, entitlement and delivery are shown — and handled — separately. */
export default function PurchaseScreen({ transaction: tx, entitlement: ent, onVerify, onDeliver }: Props) {
  if (!tx) return null;
  const pending = tx.status === 'pending';
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{pending ? 'Payment pending' : 'Payment verified — preparing your plan'}</h2>
      <p style={lead}>
        {pending
          ? 'The store has not confirmed this payment yet. The plan stays locked until it does; you will not be charged twice if you wait or come back later.'
          : 'Your payment is confirmed. The plan is delivered as a separate step, so a delivery problem never affects the payment.'}
      </p>

      <div style={{ ...card, marginBottom: 14 }}>
        <Row label="Transaction" value={tx.transactionId} mono />
        <Row label="Amount (example)" value={`$${tx.amount.toFixed(2)}`} />
        <Row label="Payment" value={<Chip tone={pending ? 'warn' : 'ok'}>{tx.status}</Chip>} />
        <Row label="Entitlement" value={<Chip tone={ent?.granted ? 'ok' : 'warn'}>{ent?.granted ? 'granted' : 'not granted'}</Chip>} />
        <Row label="Report delivery" value={<Chip tone={ent?.deliveryStatus === 'failed' ? 'bad' : 'warn'}>{ent?.deliveryStatus ?? '—'}</Chip>} />
        <Row label="Plan" value={<Chip tone="bad">locked</Chip>} />
      </div>

      <Sim>Store responses are simulated with the buttons below.</Sim>
      {pending ? (
        <button onClick={onVerify} style={btn('#047857')}>Simulate: store confirms payment</button>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <button onClick={() => onDeliver(true)} style={btn('#047857')}>Simulate: delivery succeeds</button>
          <button onClick={() => onDeliver(false)} style={btn('#dc2626')}>Simulate: delivery fails</button>
        </div>
      )}
    </div>
  );
}
