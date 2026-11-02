import { AppState } from './core/types';
import { useAppStore } from './core/useAppStore';
import StartScreen from './components/StartScreen';
import ScanScreen from './components/ScanScreen';
import AnalyzingScreen from './components/AnalyzingScreen';
import FreeActionScreen from './components/FreeActionScreen';
import PaidUpsellScreen from './components/PaidUpsellScreen';
import PurchaseScreen from './components/PurchaseScreen';
import DeliveredScreen from './components/DeliveredScreen';
import ErrorScreen from './components/ErrorScreen';
import TestPanel from './components/TestPanel';
import { useLang } from './i18n/lang';

const TONE: Partial<Record<AppState, [string, string]>> = {
  [AppState.DELIVERED]: ['#dcfce7', '#166534'],
  [AppState.UNSUPPORTED]: ['#fee2e2', '#991b1b'],
  [AppState.SCAN_INCOMPLETE]: ['#fee2e2', '#991b1b'],
  [AppState.ANALYSIS_FAILED]: ['#fee2e2', '#991b1b'],
  [AppState.DELIVERY_FAILED]: ['#fee2e2', '#991b1b'],
  [AppState.ANALYZING]: ['#fef3c7', '#92400e'],
  [AppState.PURCHASE_PENDING]: ['#fef3c7', '#92400e'],
};

export default function App() {
  const a = useAppStore();
  const { t, lang, setLang } = useLang();
  const { store } = a;

  const screen = () => {
    switch (store.state) {
      case AppState.IDLE:
        return <StartScreen selected={store.selectedConstraints} onStart={a.startScan} onUnsupported={a.checkDeviceUnsupported} />;
      case AppState.SCAN_CAPTURE:
        return <ScanScreen initialAreas={store.scanResult?.areas ?? null} selectedConstraints={store.selectedConstraints}
          onToggleConstraint={a.toggleConstraint} onSubmit={a.submitScan} />;
      case AppState.ANALYZING:
        return store.analysisJob ? <AnalyzingScreen job={store.analysisJob} /> : null;
      case AppState.UNSUPPORTED:
        return <ErrorScreen store={store} />;
      case AppState.SCAN_INCOMPLETE:
        return <ErrorScreen store={store} onRetry={a.retryScan} />;
      case AppState.ANALYSIS_FAILED:
        return <ErrorScreen store={store} onRetry={a.retryAnalysis} />;
      case AppState.DELIVERY_FAILED:
        return <ErrorScreen store={store} onRetry={a.retryDelivery} />;
      case AppState.FREE_ACTION:
        return <FreeActionScreen applied={store.freeActionApplied} markedDone={store.freeActionMarkedDone}
          onApply={a.applyFreeAction} onMarkDone={a.markFreeActionDone} onProceed={a.proceedToUpsell} />;
      case AppState.PAID_UPSELL:
        return <PaidUpsellScreen constraints={store.selectedConstraints} onPurchase={a.initiatePurchase} />;
      case AppState.PURCHASE_PENDING:
      case AppState.PURCHASE_VERIFIED:
        return <PurchaseScreen transaction={store.transaction} entitlement={store.entitlement}
          onVerify={a.receiveVerification} onDeliver={a.deliverContent} />;
      case AppState.DELIVERED:
        return <DeliveredScreen constraints={store.selectedConstraints} transaction={store.transaction} />;
      default: // DEVICE_CHECK and SCAN_VALIDATE are instantaneous in the prototype
        return <p style={{ padding: 16, color: '#64748b' }}>{t('app.working')}</p>;
    }
  };

  const [bg, fg] = TONE[store.state] ?? ['#f1f5f9', '#475569'];
  return (
    <div style={{
      maxWidth: 390, margin: '0 auto', minHeight: '100dvh', background: '#fff', color: '#1e293b',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans SC", sans-serif', paddingBottom: 56,
    }}>
      <header style={{ padding: '12px 16px', borderBottom: '1px solid #e2e8f0', display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 8, rowGap: 6 }}>
        <span style={{ fontSize: 14, fontWeight: 700 }}>ChiSensor</span>
        <span style={{ fontSize: 11, color: '#64748b' }}>{t('app.subtitle')}</span>
        <span role="group" aria-label={t('app.language')} style={{ marginLeft: 'auto', display: 'inline-flex', border: '1px solid #cbd5e1', borderRadius: 6, overflow: 'hidden' }}>
          {(['en', 'zh'] as const).map((l) => (
            <button key={l} data-testid={`lang-${l}`} aria-pressed={lang === l} onClick={() => setLang(l)} style={{
              border: 'none', padding: '3px 8px', minHeight: 26, fontSize: 11, fontWeight: 600, cursor: 'pointer',
              background: lang === l ? '#1e293b' : '#fff', color: lang === l ? '#fff' : '#475569',
            }}>{l === 'en' ? 'EN' : '中文'}</button>
          ))}
        </span>
        <span data-testid="state" style={{ fontSize: 11, fontWeight: 600, padding: '2px 8px', borderRadius: 10, background: bg, color: fg }}>
          {store.state}
        </span>
      </header>
      <main>{screen()}</main>
      <TestPanel store={store} contentUnlocked={a.contentUnlocked} onLoadScenario={a.loadScenario}
        onDuplicateVerification={a.receiveVerification} onReset={a.resetApp} />
    </div>
  );
}
