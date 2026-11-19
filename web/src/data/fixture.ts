// Fixture adapter: reads docs/fixtures/snapshot.sample.json. "now" is the
// snapshot's generated_at (docs/fixtures/README.md, "the fixture clock").
import raw from '../../../docs/fixtures/snapshot.sample.json';
import type { DataSource, DealsQuery, Snapshot } from './types';
import { validateSnapshot } from './validate';
import { filterDeals, PAGE_SIZE } from './query';

export const sample: Snapshot = validateSnapshot(raw);

export function fixtureSource(snap: Snapshot = sample): DataSource {
  const now = new Date(snap.generated_at);
  return {
    now: () => now,
    snapshot: async () => snap,
    async deals(q: DealsQuery = {}) {
      const all = filterDeals(snap.deals, q);
      const start = q.cursor ? Number(q.cursor) : 0;
      const end = start + PAGE_SIZE;
      return { deals: all.slice(start, end), next_cursor: end < all.length ? String(end) : null };
    },
    async deal(id: string) {
      const deal = snap.deals.find((d) => d.deal_id === id);
      if (!deal) return null;
      const group = snap.deals.filter((d) => d.group_id === deal.group_id && d.deal_id !== id);
      return { deal, group };
    },
    async meta() {
      return { run_id: snap.run_id, received_at: snap.generated_at, pipeline: snap.pipeline };
    },
  };
}
