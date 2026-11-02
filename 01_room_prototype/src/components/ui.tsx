import type { ReactNode } from 'react';

/** Every simulated behaviour carries this label (brief: scan, analysis and purchase must be marked as simulated). */
export function Sim({ children }: { children: ReactNode }) {
  return (
    <div role="note" style={{
      display: 'flex', gap: 6, alignItems: 'flex-start', padding: '6px 10px', margin: '0 0 12px',
      background: '#eef2ff', color: '#3730a3', borderRadius: 6, fontSize: 12, lineHeight: 1.4,
    }}>
      <strong style={{ flex: 'none' }}>SIMULATED</strong><span>{children}</span>
    </div>
  );
}

export function Chip({ children, tone }: { children: ReactNode; tone: 'ok' | 'warn' | 'bad' | 'info' }) {
  const c = { ok: ['#dcfce7', '#166534'], warn: ['#fef3c7', '#92400e'], bad: ['#fee2e2', '#991b1b'], info: ['#e0e7ff', '#3730a3'] }[tone];
  return <span style={{ background: c[0], color: c[1], fontSize: 11, fontWeight: 700, padding: '2px 8px', borderRadius: 10, whiteSpace: 'nowrap' }}>{children}</span>;
}

export function Row({ label, value, mono }: { label: string; value: ReactNode; mono?: boolean }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, padding: '4px 0' }}>
      <span style={{ color: '#64748b' }}>{label}</span>
      <span style={{ fontWeight: 600, textAlign: 'right', wordBreak: 'break-all', fontFamily: mono ? 'ui-monospace, monospace' : undefined, fontSize: mono ? 12 : 13 }}>{value}</span>
    </div>
  );
}

