// Display rules from docs/ui-spec.md §2 ("Formats"). Pure functions; every
// component formats through these so wording stays identical.
import type { SnapshotDeal, TripKind } from './types';
import { destCity } from './places';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
const DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];

/** ₹25,218 and ₹3,05,000 (Indian grouping). */
export function inr(n: number): string {
  return '₹' + Math.round(n).toLocaleString('en-IN');
}

/** 29.8 → 30. */
export function pct(p: number): number {
  return Math.round(p);
}

function parts(iso: string) {
  const [y, m, d] = iso.slice(0, 10).split('-').map(Number);
  return { y: y!, m: m! - 1, d: d!, wd: new Date(Date.UTC(y!, m! - 1, d!)).getUTCDay() };
}

/** "5–11 Apr", "27 Nov–6 Dec"; long adds the year: "5–11 Apr 2027". */
export function dateRange(from: string, to: string, long = false): string {
  const a = parts(from);
  const b = parts(to);
  const year = long ? ' ' + b.y : '';
  if (a.y === b.y && a.m === b.m) return `${a.d}–${b.d} ${MONTHS[b.m]}${year}`;
  const ay = long && a.y !== b.y ? ' ' + a.y : '';
  return `${a.d} ${MONTHS[a.m]}${ay}–${b.d} ${MONTHS[b.m]}${year}`;
}

/** "Mon 5 Apr 2027". */
export function flightDate(iso: string): string {
  const p = parts(iso);
  return `${DAYS[p.wd]} ${p.d} ${MONTHS[p.m]} ${p.y}`;
}

export function tripKind(nights: number): TripKind {
  return nights <= 5 ? 'short' : nights >= 14 ? 'long' : 'week';
}
export const TRIP_LABEL: Record<TripKind, string> = {
  short: 'Short break',
  week: 'A week away',
  long: 'Long holiday',
};

export function nightsLabel(n: number): string {
  return n === 1 ? '1 night' : `${n} nights`;
}

/** "non-stop" / "1 stop"; null when not recorded (G35). */
export function stopsShort(stops: number | null): string | null {
  if (stops == null) return null;
  return stops === 0 ? 'non-stop' : stops === 1 ? '1 stop' : `${stops} stops`;
}

/** "Non-stop both ways" / "1 stop each way, in Abu Dhabi". */
export function stopsLong(d: Pick<SnapshotDeal, 'stops' | 'via'>): string | null {
  if (d.stops == null) return null;
  if (d.stops === 0) return 'Non-stop both ways';
  const via = d.via?.length ? `, in ${d.via.map(destCity).join(' and ')}` : '';
  return `${d.stops === 1 ? '1 stop' : d.stops + ' stops'} each way${via}`;
}

/** "Vietjet · non-stop". */
export function flightLine(d: Pick<SnapshotDeal, 'airline_name' | 'stops'>): string {
  return [d.airline_name, stopsShort(d.stops)].filter(Boolean).join(' · ');
}

/** "40 min", "2 h", "yesterday", "2 days". */
export function age(fromIso: string, now: Date): string {
  const mins = Math.max(0, Math.round((now.getTime() - Date.parse(fromIso)) / 60000));
  if (mins < 60) return `${Math.max(1, mins)} min`;
  const h = Math.round(mins / 60);
  if (h < 24) return `${h} h`;
  const days = Math.round(h / 24);
  return days <= 1 ? 'yesterday' : `${days} days`;
}

/** "Checked 2 h ago", "Checked yesterday". */
export function checkedLabel(checkedAt: string, now: Date): string {
  const a = age(checkedAt, now);
  return a === 'yesterday' ? 'Checked yesterday' : `Checked ${a} ago`;
}

/** Fresh = checked within 24 h (dot colour, spec §2). */
export function isFresh(checkedAt: string, now: Date): boolean {
  return now.getTime() - Date.parse(checkedAt) < 24 * 3600 * 1000;
}

/** "Save ₹10,730 (30%)" and the other pill formats (C15). */
export type SavingFormat = 'save' | 'off' | 'minus' | 'you-save';
export function savingText(saving: number, savingPct: number, format: SavingFormat = 'save'): string {
  switch (format) {
    case 'off':
      return `${pct(savingPct)}% off usual`;
    case 'minus':
      return `−${pct(savingPct)}%`;
    case 'you-save':
      return `You save ${inr(saving)}`;
    default:
      return `Save ${inr(saving)} (${pct(savingPct)}%)`;
  }
}

/** "~₹39,000" when the usual price is an estimate (G7). */
export function usualText(usual: number, estimate: boolean): string {
  return (estimate ? '~' : '') + inr(usual);
}
