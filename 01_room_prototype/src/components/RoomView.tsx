import { type RoomData, type RoomItem, type FreeAction } from '../core/types';

interface Props {
  room: RoomData;
  freeAction?: FreeAction;
  applied: boolean;
  showPaths?: boolean;
}

const SCALE = 90; // 1m = 90px → 4m room = 360px (fits 390px screen)
const PAD = 15;

function itemColor(item: RoomItem, isTarget: boolean, applied: boolean): string {
  if (!item.movable) return '#64748b'; // slate — immovable
  if (isTarget && !applied) return '#ef4444'; // red — problem
  if (isTarget && applied) return '#22c55e'; // green — fixed
  return '#3b82f6'; // blue — movable
}

export default function RoomView({ room, freeAction, applied, showPaths = true }: Props) {
  const W = room.width * SCALE + PAD * 2;
  const H = room.height * SCALE + PAD * 2;

  const s = (v: number) => v * SCALE + PAD;

  const pathToD = (pts: [number, number][]) =>
    pts.map((p, i) => `${i === 0 ? 'M' : 'L'}${s(p[0])},${s(p[1])}`).join(' ');

  return (
    <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', maxWidth: W, display: 'block', margin: '0 auto' }}>
      {/* Room outline */}
      <rect
        x={PAD} y={PAD}
        width={room.width * SCALE} height={room.height * SCALE}
        fill="#f8fafc" stroke="#334155" strokeWidth={2} rx={4}
      />

      {/* Door */}
      <rect
        x={s(room.door.x) - 3} y={s(room.door.y)}
        width={6} height={30}
        fill="#f59e0b" rx={2}
      />
      <text x={s(room.door.x) + 8} y={s(room.door.y) + 18} fontSize={9} fill="#92400e">Door</text>

      {/* Paths */}
      {showPaths && (
        <>
          <path d={pathToD(room.entryPath)} fill="none" stroke="#10b981" strokeWidth={2} strokeDasharray="6 3" opacity={0.6} />
          <path d={pathToD(room.bedsidePath)} fill="none" stroke="#8b5cf6" strokeWidth={2} strokeDasharray="6 3" opacity={0.6} />
        </>
      )}

      {/* Furniture */}
      {room.items.map((item) => {
        const isTarget = item.id === freeAction?.targetItemId;
        const showAt = isTarget && applied && freeAction?.suggestedPosition
          ? { ...item, x: freeAction.suggestedPosition.x, y: freeAction.suggestedPosition.y }
          : item;

        return (
          <g key={item.id}>
            {/* Ghost of old position when moved */}
            {isTarget && applied && (
              <rect
                x={s(item.x)} y={s(item.y)}
                width={item.w * SCALE} height={item.h * SCALE}
                fill="none" stroke="#cbd5e1" strokeWidth={1} strokeDasharray="4 2" rx={3}
              />
            )}
            <rect
              x={s(showAt.x)} y={s(showAt.y)}
              width={item.w * SCALE} height={item.h * SCALE}
              fill={itemColor(item, isTarget, applied)}
              opacity={0.15} stroke={itemColor(item, isTarget, applied)}
              strokeWidth={1.5} rx={3}
            />
            <text
              x={s(showAt.x) + (item.w * SCALE) / 2}
              y={s(showAt.y) + (item.h * SCALE) / 2 + 4}
              textAnchor="middle" fontSize={11} fill={itemColor(item, isTarget, applied)}
              fontWeight={600}
            >
              {item.label}
            </text>
          </g>
        );
      })}

      {/* Legend */}
      {showPaths && (
        <g transform={`translate(${PAD + 4}, ${H - 26})`}>
          <line x1={0} y1={0} x2={16} y2={0} stroke="#10b981" strokeWidth={2} strokeDasharray="4 2" />
          <text x={20} y={4} fontSize={8} fill="#64748b">Entry</text>
          <line x1={56} y1={0} x2={72} y2={0} stroke="#8b5cf6" strokeWidth={2} strokeDasharray="4 2" />
          <text x={76} y={4} fontSize={8} fill="#64748b">Bedside</text>
        </g>
      )}
    </svg>
  );
}
