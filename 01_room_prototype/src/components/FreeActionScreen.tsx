import { BEDROOM, FREE_ACTION } from '../data/room';
import { useLang } from '../i18n/lang';
import RoomView from './RoomView';
import { Chip } from './ui';
import { btn, card, h2, lead } from './styles';

interface Props {
  applied: boolean;
  markedDone: boolean;
  onApply: () => void;
  onMarkDone: () => void;
  onProceed: () => void;
}

/**
 * Brief, item 4: one complete free action — object/area, change, short reason, simple diagram —
 * keeping the bed fixed, and clearly separating the SUGGESTED change from what the user has DONE.
 */
export default function FreeActionScreen({ applied, markedDone, onApply, onMarkDone, onProceed }: Props) {
  const { t, lang } = useLang();
  const status = markedDone
    ? <Chip tone="ok">{t('free.done')}</Chip>
    : applied ? <Chip tone="info">{t('free.suggested')}</Chip> : <Chip tone="warn">{t('free.notOpened')}</Chip>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <h2 style={{ ...h2, margin: 0 }}>{t('free.title')}</h2>
        <span style={{ marginLeft: 'auto' }} data-testid="free-action-status">{status}</span>
      </div>
      <p style={lead}>{t('free.description')}{lang === 'zh' ? '。' : '.'}</p>

      <RoomView room={BEDROOM} freeAction={FREE_ACTION} applied={applied} />
      <p style={{ fontSize: 11, color: '#64748b', margin: '4px 0 12px', textAlign: 'center' }}>
        {applied ? t('free.captionApplied') : t('free.captionInitial')}
      </p>

      <div style={card}>
        <div><strong>{t('free.areaLabel')}</strong> {t('free.area')}</div>
        <div style={{ marginTop: 6 }}><strong>{t('free.why')}</strong> {t('free.rationale')}</div>
        <div style={{ marginTop: 6, color: '#475569' }}><strong>{t('free.kept')}</strong> {t('free.constraint')}</div>
      </div>

      <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
        {!applied && <button onClick={onApply} style={btn('#2563eb')}>{t('free.show')}</button>}
        {applied && !markedDone && <button onClick={onMarkDone} style={btn('#047857')}>{t('free.markDone')}</button>}
        {applied && (
          <button onClick={onProceed} style={markedDone ? btn('#1e293b') : btn('transparent', '#334155')}>
            {markedDone ? t('free.proceedDone') : t('free.proceedLater')}
          </button>
        )}
      </div>
    </div>
  );
}
