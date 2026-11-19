// Runtime check that a snapshot matches LLD §3. The fixture adapter runs it
// at build time, so a fixture or type drift fails `astro build`.
import type { Snapshot } from './types';

const STATUSES = ['live', 'stale', 'ended'];
type Kind = 'str' | 'num' | 'arr' | 'bool';
const DEAL: Record<string, [Kind, boolean]> = {
  // field: [kind, nullable]
  deal_id: ['str', false], group_id: ['str', false], origin: ['str', false],
  destination: ['str', false], depart_date: ['str', false], return_date: ['str', false],
  nights: ['num', false], price: ['num', false], usual: ['num', true],
  range_low: ['num', true], range_high: ['num', true], saving: ['num', false],
  saving_pct: ['num', false], airline: ['str', true], airline_name: ['str', true],
  stops: ['num', true], via: ['arr', true], status: ['str', false],
  detected_at: ['str', false], checked_at: ['str', false], card_html: ['str', true],
};
const OPTIONAL: Record<string, Kind> = { usual_is_estimate: 'bool' }; // G7

function kindOf(v: unknown): Kind | 'null' | 'other' {
  if (v === null) return 'null';
  if (Array.isArray(v)) return 'arr';
  const t = typeof v;
  return t === 'string' ? 'str' : t === 'number' ? 'num' : t === 'boolean' ? 'bool' : 'other';
}

export function validateSnapshot(raw: unknown): Snapshot {
  const errs: string[] = [];
  const s = raw as Record<string, any>;
  if (!s || typeof s !== 'object') throw new Error('snapshot: not an object');
  if (s.schema !== 1) errs.push('schema must be 1');
  for (const k of ['run_id', 'generated_at']) if (typeof s[k] !== 'string') errs.push(`${k} must be a string`);
  const p = s.pipeline;
  if (!p || typeof p !== 'object') errs.push('pipeline missing');
  else {
    for (const k of ['last_collect_at', 'last_gf_at']) if (!(p[k] === null || typeof p[k] === 'string')) errs.push(`pipeline.${k}`);
    for (const k of ['gf_answered_today', 'gf_budget']) if (typeof p[k] !== 'number') errs.push(`pipeline.${k}`);
  }
  if (!Array.isArray(s.deals)) errs.push('deals must be an array');
  if (!Array.isArray(s.route_prices)) errs.push('route_prices must be an array');
  (s.deals ?? []).forEach((d: Record<string, unknown>, i: number) => {
    const at = `deals[${i}]`;
    for (const [k, [kind, nullable]] of Object.entries(DEAL)) {
      if (!(k in d)) { errs.push(`${at}.${k} missing`); continue; }
      const got = kindOf(d[k]);
      if (got === 'null' ? !nullable : got !== kind) errs.push(`${at}.${k}: ${got}`);
    }
    for (const k of Object.keys(d)) {
      if (!(k in DEAL) && !(k in OPTIONAL)) errs.push(`${at}.${k}: unknown field`);
      if (k in OPTIONAL && kindOf(d[k]) !== OPTIONAL[k]) errs.push(`${at}.${k}: ${kindOf(d[k])}`);
    }
    if (!STATUSES.includes(d.status as string)) errs.push(`${at}.status: ${d.status}`);
    const id = `${d.origin}-${d.destination}-${d.depart_date}-${d.return_date}`;
    if (d.deal_id !== id) errs.push(`${at}.deal_id != ${id}`);
  });
  (s.route_prices ?? []).forEach((r: Record<string, unknown>, i: number) => {
    for (const k of ['origin', 'destination', 'month', 'fetched_at']) if (typeof r[k] !== 'string') errs.push(`route_prices[${i}].${k}`);
    if (typeof r.price !== 'number') errs.push(`route_prices[${i}].price`);
  });
  if (errs.length) throw new Error('snapshot does not match LLD §3:\n  ' + errs.join('\n  '));
  return s as Snapshot;
}
