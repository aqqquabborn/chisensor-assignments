import { PAID_REPORT_SECTIONS, buildAdjustmentPlan } from '../data/room';
import type { Transaction } from '../core/types';
import { h2, lead } from './styles';

export default function DeliveredScreen({ constraints, transaction }: { constraints: string[]; transaction: Transaction | null }) {
  const plan = buildAdjustmentPlan(constraints);
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>Your full plan</h2>
      <p style={lead}>Unlocked by transaction <code>{transaction?.transactionId}</code>.</p>
      {PAID_REPORT_SECTIONS.map((s, i) => (
        <details key={s.id} open={i === 0} style={{ marginBottom: 8, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
          <summary style={{ padding: 12, minHeight: 44, fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>{s.title}</summary>
          <div style={{ padding: '0 12px 12px', fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
            {s.id === 'reorder' ? (
              <>
                <ol style={{ margin: 0, paddingLeft: 18 }}>
                  {plan.steps.map((st) => <li key={st.itemId} style={{ marginBottom: 4 }}><strong>{st.label}.</strong> {st.move}</li>)}
                </ol>
                <p style={{ margin: '6px 0 0' }}>Stays in place: {plan.fixed.join(', ') || '—'}.</p>
              </>
            ) : s.detail}
          </div>
        </details>
      ))}
    </div>
  );
}
