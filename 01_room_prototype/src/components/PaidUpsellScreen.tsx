import { PAID_REPORT_SECTIONS, EXAMPLE_PRICE, buildAdjustmentPlan } from '../data/room';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import { Sim } from './ui';
import { btn, h2, lead } from './styles';

interface Props {
  constraints: string[];
  onPurchase: () => void;
}

/** Brief, item 5: explain the paid increment with the provided report sections. */
export default function PaidUpsellScreen({ constraints, onPurchase }: Props) {
  const { t, list } = useLang();
  const plan = buildAdjustmentPlan(constraints);
  const fixedNames = list(plan.fixed.map((id) => t(`item.${id}` as Key)));
  const fixed = plan.fixed.length === 0 ? ''
    : plan.fixed.length === 1 ? t('upsell.fixed1', { list: fixedNames }) : t('upsell.fixedN', { list: fixedNames });
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{t('upsell.title')}</h2>
      <p style={lead}>{t('upsell.lead', { n: plan.steps.length, fixed })}</p>
      {PAID_REPORT_SECTIONS.map((s) => (
        <div key={s.id} style={{ padding: 12, marginBottom: 8, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8 }}>
          <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 2 }}>🔒 {t(`section.${s.id}.title` as Key)}</div>
          <div style={{ fontSize: 12, color: '#64748b' }}>{t(`section.${s.id}.preview` as Key)}</div>
        </div>
      ))}
      <button onClick={onPurchase} style={{ ...btn('#6d28d9'), marginTop: 8 }}>
        {t('upsell.cta', { price: EXAMPLE_PRICE.toFixed(2) })}
      </button>
      <div style={{ height: 8 }} />
      <Sim>{t('upsell.sim')}</Sim>
    </div>
  );
}
