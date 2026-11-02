import { useState } from 'react';
import type { AppStore, ScenarioKey } from '../core/types';
import { SCENARIO_LIST } from '../core/scenarios';
import { debugSnapshot } from '../core/debug';
import { useLang } from '../i18n/lang';

interface Props {
  store: AppStore;
  contentUnlocked: boolean;
  onLoadScenario: (key: ScenarioKey) => void;
  onDuplicateVerification: () => void;
  onReset: () => void;
}

export default function TestPanel({ store, contentUnlocked, onLoadScenario, onDuplicateVerification, onReset }: Props) {
  const { t } = useLang();
  const [open, setOpen] = useState(false);
  const [copied, setCopied] = useState('');
  const snap = debugSnapshot(store, contentUnlocked);
  const json = JSON.stringify(snap, null, 2);

  // Copy rather than download: works locally and inside sandboxed hosting where downloads are blocked.
  const copy = () => {
    const done = (msg: string) => { setCopied(msg); setTimeout(() => setCopied(''), 1800); };
    const selectFallback = () => {
      const pre = document.querySelector('[data-testid=debug]');
      if (pre) { const r = document.createRange(); r.selectNodeContents(pre); getSelection()?.removeAllRanges(); getSelection()?.addRange(r); }
      done(t('panel.selected'));
    };
    try { navigator.clipboard.writeText(json).then(() => done(t('panel.copied')), selectFallback); } catch { selectFallback(); }
  };

  const small = (bg: string): React.CSSProperties => ({
    padding: '8px 10px', minHeight: 36, background: bg, color: '#e2e8f0', border: '1px solid #334155',
    borderRadius: 6, fontSize: 12, cursor: 'pointer', textAlign: 'left',
  });

  return (
    <div style={{
      position: 'fixed', bottom: 0, left: 0, right: 0, background: '#0f172a', color: '#e2e8f0',
      zIndex: 999, maxWidth: 390, margin: '0 auto', borderTop: '2px solid #334155',
      maxHeight: '75dvh', overflowY: 'auto',
    }}>
      <button data-testid="panel-toggle" onClick={() => setOpen((v) => !v)} aria-expanded={open} style={{
        width: '100%', minHeight: 40, padding: '8px 16px', background: 'transparent', color: '#cbd5e1',
        border: 'none', fontSize: 12, cursor: 'pointer', display: 'flex', justifyContent: 'space-between',
      }}>
        <span>{t('panel.title')} · {store.state}</span><span>{open ? '▼' : '▲'}</span>
      </button>

      {open && (
        <div style={{ padding: '0 16px 12px' }}>
          <pre data-testid="debug" style={{
            fontFamily: 'ui-monospace, monospace', fontSize: 11, padding: 8, margin: '0 0 8px',
            background: '#1e293b', borderRadius: 6, whiteSpace: 'pre-wrap', wordBreak: 'break-all',
          }}>{json}</pre>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 6, marginBottom: 8 }}>
            <button onClick={copy} style={small('#1e293b')}>{copied || t('panel.copy')}</button>
            <button onClick={onDuplicateVerification} disabled={!store.transaction} style={small('#1e293b')}
              title={t('panel.duplicateTitle')}>{t('panel.duplicate')}</button>
          </div>
          <div style={{ fontSize: 11, color: '#94a3b8', margin: '4px 0' }}>{t('panel.scenarios')}</div>
          <div style={{ display: 'grid', gap: 4 }}>
            {SCENARIO_LIST.map(({ key, label }) => (
              <button key={key} onClick={() => onLoadScenario(key)} style={{
                ...small(store.activeScenario === key ? '#334155' : '#1e293b'),
                color: store.activeScenario === key ? '#7dd3fc' : '#cbd5e1',
              }}>{label}</button>
            ))}
          </div>
          <button onClick={onReset} style={{ ...small('#b91c1c'), marginTop: 8, width: '100%', textAlign: 'center' }}>
            {t('panel.reset')}
          </button>
        </div>
      )}
    </div>
  );
}
