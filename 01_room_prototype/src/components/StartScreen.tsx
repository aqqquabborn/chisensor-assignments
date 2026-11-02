import { BEDROOM, CONSTRAINTS } from '../data/room';
import { useLang } from '../i18n/lang';
import type { Key } from '../i18n/strings';
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
  const { t } = useLang();
  return (
    <div style={{ padding: 16 }}>
      <h2 style={h2}>{t('start.title')}</h2>
      <p style={lead}><strong style={{ color: '#1e293b' }}>{t('start.goal')}</strong> {t('room.goal')}</p>
      <RoomView room={BEDROOM} applied={false} />
      <div style={{ ...card, margin: '12px 0' }}>
        <strong>{t('start.constraints')}</strong>
        <ul style={{ margin: '6px 0 0', paddingLeft: 18, lineHeight: 1.6 }}>
          {CONSTRAINTS.filter((c) => c.locked || selected.includes(c.id)).map((c) => (
            <li key={c.id}>{t(`constraint.${c.id}` as Key)}{c.locked ? '' : t('start.yourChoice')}</li>
          ))}
        </ul>
      </div>
      <Sim>{t('start.sim')}</Sim>
      <button onClick={onStart} style={btn('#1e293b')}>{t('start.cta')}</button>
      <button onClick={onUnsupported} style={{ ...btn('transparent', '#475569'), marginTop: 8, fontSize: 13 }}>
        {t('start.unsupported')}
      </button>
    </div>
  );
}
