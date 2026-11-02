import type { AnalysisJob } from '../core/types';
import { BEDROOM } from '../data/room';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
import RoomView from './RoomView';
import { Sim } from './ui';
import { h2 } from './styles';

/** Brief, item 3: the analysis shows the room; status text follows the deterministic simulated tasks. */
export default function AnalyzingScreen({ job }: { job: AnalysisJob }) {
  const { t } = useLang();
  const current = job.tasks.find((x) => x.status === 'running');
  const label = (id: string) => t(`task.${id}` as Key);
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{t('analysis.title')}</h2>
      <Sim>{t('analysis.sim')}</Sim>
      <RoomView room={BEDROOM} applied={false} />

      <p aria-live="polite" style={{ margin: '12px 0 8px', fontSize: 14, fontWeight: 600 }}>
        {current ? `${label(current.id)}…` : t('analysis.starting')}
      </p>
      <div style={{ height: 6, background: '#e2e8f0', borderRadius: 3, overflow: 'hidden', marginBottom: 10 }}>
        <div style={{ height: '100%', width: `${job.progress}%`, background: '#3b82f6', transition: 'width 0.4s ease' }} />
      </div>

      {job.tasks.map((task) => (
        <div key={task.id} data-task={task.id} data-status={task.status} style={{
          display: 'flex', alignItems: 'center', gap: 8, padding: '4px 0', fontSize: 13,
          color: task.status === 'completed' ? '#047857' : task.status === 'running' ? '#2563eb' : task.status === 'failed' ? '#dc2626' : '#94a3b8',
        }}>
          <span style={{ width: 18, textAlign: 'center' }}>
            {task.status === 'completed' ? '✓' : task.status === 'running' ? '◉' : task.status === 'failed' ? '✗' : '○'}
          </span>
          {label(task.id)}
        </div>
      ))}

      <p style={{ marginTop: 10, fontSize: 12, color: '#64748b' }}>
        {t('analysis.constraints')} {job.constraints.map((id) => t(`constraint.${id}` as Key)).join(' · ')}
      </p>
      <p style={{ marginTop: 4, fontSize: 11, color: '#94a3b8', fontFamily: 'ui-monospace, monospace' }}>
        {job.jobId} · {t('analysis.attempt', { n: job.attempt })}
      </p>
    </div>
  );
}
