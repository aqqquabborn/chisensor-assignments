import { AppState, REQUIRED_SCAN_AREAS, type AppStore } from '../core/types';
import { AREA_INFO } from '../data/room';
import { Sim, Row } from './ui';
import { btn, card, h2, lead } from './styles';

interface Props {
  store: AppStore;
  onRetry?: () => void;
}

export default function ErrorScreen({ store, onRetry }: Props) {
  const wrap = (title: string, body: React.ReactNode, retry?: string) => (
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
      return wrap('This device cannot scan the room', <>
        <p style={lead}>Room scanning needs a LiDAR sensor (iPhone Pro or iPad Pro). We stop here, before the scan,
          so you do not spend time on a scan that cannot produce a plan.</p>
        <Sim>The device check is simulated; no sensor was accessed. Use the Test panel to switch scenario.</Sim>
      </>);

    case AppState.SCAN_INCOMPLETE: {
      const areas = store.scanResult?.areas;
      const missing = REQUIRED_SCAN_AREAS.filter((k) => !areas?.[k]);
      return wrap('Scan incomplete — analysis not started', <>
        <p style={lead}>The plan needs all three areas. Nothing was analysed or offered for sale on partial input.</p>
        <div style={card}>
          {REQUIRED_SCAN_AREAS.map((k) => (
            <Row key={k} label={AREA_INFO[k].label} value={areas?.[k]
              ? <span style={{ color: '#047857' }}>captured</span>
              : <span style={{ color: '#b45309' }}>missing — {AREA_INFO[k].hint.toLowerCase()}</span>} />
          ))}
        </div>
        <p style={{ ...lead, marginTop: 10 }}>Re-scan {missing.map((k) => AREA_INFO[k].label.toLowerCase()).join(' and ')}. Captured areas are kept.</p>
      </>, `Re-scan missing area${missing.length > 1 ? 's' : ''}`);
    }

    case AppState.ANALYSIS_FAILED: {
      const job = store.analysisJob;
      const failed = job?.tasks.find((t) => t.status === 'failed');
      const done = job?.tasks.filter((t) => t.status === 'completed').length ?? 0;
      return wrap('Analysis stopped', <>
        <p style={lead}>“{failed?.label ?? 'A step'}” failed. Your scan, constraints and the {done} finished step{done === 1 ? '' : 's'} are kept;
          retry continues the same job from this step.</p>
        <div style={card}>
          <Row label="Job" value={job?.jobId ?? '—'} mono />
          <Row label="Attempt" value={String(job?.attempt ?? 1)} />
        </div>
        <Sim>This failure is injected by the scenario to show recovery.</Sim>
      </>, 'Retry analysis');
    }

    case AppState.DELIVERY_FAILED:
      return wrap('Payment received — report not delivered yet', <>
        <p style={lead}>Your payment is verified and stays valid. Retrying only re-sends the report for the same
          transaction; it cannot charge you again.</p>
        <div style={card}>
          <Row label="Transaction" value={store.transaction?.transactionId ?? '—'} mono />
          <Row label="Payment" value={store.transaction?.status ?? '—'} />
          <Row label="Delivery attempts" value={String(store.entitlement?.deliveryAttempts ?? 0)} />
        </div>
      </>, 'Retry delivery (no new charge)');

    default:
      return null;
  }
}
