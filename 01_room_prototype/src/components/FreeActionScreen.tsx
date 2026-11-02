import { BEDROOM, FREE_ACTION } from '../data/room';
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
  const status = markedDone
    ? <Chip tone="ok">Done by you</Chip>
    : applied ? <Chip tone="info">Suggested — not done yet</Chip> : <Chip tone="warn">Not opened</Chip>;

  return (
    <div style={{ padding: 16 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
        <h2 style={{ ...h2, margin: 0 }}>Free action</h2>
        <span style={{ marginLeft: 'auto' }} data-testid="free-action-status">{status}</span>
      </div>
      <p style={lead}>{FREE_ACTION.description}.</p>

      <RoomView room={BEDROOM} freeAction={FREE_ACTION} applied={applied} />
      <p style={{ fontSize: 11, color: '#64748b', margin: '4px 0 12px', textAlign: 'center' }}>
        {applied ? 'Green = suggested position · dashed = current position' : 'Red = the chair in your entry path'}
      </p>

      <div style={card}>
        <div><strong>Area:</strong> {FREE_ACTION.area}</div>
        <div style={{ marginTop: 6 }}><strong>Why:</strong> {FREE_ACTION.rationale}</div>
        <div style={{ marginTop: 6, color: '#475569' }}><strong>Constraint kept:</strong> {FREE_ACTION.constraint}</div>
      </div>

      <div style={{ marginTop: 14, display: 'grid', gap: 8 }}>
        {!applied && <button onClick={onApply} style={btn('#2563eb')}>Show the suggested position</button>}
        {applied && !markedDone && <button onClick={onMarkDone} style={btn('#047857')}>I have moved the chair</button>}
        {applied && (
          <button onClick={onProceed} style={markedDone ? btn('#1e293b') : btn('transparent', '#334155')}>
            {markedDone ? 'See what the full plan adds →' : 'Not now — see what the full plan adds →'}
          </button>
        )}
      </div>
    </div>
  );
}
