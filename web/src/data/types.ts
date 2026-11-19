// Types for docs/lld.md, the contract. §3 is the snapshot (exporter →
// Worker, and phase 1's /deals.json); §4–§5 give the API's shapes. Field
// names are the LLD's, unchanged.

export type IsoDateTime = string; // "2026-11-15T10:19:40Z"
export type IsoDate = string; // "2027-04-05"
export type Airport = string; // IATA code, e.g. "BOM"

export type DealStatus = 'live' | 'stale' | 'ended'; // LLD §2.3

/** One deal in the snapshot (LLD §3). */
export interface SnapshotDeal {
  deal_id: string; // `${origin}-${destination}-${depart_date}-${return_date}`
  group_id: string;
  origin: Airport;
  destination: Airport;
  depart_date: IsoDate;
  return_date: IsoDate;
  nights: number;
  price: number; // INR, one adult, return
  usual: number | null;
  range_low: number | null;
  range_high: number | null;
  saving: number;
  saving_pct: number;
  airline: string | null;
  airline_name: string | null;
  stops: number | null; // null only where the source doesn't record it (G35)
  via: Airport[] | null;
  status: DealStatus;
  detected_at: IsoDateTime;
  checked_at: IsoDateTime;
  card_html: string | null;
  /** Proposed in gap G7, not yet in the LLD: the usual price is an estimate. */
  usual_is_estimate?: boolean;
}

export interface Pipeline {
  last_collect_at: IsoDateTime | null;
  last_gf_at: IsoDateTime | null;
  gf_answered_today: number;
  gf_budget: number;
}

/** Monthly minimum for a watched route (LLD §2.5). */
export interface RoutePrice {
  origin: Airport;
  destination: Airport;
  month: string; // "2027-01"
  price: number;
  fetched_at: IsoDateTime;
}

/** The whole snapshot (LLD §3). */
export interface Snapshot {
  schema: 1;
  run_id: string;
  generated_at: IsoDateTime;
  pipeline: Pipeline;
  deals: SnapshotDeal[];
  route_prices: RoutePrice[];
}

// ---- API shapes -----------------------------------------------------------
// PROPOSED (gap G52): LLD §5 names the endpoints and request bodies but not the
// response bodies. DealsPage, DealDetail, Meta, Me, SavedItem and Watch
// below are this file's proposal; phase 5 writes them into LLD §5 or
// changes these types. Request bodies and Prefs do follow the LLD.

export interface ApiError {
  error: { code: string; message: string };
}

export type Region = 'gulf' | 'sea' | 'near' | 'east' | 'europe' | 'aus';
export type TripKind = 'short' | 'week' | 'long';
export type TripFilter = TripKind | 'any';
export type SortKey = 'saving' | 'price' | 'soon';

/** GET /api/deals query. */
export interface DealsQuery {
  city?: string;
  region?: Region;
  trip?: TripFilter;
  sort?: SortKey;
  cursor?: string;
}

/** GET /api/deals: 12 per page. */
export interface DealsPage {
  deals: SnapshotDeal[];
  next_cursor: string | null;
}

/** GET /api/deals/:deal_id: the deal plus its group's other dates. */
export interface DealDetail {
  deal: SnapshotDeal;
  group: SnapshotDeal[];
}

/** GET /api/meta: pipeline freshness for the stale banner. */
export interface Meta {
  run_id: string;
  received_at: IsoDateTime;
  pipeline: Pipeline;
}

export type Plan = 'free' | 'trial' | 'plus';

/** prefs table (LLD §4). */
export interface Prefs {
  origins: Airport[];
  regions: Region[];
  nights_min: number;
  nights_max: number;
  min_saving: number;
  instant_email: boolean;
  weekly_digest: boolean;
  quiet_start: string | null;
  quiet_end: string | null;
  paused_until: IsoDateTime | null;
}

/** GET /api/me. */
export interface Me {
  email: string;
  plan: Plan;
  plan_until: IsoDateTime | null;
  prefs: Prefs;
  counts: { saved: number; watches: number };
}

export interface SavedItem {
  deal_id: string;
  saved_at: IsoDateTime;
  price_at_save: number;
  deal: SnapshotDeal | null; // null once the deal has left the mirror
}

export interface Watch {
  id: string;
  origin: Airport;
  destination: Airport;
  target: number;
  created_at: IsoDateTime;
  last_notified_price: number | null;
  last_notified_at: IsoDateTime | null;
}

export type Verdict = 'good' | 'not_for_me' | 'price_different';

export interface FeedbackBody {
  deal_id: string;
  verdict: Verdict;
}

export interface AuthStartBody {
  email: string;
  consent?: true;
}
export interface AuthVerifyBody {
  email: string;
  code: string;
}

/** What every page reads deals through; fixture now, API later. */
export interface DataSource {
  /** "now" for freshness maths: the snapshot clock in fixture mode. */
  now(): Date;
  snapshot(): Promise<Snapshot>;
  deals(q?: DealsQuery): Promise<DealsPage>;
  deal(dealId: string): Promise<DealDetail | null>;
  meta(): Promise<Meta>;
}
