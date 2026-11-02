import { BEDROOM, CONSTRAINTS, ROOM_GOAL } from '../data/room';
import RoomView from './RoomView';
import { Sim } from './ui';
import { btn, card, h2, lead } from './styles';

interface Props {
  selected: string[];
  onStart: () => void;
  onUnsupported: () => void;
}

/** Brief, item 1: show the room goal and its constraints before anything else. */
export default function StartScreen({ selected, onStart, onUnsupported }: Props) {
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>Your bedroom</h2>
      <p style={lead}><strong style={{ color: '#1e293b' }}>Goal:</strong> {ROOM_GOAL}</p>
      <RoomView room={BEDROOM} applied={false} />
      <div style={{ ...card, margin: '12px 0' }}>
        <strong>Constraints</strong>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18, lineHeight: 1.6 }}>
          {CONSTRAINTS.filter((c) => c.locked || selected.includes(c.id)).map((c) => (
            <li key={c.id}>{c.label}{c.locked ? '' : ' (your choice)'}</li>
          ))}
        </ul>
      </div>
      <Sim>This is a prototype. The device check, scan, analysis and payment are all simulated. No camera, sensor, photo or payment detail is ever requested.</Sim>
      <button onClick={onStart} style={btn('#1e293b')}>Start scan — simulated supported device</button>
      <button onClick={onUnsupported} style={{ ...btn('transparent', '#475569'), marginTop: 8, fontSize: 13 }}>
        Simulate: unsupported device
      </button>
    </div>
  );
}
