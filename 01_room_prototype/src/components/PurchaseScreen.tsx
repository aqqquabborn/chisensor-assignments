import type { Transaction, Entitlement } from '../core/types';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
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
  const { t } = useLang();
  if (!tx) return null;
  const pending = tx.status === 'pending';
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{pending ? t('purchase.pendingTitle') : t('purchase.verifiedTitle')}</h2>
      <p style={lead}>{pending ? t('purchase.pendingLead') : t('purchase.verifiedLead')}</p>

      <div style={{ ...card, marginBottom: 14 }}>
        <Row label={t('purchase.transaction')} value={tx.transactionId} mono />
        <Row label={t('purchase.amount')} value={`$${tx.amount.toFixed(2)}`} />
        <Row label={t('purchase.payment')} value={<Chip tone={pending ? 'warn' : 'ok'}>{t(`status.${tx.status}` as Key)}</Chip>} />
        <Row label={t('purchase.entitlement')} value={<Chip tone={ent?.granted ? 'ok' : 'warn'}>{ent?.granted ? t('purchase.granted') : t('purchase.notGranted')}</Chip>} />
        <Row label={t('purchase.delivery')} value={<Chip tone={ent?.deliveryStatus === 'failed' ? 'bad' : 'warn'}>{ent ? t(`status.${ent.deliveryStatus}` as Key) : '—'}</Chip>} />
        <Row label={t('purchase.plan')} value={<Chip tone="bad">{t('purchase.locked')}</Chip>} />
      </div>

      <Sim>{t('purchase.sim')}</Sim>
      {pending ? (
        <button onClick={onVerify} style={btn('#047857')}>{t('purchase.confirm')}</button>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
          <button onClick={() => onDeliver(true)} style={btn('#047857')}>{t('purchase.deliverOk')}</button>
          <button onClick={() => onDeliver(false)} style={btn('#dc2626')}>{t('purchase.deliverFail')}</button>
        </div>
      )}
    </div>
  );
}
