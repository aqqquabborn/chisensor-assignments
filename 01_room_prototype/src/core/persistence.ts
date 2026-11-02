import { AppState, type AppStore } from './types';
import { DEFAULT_CONSTRAINTS } from '../data/room';

const STORAGE_KEY = 'chisensor_app_store';

/**
 * Default store — entry point for every fresh session.
 */
export function defaultStore(): AppStore {
  return {
    state: AppState.IDLE,
    deviceSupported: null,
    scanResult: null,
    analysisJob: null,
    transaction: null,
    entitlement: null,
    freeActionApplied: false,
    freeActionMarkedDone: false,
    selectedConstraints: [...DEFAULT_CONSTRAINTS],
    injectAnalysisFailureAt: null,
    activeScenario: 'happy',
  };
}

/**
 * Validate a parsed object is a plausible AppStore.
 * Loose check — we trust shape, not deep invariants.
 */
function isValidStore(obj: unknown): obj is AppStore {
  if (!obj || typeof obj !== 'object') return false;
  const o = obj as Record<string, unknown>;
  return (
    typeof o.state === 'string' &&
    Object.values(AppState).includes(o.state as AppState) &&
    typeof o.freeActionApplied === 'boolean' &&
    typeof o.activeScenario === 'string'
  );
}

/**
 * Load persisted state. Returns default if nothing valid is stored.
 */
export function loadStore(): AppStore {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return defaultStore();
    const parsed = JSON.parse(raw);
    // Merge over defaults so a store saved by an older build still loads.
    if (isValidStore(parsed)) return { ...defaultStore(), ...parsed };
  } catch {
    // Corrupted or missing — start fresh
  }
  return defaultStore();
}

/**
 * Persist entire store. Called on every state change.
 */
export function saveStore(store: AppStore): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
  } catch {
    // Storage full or blocked — silent fail, app still works in-memory
  }
}

/**
 * Wipe persisted state (used by scenario switcher).
 */
export function clearStore(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // noop
  }
}
