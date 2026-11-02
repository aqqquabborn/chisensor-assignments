import type { CSSProperties } from 'react';

export const btn = (bg: string, color = '#fff'): CSSProperties => ({
  width: '100%', minHeight: 44, padding: '12px 0', background: bg, color,
  border: bg === 'transparent' ? '1px solid #cbd5e1' : 'none', borderRadius: 8,
  fontSize: 15, fontWeight: 600, cursor: 'pointer',
});

export const card: CSSProperties = {
  padding: 12, background: '#f8fafc', border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 13,
};

export const h2: CSSProperties = { margin: '0 0 6px', fontSize: 18 };
export const lead: CSSProperties = { margin: '0 0 12px', fontSize: 13, color: '#64748b', lineHeight: 1.5 };
