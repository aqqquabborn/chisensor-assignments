// ─── State Machine ───────────────────────────────────────────────
// A const object instead of `enum`: the project compiles with
// `erasableSyntaxOnly`, which rejects enums (this broke `npm run build`).

export const AppState = {
  IDLE: 'idle',
  DEVICE_CHECK: 'device_check',
  UNSUPPORTED: 'unsupported',
  SCAN_CAPTURE: 'scan_capture',
  SCAN_VALIDATE: 'scan_validate',
  SCAN_INCOMPLETE: 'scan_incomplete',
  ANALYZING: 'analyzing',
  ANALYSIS_FAILED: 'analysis_failed',
  FREE_ACTION: 'free_action',
  PAID_UPSELL: 'paid_upsell',
  PURCHASE_PENDING: 'purchase_pending',
  PURCHASE_VERIFIED: 'purchase_verified',
  DELIVERY_FAILED: 'delivery_failed',
  DELIVERED: 'delivered',
} as const;
export type AppState = (typeof AppState)[keyof typeof AppState];

// ─── Scan ────────────────────────────────────────────────────────

export interface ScanAreas {
  entry: boolean;
  bedside_path: boolean;
  bed_outline: boolean;
}

export const REQUIRED_SCAN_AREAS: (keyof ScanAreas)[] = ['entry', 'bedside_path', 'bed_outline'];

export interface ScanResult {
  areas: ScanAreas;
  timestamp: number;
}

// ─── Constraints ─────────────────────────────────────────────────

export interface Constraint {
  id: string;
  label: string;
  locked: boolean; // locked = always on (part of the brief), cannot be unticked
  fixedItemId?: string; // furniture this constraint keeps in place
}

// ─── Analysis ────────────────────────────────────────────────────

export interface SimulatedTask {
  id: string;
  label: string;
  durationMs: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
}

export interface AnalysisJob {
  jobId: string;
  status: 'running' | 'completed' | 'failed';
  progress: number; // 0–100
  tasks: SimulatedTask[];
  currentTaskIndex: number;
  constraints: string[]; // constraint ids the job runs with
  startedAt: number;
  attempt: number; // 1 on first run, +1 per retry of the same job
  failedAt?: number;
}

// ─── Payment ─────────────────────────────────────────────────────

export type TransactionStatus = 'pending' | 'verified' | 'cancelled';
export type DeliveryStatus = 'pending' | 'delivered' | 'failed';

export interface Transaction {
  transactionId: string;
  status: TransactionStatus;
  amount: number;
  createdAt: number;
  verifiedAt?: number;
  verificationEvents: number; // how many verification events arrived (dupes included)
}

export interface Entitlement {
  transactionId: string;
  granted: boolean;
  deliveryStatus: DeliveryStatus;
  deliveryAttempts: number;
  lastAttemptAt?: number;
}

// ─── Room ────────────────────────────────────────────────────────

export interface Rect {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface RoomItem extends Rect {
  id: string;
  label: string;
  movable: boolean;
}

export interface RoomData {
  width: number;
  height: number;
  items: RoomItem[];
  door: { x: number; y: number; side: 'left' | 'right' };
  entryPath: [number, number][];
  bedsidePath: [number, number][];
}

// ─── Free Action ─────────────────────────────────────────────────

export interface FreeAction {
  targetItemId: string;
  area: string;
  description: string;
  rationale: string;
  constraint: string;
  suggestedPosition: { x: number; y: number };
}

// ─── Scenarios ───────────────────────────────────────────────────

export type ScenarioKey =
  | 'happy'
  | 'unsupported'
  | 'scan_incomplete'
  | 'analysis_failed_recoverable'
  | 'purchase_pending'
  | 'verified_payment_delivery_failed';

// ─── App Store ───────────────────────────────────────────────────

export interface AppStore {
  state: AppState;
  deviceSupported: boolean | null;
  scanResult: ScanResult | null;
  analysisJob: AnalysisJob | null;
  transaction: Transaction | null;
  entitlement: Entitlement | null;
  freeActionApplied: boolean; // user opened the suggested change
  freeActionMarkedDone: boolean; // user says they actually did it
  selectedConstraints: string[];
  /** Simulated fault: fail the analysis once at this task index, then clear. Persisted, so a refresh keeps it. */
  injectAnalysisFailureAt: number | null;
  activeScenario: ScenarioKey;
}
