import type { RoomData, FreeAction, Constraint, ScanAreas } from '../core/types';

/**
 * Bedroom used by the prototype. Coordinates in metres, 4 m × 3.5 m,
 * door on the left wall. The bed cannot move — the core constraint of the brief.
 */
export const BEDROOM: RoomData = {
  width: 4,
  height: 3.5,
  items: [
    { id: 'bed', label: 'Bed', x: 1.5, y: 0.5, w: 1.4, h: 2.0, movable: false },
    { id: 'chair', label: 'Chair', x: 0.3, y: 1.0, w: 0.6, h: 0.6, movable: true },
    { id: 'nightstand', label: 'Nightstand', x: 3.0, y: 0.8, w: 0.5, h: 0.5, movable: true },
    { id: 'dresser', label: 'Dresser', x: 0.1, y: 2.8, w: 1.2, h: 0.5, movable: true },
  ],
  door: { x: 0, y: 0.2, side: 'left' },
  entryPath: [[0, 0.5], [0.8, 0.5], [0.8, 1.5]],
  bedsidePath: [[0.8, 1.5], [1.3, 1.5], [1.3, 2.5], [2.2, 2.5]],
};

/**
 * Constraints the user confirms before the scan. Locked ones come from the brief
 * (renter: the bed cannot move; goal: no new furniture). The optional one shows
 * how a selected constraint changes the paid adjustment order.
 */
export const CONSTRAINTS: Constraint[] = [
  { id: 'bed_fixed', label: 'The bed stays where it is', locked: true, fixedItemId: 'bed' },
  { id: 'no_new_furniture', label: 'No new furniture — only move what is there', locked: true },
  { id: 'dresser_fixed', label: 'Keep the dresser where it is', locked: false, fixedItemId: 'dresser' },
];
export const DEFAULT_CONSTRAINTS = CONSTRAINTS.filter((c) => c.locked).map((c) => c.id);

export const ROOM_GOAL =
  'Make it easier to walk from the door to the bedside without buying furniture or moving the bed.';

/** The one complete free action: move the chair out of the entry path. */
export const FREE_ACTION: FreeAction = {
  targetItemId: 'chair',
  area: 'Entry path (door → bedside)',
  description: 'Move the chair out of the entry path, to the free corner opposite the door',
  rationale:
    'The chair sits on the line you walk from the door to the bed, so every entry means stepping ' +
    'around it. In the free corner it blocks neither the entry path nor the bedside path.',
  constraint: 'The bed stays in place and nothing is bought.',
  suggestedPosition: { x: 3.2, y: 2.8 },
};

export interface PlanStep {
  itemId: string;
  label: string;
  move: string;
}

const MOVES: Record<string, PlanStep> = {
  chair: { itemId: 'chair', label: 'Chair', move: 'Move it to the free corner opposite the door (the free action).' },
  dresser: { itemId: 'dresser', label: 'Dresser', move: 'Push it the last 20 cm back against its wall, so it does not narrow the walk at the foot of the bed.' },
  nightstand: { itemId: 'nightstand', label: 'Nightstand', move: 'Turn it so its drawer opens towards the bed, not into the path.' },
};
const ORDER = ['chair', 'dresser', 'nightstand'];

/**
 * The paid increment: an adjustment ORDER that respects the selected constraints.
 * Items held in place by a constraint are skipped and listed as fixed.
 */
export function buildAdjustmentPlan(constraintIds: string[]) {
  const fixed = new Set(
    CONSTRAINTS.filter((c) => constraintIds.includes(c.id) && c.fixedItemId).map((c) => c.fixedItemId as string),
  );
  return {
    steps: ORDER.filter((id) => !fixed.has(id)).map((id) => MOVES[id]),
    fixed: BEDROOM.items.filter((i) => fixed.has(i.id)).map((i) => i.label),
  };
}

/**
 * Paid report sections. No windows, compass readings or guaranteed results.
 * The 'reorder' section is filled from buildAdjustmentPlan at render time.
 */
export const PAID_REPORT_SECTIONS = [
  {
    id: 'reorder',
    title: 'Adjustment order for your constraints',
    preview: 'The order to move each piece, built around what must stay where it is.',
    detail: '',
  },
  {
    id: 'try',
    title: 'Try: one move at a time',
    preview: 'How to test each move before committing to it.',
    detail: 'Make one move, then walk from the door to the bedside twice. If you have to turn sideways anywhere, undo that move.',
  },
  {
    id: 'check',
    title: 'Check: is the path actually clearer?',
    preview: 'A simple check for each path after each move.',
    detail: 'Walk the entry path and the bedside path. Note any point where you touch furniture. Fewer touch points means the move helped.',
  },
  {
    id: 'save',
    title: 'Save: keep what works',
    preview: 'Record the layout you decide to keep.',
    detail: 'Mark each move as kept or undone, so the next scan starts from the layout you actually have.',
  },
  {
    id: 'review',
    title: 'Review: before and after',
    preview: 'Compare the original and the new layout.',
    detail: 'Side-by-side view of both layouts with the entry and bedside paths. No score or outcome is guaranteed — it depends on your room and how you use it.',
  },
] as const;

/** Example price for the exercise only — not an approved ChiSensor price. */
export const EXAMPLE_PRICE = 9.99;

/** The three required scan areas, as shown to the user. */
export const AREA_INFO: Record<keyof ScanAreas, { label: string; hint: string }> = {
  entry: { label: 'Entry', hint: 'Doorway and the first metre inside' },
  bedside_path: { label: 'Bedside path', hint: 'The walk from the entry to the side of the bed' },
  bed_outline: { label: 'Bed outline', hint: 'All four edges of the bed' },
};
