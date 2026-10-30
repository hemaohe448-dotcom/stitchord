export const HISTORY_LIMIT = 100;

export function pushHistory<T>(past: T[], entry: T): T[] {
  return [...past, entry].slice(-HISTORY_LIMIT);
}
