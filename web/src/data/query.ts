// Feed filtering and sorting shared by the fixture adapter and (later) the
// client-side feed island. Mirrors GET /api/deals (LLD §5).
import type { DealsQuery, SnapshotDeal } from './types';
import { CITY_AIRPORTS, regionOf } from './places';
import { tripKind } from './format';

export const PAGE_SIZE = 12;

export function filterDeals(all: SnapshotDeal[], q: DealsQuery = {}): SnapshotDeal[] {
  const airports = q.city && q.city !== 'all' ? CITY_AIRPORTS[q.city] ?? [q.city] : null;
  const out = all
    .filter((d) => d.status === 'live' || d.status === 'stale')
    .filter((d) => !airports || airports.includes(d.origin))
    .filter((d) => !q.region || regionOf(d.destination) === q.region)
    .filter((d) => !q.trip || q.trip === 'any' || tripKind(d.nights) === q.trip);
  const sort = q.sort ?? 'saving';
  const by: Record<string, (a: SnapshotDeal, b: SnapshotDeal) => number> = {
    saving: (a, b) => b.saving_pct - a.saving_pct,
    price: (a, b) => a.price - b.price,
    soon: (a, b) => a.depart_date.localeCompare(b.depart_date),
  };
  return out.sort(by[sort]);
}
