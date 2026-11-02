import { useState } from 'react';
import { REQUIRED_SCAN_AREAS, type ScanAreas } from '../core/types';
import { AREA_INFO, CONSTRAINTS } from '../data/room';
import { Sim } from './ui';
import { btn, h2, lead } from './styles';

interface Props {
  initialAreas: ScanAreas | null;
  selectedConstraints: string[];
  onToggleConstraint: (id: string) => void;
  onSubmit: (areas: ScanAreas) => void;
}


export default function ScanScreen({ initialAreas, selectedConstraints, onToggleConstraint, onSubmit }: Props) {
  // A retry after an incomplete scan keeps what was already captured.
  const [areas, setAreas] = useState<ScanAreas>(initialAreas ?? { entry: false, bedside_path: false, bed_outline: false });
  const missing = REQUIRED_SCAN_AREAS.filter((k) => !areas[k]);

  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>Scan quality check</h2>
      <Sim>No camera is opened. Tick an area to simulate capturing it.</Sim>
      <p style={lead}>All three areas are required before the analysis can start.</p>

      {REQUIRED_SCAN_AREAS.map((key) => (
        <label key={key} style={{
          display: 'flex', alignItems: 'center', gap: 10, minHeight: 48, padding: '8px 12px', marginBottom: 8,
          background: areas[key] ? '#ecfdf5' : '#f8fafc', border: `1.5px solid ${areas[key] ? '#10b981' : '#e2e8f0'}`,
          borderRadius: 8, cursor: 'pointer', fontSize: 14,
        }}>
          <input type="checkbox" name={key} checked={areas[key]} onChange={() => setAreas((p) => ({ ...p, [key]: !p[key] }))}
            style={{ width: 20, height: 20, accentColor: '#10b981', flex: 'none' }} />
          <span><strong>{AREA_INFO[key].label}</strong><br /><span style={{ fontSize: 12, color: '#64748b' }}>{AREA_INFO[key].hint}</span></span>
          <span style={{ marginLeft: 'auto', fontSize: 12, color: areas[key] ? '#047857' : '#b45309' }}>{areas[key] ? 'captured' : 'missing'}</span>
        </label>
      ))}

      <fieldset style={{ border: '1px solid #e2e8f0', borderRadius: 8, padding: '8px 12px', margin: '8px 0 12px' }}>
        <legend style={{ fontSize: 12, color: '#64748b', padding: '0 4px' }}>Constraints for this analysis</legend>
        {CONSTRAINTS.map((c) => (
          <label key={c.id} style={{ display: 'flex', gap: 8, alignItems: 'center', minHeight: 36, fontSize: 13, color: c.locked ? '#64748b' : '#1e293b' }}>
            <input type="checkbox" name={`constraint-${c.id}`} checked={selectedConstraints.includes(c.id)} disabled={c.locked}
              onChange={() => onToggleConstraint(c.id)} style={{ width: 18, height: 18 }} />
            {c.label}{c.locked ? ' — required' : ''}
          </label>
        ))}
      </fieldset>

      <button onClick={() => onSubmit(areas)} style={btn('#1e293b')}>
        {missing.length ? `Submit scan (${missing.length} area${missing.length > 1 ? 's' : ''} missing)` : 'Submit scan'}
      </button>
    </div>
  );
}
