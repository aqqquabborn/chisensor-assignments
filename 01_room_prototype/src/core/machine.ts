import { AppState, type AppStore, type AnalysisJob, type SimulatedTask } from './types';

// ─── Valid Transitions ──────────────────────────────────────────

const TRANSITIONS: Record<AppState, AppState[]> = {
  [AppState.IDLE]:               [AppState.DEVICE_CHECK],
  [AppState.DEVICE_CHECK]:       [AppState.UNSUPPORTED, AppState.SCAN_CAPTURE],
  [AppState.UNSUPPORTED]:        [], // dead end
  [AppState.SCAN_CAPTURE]:       [AppState.SCAN_VALIDATE],
  [AppState.SCAN_VALIDATE]:      [AppState.SCAN_INCOMPLETE, AppState.ANALYZING],
  [AppState.SCAN_INCOMPLETE]:    [AppState.SCAN_CAPTURE], // retry
  [AppState.ANALYZING]:          [AppState.ANALYSIS_FAILED, AppState.FREE_ACTION],
  [AppState.ANALYSIS_FAILED]:    [AppState.ANALYZING], // retry
  [AppState.FREE_ACTION]:        [AppState.PAID_UPSELL],
  [AppState.PAID_UPSELL]:        [AppState.PURCHASE_PENDING],
  [AppState.PURCHASE_PENDING]:   [AppState.PURCHASE_VERIFIED],
  [AppState.PURCHASE_VERIFIED]:  [AppState.DELIVERY_FAILED, AppState.DELIVERED],
  [AppState.DELIVERY_FAILED]:    [AppState.DELIVERED], // retry delivery
  [AppState.DELIVERED]:          [], // terminal
};

export function canTransition(from: AppState, to: AppState): boolean {
  return TRANSITIONS[from]?.includes(to) ?? false;
}

/**
 * Attempt a state transition. Returns new store or null if invalid.
 * Pure function — no side effects.
 */
export function transition(store: AppStore, to: AppState): AppStore | null {
  if (!canTransition(store.state, to)) return null;
  return { ...store, state: to };
}

// ─── Analysis Job Factory ───────────────────────────────────────

const ANALYSIS_TASKS: Omit<SimulatedTask, 'status'>[] = [
  { id: 'detect_walls',    label: 'Detecting walls',         durationMs: 1200 },
  { id: 'map_furniture',   label: 'Mapping furniture',       durationMs: 1500 },
  { id: 'calc_paths',      label: 'Calculating paths',       durationMs: 1000 },
  { id: 'find_constraint', label: 'Identifying constraints', durationMs: 800 },
  { id: 'gen_plan',        label: 'Generating plan',         durationMs: 1400 },
];

/**
 * Deterministic job ID from a fixed seed so the same job
 * resumes identically after a page refresh.
 */
function makeJobId(seed: number): string {
  // Simple hash — deterministic, not cryptographic
  const h = ((seed * 2654435761) >>> 0).toString(16).padStart(8, '0');
  return `job_${h}`;
}

export function createAnalysisJob(constraints: string[], seed?: number): AnalysisJob {
  const s = seed ?? Date.now();
  return {
    jobId: makeJobId(s),
    status: 'running',
    progress: 0,
    tasks: ANALYSIS_TASKS.map((t) => ({ ...t, status: 'pending' as const })),
    currentTaskIndex: 0,
    constraints: [...constraints],
    startedAt: s,
    attempt: 1,
  };
}

/**
 * Recover a failed job: same job ID, same constraints, completed tasks kept;
 * only the failed task is reset and the run continues from there.
 */
export function resumeFailedJob(job: AnalysisJob): AnalysisJob {
  if (job.status !== 'failed') return job;
  return {
    ...job,
    status: 'running',
    attempt: job.attempt + 1,
    failedAt: undefined,
    tasks: job.tasks.map((t) => (t.status === 'failed' ? { ...t, status: 'pending' as const } : { ...t })),
  };
}

/**
 * Advance the analysis job by one tick.
 * Returns updated job. Pure — caller decides timing.
 */
export function tickAnalysis(job: AnalysisJob): AnalysisJob {
  if (job.status !== 'running') return job;

  const tasks = [...job.tasks.map((t) => ({ ...t }))];
  const idx = job.currentTaskIndex;

  if (idx >= tasks.length) {
    // All tasks done
    return { ...job, status: 'completed', progress: 100, tasks };
  }

  // Tick 1: pending → running (visible in UI)
  if (tasks[idx].status === 'pending') {
    tasks[idx].status = 'running';
    return { ...job, tasks };
  }

  // Tick 2: running → completed, advance to next
  if (tasks[idx].status === 'running') {
    tasks[idx].status = 'completed';
    const nextIdx = idx + 1;
    const progress = Math.round((nextIdx / tasks.length) * 100);

    if (nextIdx >= tasks.length) {
      return { ...job, tasks, currentTaskIndex: nextIdx, progress: 100, status: 'completed' };
    }
    return { ...job, tasks, currentTaskIndex: nextIdx, progress };
  }

  return { ...job, tasks };
}

/**
 * Fail the analysis at the current task.
 */
export function failAnalysis(job: AnalysisJob): AnalysisJob {
  if (job.status !== 'running') return job;
  const tasks = job.tasks.map((t, i) =>
    i === job.currentTaskIndex ? { ...t, status: 'failed' as const } : { ...t },
  );
  return { ...job, tasks, status: 'failed', failedAt: Date.now() };
}
