# faredrop product backend: low-level design (LLD)

Status: proposal, 2026-11-15. Read `docs/hld.md` first; this file assumes its
components and phases. Names in `code` that already exist in the repo are real
(checked 2026-11-15); everything else is new.

## 1. Repository layout (additions)

```
src/export.py              exporter (phase 1), runs in GitHub Actions
src/export_rules.py        allowlist + region map + status rules (pure, tested)
web/                       static site for Cloudflare Pages (phase 1+)
  index.html, deal.html, ...    built from the canvas screens
  theme.css                     the colour tokens (light + dark) from the mocks
api/                       Cloudflare Worker (phase 2+), TypeScript
  src/index.ts                  router
  src/ingest.ts, match.ts, send.ts, auth.ts, digest.ts, links.ts
  migrations/0001_init.sql      the D1 schema in section 4
  schema/snapshot.schema.json   the exporter ↔ Worker contract (section 3)
  wrangler.toml                 bindings and cron (no secrets)
tests/test_export.py       token-free, in the style of tests/test_pipeline.py
```

Python stays the engine's language. The Worker is TypeScript, because Workers'
Python support is still the less-trodden path. The contract between them is the
JSON schema in `api/schema/`, tested on both sides.

## 2. Exporter (`src/export.py`)

### 2.1 Placement

Add one step at the end of `gf.yml`, after `notify.py` and before
`dbstore.py push`:

```yaml
- name: Export deals to the product
  run: python3 src/export.py || echo "::warning::export failed"
  env:
    FAREDROP_INGEST_URL: ${{ secrets.FAREDROP_INGEST_URL }}   # phase 2+
    FAREDROP_INGEST_KEY: ${{ secrets.FAREDROP_INGEST_KEY }}   # phase 2+
```

- **Read-only** on the engine database: it opens SQLite and never writes, so it
  can't affect collection, `--reparse` or `dbstore.py`'s size guards.
- **Non-blocking** (`|| echo`), like the calendar step in `calendar.yml`.
- **Phase 1:** writes `web/deals.json` and deploys it to Pages; there's no Worker
  yet.
- **Phase 2+:** also POSTs the same body to `/internal/ingest`.

### 2.2 Which deals

```sql
SELECT d.*, q.usual, q.range_low, q.range_high, q.airline AS q_airline, q.via AS q_via
FROM deal d
LEFT JOIN gf_quote q ON q.id = -d.observation_id      -- Google deals store -quote_id
WHERE d.source = 'google_flights'
  AND d.gf_status IN ('still', 'gone')
  AND (d.detected_at >= :since_14d OR d.gf_checked_at >= :since_14d)
  AND d.origin IN (:EXPORT_ORIGINS) AND d.destination IN (:EXPORT_DESTINATIONS)
```

A deal found weeks ago but re-checked recently stays in the snapshot (BOM→SGN,
found 24 Oct, is the real case). Filtering on `detected_at` alone would make
long-lived deals vanish from the site while still bookable.

- Only Google-confirmed deals (`gf_status`), matching `VERIFY_REQUIRE_CONFIRMED`.
  Travelpayouts-only deals are never exported.
- **Allowlist** (`src/export_rules.py`), deliberately **not** `ALERT_ORIGINS`,
  which now includes the 14 Nov cities:
  ```python
  EXPORT_ORIGINS = {"BLR", "MAA", "COK", "HYD", "GOI", "GOX", "BOM", "CCU"}
  EXPORT_DESTINATIONS = {  # the original 25 of routes/gf_routes.json (2026-10-12)
      "DXB","AUH","SHJ","DOH","MCT","BAH","KWI", "SIN","KUL","BKK","HKT","DPS","SGN",
      "CMB","MLE","KTM", "HKG","TYO","SEL", "LON","PAR","FRA","AMS","IST", "SYD"}
  ```
  Widening the product's coverage later means changing these two sets on
  purpose, not as a side effect of a pipeline change.
- **Never exported:** `gf_cal_*` (the calendar experiment), probe outputs,
  `tools/simulate.py` data, `gf_raw` bodies.

### 2.3 Deal status (computed by the exporter)

| Status | Rule |
|---|---|
| `live` | `gf_status='still'` and `depart_date > today` and checked within 72 h |
| `stale` | `gf_status='still'`, but last checked more than 72 h ago (UI shows the "data is behind" state) |
| `ended` | `gf_status='gone'`, or `depart_date <= today` |

`checked_at = max(d.gf_checked_at, latest gf_quote.fetched_at for the same trip)`.

Open engine question: today a confirmed deal is only looked up again when
discovery happens to revisit it (`GF_RECHECK_DAYS` = 3 is a floor, not a
schedule). So many live deals will show as `stale` until the engine re-checks
live, exported deals on purpose. That re-check would spend Google lookups, so
it's a budget decision under the `GF_DAILY_LOOKUPS` rule, not something the
product side can fix. Until then the UI shows honest freshness ("checked 3 days
ago").

### 2.4 Identity and grouping

- `deal_id = f"{origin}-{destination}-{depart_date}-{return_date}"`. Readable,
  stable, and it carries no personal data.
- `group_id`: deals on the same route whose departures are within
  `NOTIFY_DUP_DEPART_DAYS` (7) of each other join one group, anchored on the
  cheapest. This is the clustering behind the "also this cheap on…" chips.
  It reuses the rule from `notify.near_duplicates`, kept in one function in
  `export_rules.py` and imported by `notify.py`, so there's one source of truth.

### 2.5 Route prices (for watched routes)

The latest Google price per route and departure month:

```sql
SELECT origin, destination, substr(depart_date,1,7) AS month,
       MIN(price) AS price, MAX(fetched_at) AS fetched_at
FROM gf_quote
WHERE fetched_at >= :since_14d AND price IS NOT NULL
  AND nights BETWEEN :GF_NIGHTS_MIN AND :GF_NIGHTS_MAX
GROUP BY origin, destination, month
```

This is Google data only, so a watch never fires on a Travelpayouts price (the
same rule as deals).

### 2.6 Email card

The exporter also renders each deal's email card with the existing
`notify._card(...)`: table-based HTML with inline styles. The card contains no
user-specific content. The Worker wraps it with the header, footer and the
user's signed links. This reuses the email-safe HTML that already works rather
than rewriting templates in TypeScript.

## 3. Snapshot contract (exporter → Worker)

```json
{
  "schema": 1,
  "run_id": "gf-2026-11-15T10:17:02Z",
  "generated_at": "2026-11-15T10:19:40Z",
  "pipeline": { "last_collect_at": "...", "last_gf_at": "...", "gf_answered_today": 41, "gf_budget": 60 },
  "deals": [{
    "deal_id": "BOM-SGN-2027-04-05-2027-04-11",
    "group_id": "BOM-SGN-2027-04-05-2027-04-11",
    "origin": "BOM", "destination": "SGN",
    "depart_date": "2027-04-05", "return_date": "2027-04-11", "nights": 6,
    "price": 25218, "usual": 35948, "range_low": 30500, "range_high": 44000,
    "saving": 10730, "saving_pct": 29.8,
    "airline": "VJ", "airline_name": "Vietjet", "stops": 0, "via": [],
    "status": "live", "detected_at": "...", "checked_at": "...",
    "card_html": "<table ...>...</table>"
  }],
  "route_prices": [
    { "origin": "BOM", "destination": "LON", "month": "2027-01", "price": 58210, "fetched_at": "..." }
  ]
}
```

**Transport (phase 2+):** `POST /internal/ingest` with these headers:
- `X-Faredrop-Timestamp`: Unix seconds.
- `X-Faredrop-Signature`: hex HMAC-SHA256 of `timestamp + "." + body`, keyed
  with `FAREDROP_INGEST_KEY`.

The Worker rejects anything signed more than 300 s ago, or any `run_id` it has
already applied (idempotency). The body is gzip-compressed; expected size is
under 200 KB.

## 4. D1 schema (`api/migrations/0001_init.sql`)

```sql
-- Users and auth --------------------------------------------------------------
CREATE TABLE users (
  id            TEXT PRIMARY KEY,          -- random 128-bit, base32
  email         TEXT NOT NULL UNIQUE COLLATE NOCASE,
  created_at    TEXT NOT NULL,
  verified_at   TEXT,
  plan          TEXT NOT NULL DEFAULT 'free',   -- 'free' | 'trial' | 'plus'
  plan_until    TEXT,                     -- trial/plus end; NULL for free
  consent_at    TEXT NOT NULL,            -- DPDP: when they agreed to the terms
  deleted_at    TEXT                      -- set briefly while purging
);
CREATE TABLE auth_codes (
  email         TEXT NOT NULL COLLATE NOCASE,
  code_hash     TEXT NOT NULL,            -- SHA-256(pepper || email || code)
  expires_at    TEXT NOT NULL,            -- +10 min
  attempts      INTEGER NOT NULL DEFAULT 0,
  created_at    TEXT NOT NULL
);
CREATE INDEX idx_auth_email ON auth_codes (email, created_at);
CREATE TABLE sessions (
  token_hash    TEXT PRIMARY KEY,         -- SHA-256 of the cookie value
  user_id       TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  created_at    TEXT NOT NULL,
  expires_at    TEXT NOT NULL             -- +30 days, sliding
);

-- Preferences -----------------------------------------------------------------
CREATE TABLE prefs (
  user_id        TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  origins        TEXT NOT NULL,           -- JSON array of airport codes, e.g. ["BOM","GOI","GOX"]
  regions        TEXT NOT NULL,           -- JSON array: gulf, sea, near, east, europe, aus
  nights_min     INTEGER NOT NULL DEFAULT 2,
  nights_max     INTEGER NOT NULL DEFAULT 21,
  min_saving     INTEGER NOT NULL DEFAULT 4000,   -- = MIN_ABS_SAVING
  instant_email  INTEGER NOT NULL DEFAULT 0,      -- Plus only
  weekly_digest  INTEGER NOT NULL DEFAULT 1,
  quiet_start    TEXT DEFAULT '23:00',            -- IST
  quiet_end      TEXT DEFAULT '07:00',
  paused_until   TEXT,                            -- unsubscribe "pause for a month"
  updated_at     TEXT NOT NULL
);

-- Deals mirrored from the engine (derived fields only) -------------------------
CREATE TABLE deals (
  deal_id      TEXT PRIMARY KEY,
  group_id     TEXT NOT NULL,
  origin       TEXT NOT NULL, destination TEXT NOT NULL, region TEXT NOT NULL,
  depart_date  TEXT NOT NULL, return_date TEXT NOT NULL, nights INTEGER NOT NULL,
  price        INTEGER NOT NULL, usual INTEGER, range_low INTEGER, range_high INTEGER,
  saving       INTEGER NOT NULL, saving_pct REAL NOT NULL,
  airline_name TEXT, stops INTEGER NOT NULL, via TEXT,
  status       TEXT NOT NULL,             -- live | stale | ended
  detected_at  TEXT NOT NULL, checked_at TEXT NOT NULL,
  first_price  INTEGER NOT NULL,          -- price when first ingested
  card_html    TEXT,
  updated_run  TEXT NOT NULL
);
CREATE INDEX idx_deals_live ON deals (status, origin, region);
CREATE INDEX idx_deals_group ON deals (group_id);
CREATE TABLE route_prices (
  origin TEXT, destination TEXT, month TEXT, price INTEGER, fetched_at TEXT,
  PRIMARY KEY (origin, destination, month)
);
CREATE TABLE ingest_runs (
  run_id TEXT PRIMARY KEY, received_at TEXT NOT NULL,
  deals INTEGER, new_deals INTEGER, changed INTEGER, ended INTEGER, pipeline TEXT
);

-- What users do -----------------------------------------------------------------
CREATE TABLE saved (
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE, deal_id TEXT NOT NULL,
  saved_at TEXT NOT NULL, price_at_save INTEGER NOT NULL,
  PRIMARY KEY (user_id, deal_id)
);
CREATE TABLE hidden (           -- "Not interested"; also a preference signal
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE, deal_id TEXT NOT NULL,
  hidden_at TEXT NOT NULL, PRIMARY KEY (user_id, deal_id)
);
CREATE TABLE watches (
  id TEXT PRIMARY KEY, user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  origin TEXT NOT NULL, destination TEXT NOT NULL,
  target INTEGER NOT NULL, created_at TEXT NOT NULL,
  last_notified_price INTEGER, last_notified_at TEXT
);
CREATE INDEX idx_watch_route ON watches (origin, destination);
CREATE TABLE feedback (
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE, deal_id TEXT NOT NULL,
  verdict TEXT NOT NULL,         -- good | not_for_me | price_different
  at TEXT NOT NULL, PRIMARY KEY (user_id, deal_id)
);

-- Sending -------------------------------------------------------------------------
CREATE TABLE alerts_sent (
  user_id TEXT REFERENCES users(id) ON DELETE CASCADE, deal_id TEXT NOT NULL,
  kind TEXT NOT NULL,            -- instant | digest | saved_change | watch
  sent_at TEXT NOT NULL, price INTEGER NOT NULL, provider_id TEXT,
  PRIMARY KEY (user_id, deal_id, kind)
);
CREATE INDEX idx_sent_user_time ON alerts_sent (user_id, sent_at);
CREATE TABLE send_queue (        -- held for quiet hours / the daily email cap
  id INTEGER PRIMARY KEY AUTOINCREMENT, user_id TEXT NOT NULL, kind TEXT NOT NULL,
  payload TEXT NOT NULL, not_before TEXT NOT NULL, priority INTEGER NOT NULL,
  attempts INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE email_counter (day TEXT PRIMARY KEY, sent INTEGER NOT NULL);

-- Payments (phase 4) ---------------------------------------------------------------
CREATE TABLE subscriptions (
  user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
  provider TEXT NOT NULL, provider_sub_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL,          -- active | cancelled_at_period_end | past_due | ended
  period_end TEXT NOT NULL, updated_at TEXT NOT NULL
);
CREATE TABLE payments (
  id TEXT PRIMARY KEY, user_id TEXT REFERENCES users(id) ON DELETE SET NULL,
  amount_paise INTEGER NOT NULL, status TEXT NOT NULL, invoice_no TEXT, at TEXT NOT NULL
);
```

Rate limiting uses a small `rate (key TEXT PRIMARY KEY, window_start TEXT,
count INTEGER)` table. KV would be cheaper per read, but one store is simpler at
this size.

**Region map** (`api/src/regions.ts`, mirrored in `export_rules.py`):

| Region | Destinations |
|---|---|
| gulf | DXB AUH SHJ DOH MCT BAH KWI |
| sea | SIN KUL BKK HKT DPS SGN |
| near | CMB MLE KTM |
| east | HKG TYO SEL |
| europe | LON PAR FRA AMS IST |
| aus | SYD |

**City → airports** (users pick cities): Goa = GOI + GOX; the others are one
airport each.

## 5. API

All responses are JSON, with errors shaped as
`{ "error": { "code": "...", "message": "..." } }`. Session is a cookie named
`fd_session`.

### Public

| Method & path | Purpose | Notes |
|---|---|---|
| `GET /api/deals?city=&region=&trip=&sort=&cursor=` | Feed | 12 per page (states sheet #6); default `status IN (live, stale)` |
| `GET /api/deals/:deal_id` | Deal page | Includes the group's other dates; `ended` deals return 200 with status, so the UI shows "Deal ended" |
| `GET /d/:deal_id` | Shared deal page | Server-rendered `<meta og:*>` with the preview image; no login |
| `GET /og/:deal_id.png` | Link preview image | Rendered once per deal, cached |
| `GET /api/meta` | Pipeline freshness for the stale banner | From the newest `ingest_runs` |

### Auth

| Method & path | Body | Behaviour |
|---|---|---|
| `POST /api/auth/start` | `{ email, consent?: true }` | Creates or loads the user, stores a code hash, emails the code. Always returns 200, so it doesn't reveal whether an account exists. Limits: 3 per email per 15 min, 20 per IP per hour |
| `POST /api/auth/verify` | `{ email, code }` | Max 5 attempts per code; sets `fd_session`; marks `verified_at` |
| `POST /api/auth/logout` | — | Deletes the session row |

### Signed in

| Method & path | Purpose |
|---|---|
| `GET /api/me` | Profile, plan, preferences, counts |
| `PUT /api/me/prefs` | Validate: origins ⊆ export allowlist; ≤ 1 city on Free, ≤ 5 on Plus; regions ⊆ map |
| `GET /api/me/saved` · `PUT /api/me/saved/:deal_id` · `DELETE /api/me/saved/:deal_id` | Saved deals (replaces the mock's browser storage) |
| `PUT /api/me/hidden/:deal_id` · `DELETE …` | "Not interested" / Undo |
| `GET/POST /api/me/watches` · `DELETE /api/me/watches/:id` | Route must be in the allowlist; Plus only |
| `POST /api/me/feedback` | `{ deal_id, verdict }` from the site |
| `GET /api/me/export` | DPDP data export (JSON) |
| `POST /api/me/delete` | Body `{ confirm: "DELETE" }`; deletes everything, ends the session, sends the confirmation |
| `GET /api/me/billing` · `POST /api/me/billing/cancel` · `POST /api/me/billing/resume` | Phase 4 |

### Signed one-click links (from emails, no session needed)

Token format: `base64url(user_id | purpose | subject | expiry) + "." + HMAC`,
keyed with `FAREDROP_LINK_KEY`. `purpose` is one of `fb` (feedback),
`unsub` (unsubscribe) or `pause`; `subject` is the deal id or the option.
Expiry is 30 days for feedback and 1 year for unsubscribe.

| Path | Behaviour |
|---|---|
| `GET /f/:token?v=good\|not_for_me\|price_different` | Upsert into `feedback`; show a thank-you page. A "price different" verdict also flags the deal for re-checking |
| `GET /u/:token` · `POST /u/:token` | Unsubscribe page; the POST is the one-click `List-Unsubscribe-Post` target |

### Internal

| Path | Auth | Purpose |
|---|---|---|
| `POST /internal/ingest` | HMAC (section 3) | Apply a snapshot |
| `GET /internal/verdicts?since=` | HMAC | `[{deal_id, good, not_for_me, price_different}]`; counts only, no user ids |
| `GET /ops/*` | Cloudflare Access (owner) | Pipeline health and deal feedback pages |
| `POST /webhooks/payments` | Provider signature | Subscription and payment events (phase 4) |

## 6. Ingest algorithm

```
apply(snapshot):
  if run_id in ingest_runs: return 200 (already applied)
  for d in snapshot.deals:
      old = deals[d.deal_id]
      region = REGION[d.destination]
      if old is None:            new.append(d)
      elif d.status == 'ended' and old.status != 'ended':  ended.append(d)
      elif abs(d.price - old.price) >= 1000:               changed.append((old, d))
      upsert deals (first_price kept from old)
  deals missing from the snapshot and older than 14 days → status 'ended'
  replace route_prices with snapshot.route_prices
  insert ingest_runs row
  enqueue: match(new), saved_changes(changed + ended), watches(route_prices)
```

The whole apply runs as one D1 `batch()`, so a half-applied snapshot can't
happen. Matching and sending run afterwards via `ctx.waitUntil`, so the engine
gets a fast 200 and never waits on email.

## 7. Matching and sending

### 7.1 Who gets a new deal

```
candidates = users JOIN prefs
  WHERE verified, not deleted, (paused_until IS NULL OR paused_until < now)
    AND deal.origin IN airports(prefs.origins)
    AND REGION[deal.destination] IN prefs.regions
    AND deal.nights BETWEEN nights_min AND nights_max
    AND deal.saving >= prefs.min_saving
    AND deal_id NOT IN hidden(user)
for each candidate:
    if near_duplicate(user, deal): skip             # 7.2
    if plan allows instant and prefs.instant_email:
        enqueue('instant', not_before = end_of_quiet_hours_if_inside(now), priority = deal.saving)
    else:
        nothing now; the Sunday digest picks it up
```

Filtering origins and regions in SQL keeps a single deal's matching to one
indexed query. At thousands of users, `prefs` could be split into
`pref_origins (user_id, airport)` rows; it's JSON for now, matched with
`json_each`.

### 7.2 Per-user near-duplicate rule

The same rule and constants as the engine (`NOTIFY_DUP_DAYS` = 14,
`NOTIFY_DUP_DEPART_DAYS` = 7, `NOTIFY_DUP_CHEAPER` = 0.05), applied per user
against `alerts_sent`:

> Skip if this user was sent a deal on the same route in the last 14 days,
> departing within 7 days of this one, unless this one is at least 5% cheaper.

The constants travel in the snapshot's `pipeline` block, so the Worker never
drifts from `config.py`.

### 7.3 Saved fare changed

Email the users who saved a deal when either of these happens:
- `ended`.
- The price dropped ≥ ₹1,000 below `price_at_save`, or rose above `range_low`
  ("out of deal territory").

At most one such email per deal per user per 24 h.

### 7.4 Watched routes

After each ingest, for each `route_prices` row with
`price <= watch.target`, email the watcher if
`last_notified_price IS NULL OR price < last_notified_price * 0.95`. That's at
most one email per watch per 3 days, and the email links to the route's newest
live deal if there is one.

### 7.5 Sending and the daily cap

- A queue drainer runs on a 15-minute Worker Cron Trigger and at the end of each
  ingest. It takes rows where `not_before <= now`, highest `priority` first.
- Before every send it checks `email_counter[today_utc] < EMAIL_DAILY_CAP`
  (default 95, under Resend's free 100/day). Sign-in codes bypass the queue and
  get a reserved headroom of 10.
- Over the cap, rows stay queued; deals that end before sending are dropped
  (states: "deal ended").
- Each send writes `alerts_sent` with the provider id. Provider errors retry
  three times with backoff, then are dropped and logged.
- Every alert email carries `List-Unsubscribe` and `List-Unsubscribe-Post`
  headers, the three feedback links, and the "why you got this" line from the
  mock.

### 7.6 Weekly digest

A Cron Trigger at `30 3 * * SUN` UTC (09:00 IST). For each user with
`weekly_digest = 1` who isn't paused: the top 5 deals by `saving_pct` from the
last 7 days that are still `live` and match their preferences, excluding deals
already sent to them instantly. It also includes the status of their watched
routes. Users with nothing to report are skipped, with no empty emails.

## 8. Plans (gating)

| Capability | Free | Trial (14 days) | Plus |
|---|---|---|---|
| Departure cities | 1 | 5 | 5 |
| Weekly digest | ✓ | ✓ | ✓ |
| Instant email | — | ✓ | ✓ |
| Watched routes | — | ✓ | ✓ |
| Saved deals, feed, deal pages | ✓ | ✓ | ✓ |

When a trial or Plus period ends, a daily cron sets `plan='free'`. It keeps the
user's first city and turns off instant email and watches. Watches are kept, not
deleted, so upgrading again restores them.

## 9. Frontend (`web/`)

- **Static HTML/CSS/JS on Pages,** built from the canvas screens.
  `theme.css` carries the light/dark tokens from the mocks
  (`prefers-color-scheme` plus a manual switch stored in `localStorage`).
- **Phase 1** reads `/deals.json` directly. **Phase 2** switches to `/api/*`
  on the same domain (Pages + Worker routes), so there's no cross-origin set-up.
- **Browser storage** holds only conveniences: theme, last filter. Saved deals
  and hidden deals live in the API once signed in, which replaces the mock's
  storage workaround.
- **States from the states sheet:** loading skeletons; "couldn't refresh" falls
  back to the last copy cached in `sessionStorage`; the stale banner comes from
  `/api/meta`; ended-deal pages; paging after 12 cards.
- **Accessibility:** real buttons and links, a visible `:focus-visible` outline,
  text contrast ≥ 4.5:1 in both themes.

## 10. Configuration and secrets

| Name | Where | Purpose |
|---|---|---|
| `FAREDROP_INGEST_URL`, `FAREDROP_INGEST_KEY` | GitHub secret + Worker secret | Exporter → Worker |
| `FAREDROP_LINK_KEY` | Worker secret | Email link tokens |
| `FAREDROP_CODE_PEPPER` | Worker secret | Sign-in code hashes |
| `EMAIL_API_KEY`, `EMAIL_FROM` | Worker secret / var | Email provider |
| `EMAIL_DAILY_CAP` | Worker var (default 95) | Section 7.5 |
| `PAYMENT_KEY_ID`, `PAYMENT_KEY_SECRET`, `PAYMENT_WEBHOOK_SECRET` | Worker secret | Phase 4 |
| D1 binding `DB` | `wrangler.toml` | Database |

As with the engine, writing GitHub secrets is the owner's job. No secret goes in
`wrangler.toml`, code, URLs or logs.

## 11. Data retention

| Data | Kept |
|---|---|
| `deals` | 90 days after `ended`, then deleted |
| `route_prices` | Replaced on every ingest |
| `alerts_sent` | 180 days (the near-duplicate rule only needs 14) |
| `auth_codes` | Deleted on use or after 1 day |
| `sessions` | Until expiry or logout |
| `feedback` | Kept while the account exists; aggregate counts are what the engine pulls |
| Users | Deleted on request immediately; `payments` keep only the amount and invoice number for tax law, with `user_id` nulled |

A daily cron does the clean-up.

## 12. Testing

- **`tests/test_export.py`** (token-free; uses a fixture DB like
  `tests/test_pipeline.py`):
  - the allowlist excludes the 14 Nov origins and destinations;
  - status rules (live / stale / ended);
  - grouping matches `notify.near_duplicates`;
  - the snapshot validates against `api/schema/snapshot.schema.json`;
  - no `gf_cal_*` fields leak.
- **Worker:** `vitest` with Miniflare's local D1 (free, offline):
  - ingest idempotency and the diff;
  - matching, including per-user duplicates and quiet hours;
  - the email-cap ordering;
  - token signing and expiry;
  - auth rate limits;
  - deletion cascades.
- **Contract:** the same fixture snapshot is checked by both test suites.
- **CI:** add a Worker test job to `check.yml`. It needs no secrets.

## 13. Observability

- `ingest_runs` gives a table of every ingest. The ops health page reads it,
  together with the snapshot's `pipeline` block. That block covers what
  `health.py` reports: Google answered per day, Travelpayouts coverage, budget.
- **Owner alerts** (by email, from the Worker): no ingest for 6 h; email cap hit;
  more than 5% of sends failing in a day; sign-in code abuse (rate limits
  tripping).
- No personal data in logs: user ids only, never email addresses.

## 14. Migration and cutover (phase 2)

1. Deploy the Worker and D1. The exporter starts POSTing, with ingest-only mode
   on: nothing is sent.
2. Create the owner's account (user #1) with today's `ALERT_ORIGINS`-equivalent
   preferences limited to the allowlist, instant email, Plus.
3. Turn on sending for user #1 only. For a week, compare the Worker's emails
   with `notify.py`'s, deal for deal.
4. When they match, set `notify.py` to dry-run in `gf.yml` (keeping its tests)
   and open sign-ups.
5. Move the review page's verdicts into `feedback` for user #1, and switch
   tuning to `/internal/verdicts`.

## 15. Out of scope here

- **WhatsApp and SMS** (dropped for now).
- **Native apps.**
- **More cities or destinations** (blocked by the allowlist until decided).
- **Holiday-aware ranking** (Stage 3 in `STATUS.md`).
- **Any change to how deals are found or judged:** the thresholds and Google
  budget stay in the engine and follow its existing rules.
