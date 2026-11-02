import { PAID_REPORT_SECTIONS, EXAMPLE_PRICE, buildAdjustmentPlan } from '../data/room';
import { Sim } from './ui';
import { btn, h2, lead } from './styles';

interface Props {
  constraints: string[];
  onPurchase: () => void;
}

/** Brief, item 5: explain the paid increment with the provided report sections. */
export default function PaidUpsellScreen({ constraints, onPurchase }: Props) {
  const plan = buildAdjustmentPlan(constraints);
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>What the full plan adds</h2>
      <p style={lead}>
        The free action fixes one item. The full plan puts {plan.steps.length} moves in an order that respects
        your constraints{plan.fixed.length ? ` (${plan.fixed.join(', ')} stay${plan.fixed.length === 1 ? 's' : ''} put)` : ''},
        then walks you through trying, checking, saving and reviewing each one.
      </p>
      {PAID_REPORT_SECTIONS.map((s) => (
        <div key={s.id} style={{ padding: 12, marginBottom: 8, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>🔒 {s.title}</div>
          <div style={{ fontSize: 12, color: '#64748b' }}>{s.preview}</div>
        </div>
      ))}
      <button onClick={onPurchase} style={{ ...btn('#6d28d9'), marginTop: 8 }}>
        Unlock plan — ${EXAMPLE_PRICE.toFixed(2)} (simulated)
      </button>
      <div style={{ height: 8 }} />
      <Sim>Example price for the exercise, not an approved ChiSensor price. No payment details are requested and nothing is charged.</Sim>
    </div>
  );
}
