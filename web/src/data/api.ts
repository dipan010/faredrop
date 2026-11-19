// Real adapter: phase 4 reads /deals.json, phase 5+ reads /api/* on the same
// origin (LLD §9). Left as a stub in phase 1.
import type { DataSource } from './types';

export function apiSource(_base = ''): DataSource {
  const todo = (what: string) => () => Promise.reject(new Error(`apiSource.${what}: not built yet (phase 4)`));
  return {
    now: () => new Date(),
    snapshot: todo('snapshot'),
    deals: todo('deals'),
    deal: todo('deal'),
    meta: todo('meta'),
  };
}
