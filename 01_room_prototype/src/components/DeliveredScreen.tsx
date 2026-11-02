import { PAID_REPORT_SECTIONS, buildAdjustmentPlan } from '../data/room';
import type { Transaction } from '../core/types';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import { h2, lead } from './styles';

export default function DeliveredScreen({ constraints, transaction }: { constraints: string[]; transaction: Transaction | null }) {
  const { t, list, lang } = useLang();
  const colon = lang === 'zh' ? '：' : '.';
  const plan = buildAdjustmentPlan(constraints);
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{t('delivered.title')}</h2>
      <p style={lead}>{t('delivered.unlockedBy')} <code>{transaction?.transactionId}</code></p>
      {PAID_REPORT_SECTIONS.map((s, i) => (
        <details key={s.id} open={i === 0} style={{ marginBottom: 8, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
          <summary style={{ padding: 12, minHeight: 44, fontSize: 14, fontWeight: 600, cursor: 'pointer' }}>
            {t(`section.${s.id}.title` as Key)}
          </summary>
          <div style={{ padding: '0 12px 12px', fontSize: 13, color: '#475569', lineHeight: 1.5 }}>
            {s.id === 'reorder' ? (
              <>
                <ol style={{ margin: 0, paddingLeft: 18 }}>
                  {plan.steps.map((st) => (
                    <li key={st.itemId} style={{ marginBottom: 4 }}>
                      <strong>{t(`item.${st.itemId}` as Key)}{colon}</strong> {t(`move.${st.itemId}` as Key)}
                    </li>
                  ))}
                </ol>
                <p style={{ margin: '6px 0 0' }}>
                  {t('delivered.staysInPlace', { list: list(plan.fixed.map((id) => t(`item.${id}` as Key))) || '—' })}
                </p>
              </>
            ) : t(`section.${s.id}.detail` as Key)}
          </div>
        </details>
      ))}
    </div>
  );
}
