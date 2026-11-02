import type { ReactNode } from 'react';
import { AppState, REQUIRED_SCAN_AREAS, type AppStore } from '../core/types';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import { Sim, Row } from './ui';
import { btn, card, h2, lead } from './styles';

interface Props {
  store: AppStore;
  onRetry?: () => void;
}

export default function ErrorScreen({ store, onRetry }: Props) {
  const { t, list } = useLang();
  const wrap = (title: string, body: ReactNode, retry?: string) => (
    <div style={{ padding: 16 }}>
      <div style={{ width: 44, height: 44, margin: '4px auto 10px', background: '#fee2e2', borderRadius: '50%',
        display: 'grid', placeItems: 'center', fontSize: 20, color: '#dc2626', fontWeight: 700 }}>!</div>
      <h2 style={{ ...h2, textAlign: 'center' }}>{title}</h2>
      {body}
      {onRetry && retry && <button onClick={onRetry} style={{ ...btn('#1e293b'), marginTop: 12 }}>{retry}</button>}
    </div>
  );

  switch (store.state) {
    case AppState.UNSUPPORTED:
      return wrap(t('unsupported.title'), <>
        <p style={lead}>{t('unsupported.body')}</p>
        <Sim>{t('unsupported.sim')}</Sim>
      </>);

    case AppState.SCAN_INCOMPLETE: {
      const areas = store.scanResult?.areas;
      const missing = REQUIRED_SCAN_AREAS.filter((k) => !areas?.[k]);
      const areaLabel = (k: string) => t(`area.${k}.label` as Key);
      return wrap(t('incomplete.title'), <>
        <p style={lead}>{t('incomplete.body')}</p>
        <div style={card}>
          {REQUIRED_SCAN_AREAS.map((k) => (
            <Row key={k} label={areaLabel(k)} value={areas?.[k]
              ? <span style={{ color: '#047857' }}>{t('scan.captured')}</span>
              : <span style={{ color: '#b45309' }}>{t('incomplete.missingHint', { hint: t(`area.${k}.hint` as Key).toLowerCase() })}</span>} />
          ))}
        </div>
        <p style={{ ...lead, marginTop: 10 }}>
          {t('incomplete.rescanList', { list: list(missing.map((k) => areaLabel(k).toLowerCase())) })}
        </p>
      </>, missing.length > 1 ? t('incomplete.retryN') : t('incomplete.retry1'));
    }

    case AppState.ANALYSIS_FAILED: {
      const job = store.analysisJob;
      const failed = job?.tasks.find((x) => x.status === 'failed');
      const done = job?.tasks.filter((x) => x.status === 'completed').length ?? 0;
      const step = failed ? t(`task.${failed.id}` as Key) : t('failed.aStep');
      return wrap(t('failed.title'), <>
        <p style={lead}>{done === 1 ? t('failed.body1', { step }) : t('failed.bodyN', { step, n: done })}</p>
        <div style={card}>
          <Row label={t('failed.job')} value={job?.jobId ?? '—'} mono />
          <Row label={t('failed.attempt')} value={String(job?.attempt ?? 1)} />
        </div>
        <Sim>{t('failed.sim')}</Sim>
      </>, t('failed.retry'));
    }

    case AppState.DELIVERY_FAILED:
      return wrap(t('delivery.title'), <>
        <p style={lead}>{t('delivery.body')}</p>
        <div style={card}>
          <Row label={t('purchase.transaction')} value={store.transaction?.transactionId ?? '—'} mono />
          <Row label={t('purchase.payment')} value={store.transaction ? t(`status.${store.transaction.status}` as Key) : '—'} />
          <Row label={t('delivery.attempts')} value={String(store.entitlement?.deliveryAttempts ?? 0)} />
        </div>
      </>, t('delivery.retry'));

    default:
      return null;
  }
}
