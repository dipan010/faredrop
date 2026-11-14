# faredrop product backend: high-level design (HLD)

Status: proposal, 2026-11-15. Nothing here is built yet. Companion: `docs/lld.md`.
Frontend mocks: the design canvas (link in `STATUS.md`).

## 1. Goal

Turn the personal deal alert into a product for other people: a public deals
site, accounts, email alerts matched to each user's cities and preferences,
saved deals, watched routes, a weekly digest, and an optional paid plan (Plus).

The deal engine (collection, detection, Google confirmation) already works and
is **not** redesigned here. This design adds the product side around it.

## 2. Constraints (inherited, non-negotiable)

| Constraint | Source | Consequence for the design |
|---|---|---|
| Free tools only; spell out what "free" means | user | Every service below names its free-tier limits (section 8) |
| The GitHub repo is public; no secret in code, commits, URLs or logs | CLAUDE.md | User data never enters the repo or GitHub Actions; secrets live in GitHub/Cloudflare secret stores |
| The collector must not miss days; raw payloads persisted before parsing | CLAUDE.md | The new export step is read-only and non-blocking; a failure never fails a collection run |
| Deals come from Google Flights; Travelpayouts is discovery/baseline only | CLAUDE.md | Only Google-confirmed deals are exported; watched routes use Google quotes only |
| Google data stays in `gf_raw`/`gf_quote` | CLAUDE.md | The export reads them; nothing new is written into `fare_observation` |
| Stay within `GF_DAILY_LOOKUPS` | CLAUDE.md | Users add **zero** Google lookups; features reuse what the pipeline already fetched |
| No WhatsApp for now | user, 2026-11-14 | Email is the only channel (instant for Plus, weekly digest for Free) |
| No test or experiment output in the product | user, 2026-11-14 | The calendar scan, probes and simulations are never exported |
| Hide the 14 Nov coverage expansion | user, 2026-11-14 | An export allowlist: 8 airports (BLR, MAA, COK, HYD, GOI, GOX, BOM, CCU) × the original 25 destinations |

## 3. System context

```
                       ┌──────────────────────────┐
  Travelpayouts API ──▶│                          │
  Google Flights   ──▶ │   Deal engine            │  existing, GitHub Actions
                       │   (collect, gfcollect,   │  encrypted SQLite on the
                       │    detect, verify)       │  `data` release
                       └────────────┬─────────────┘
                                    │ (1) signed snapshot of live deals
                                    ▼
 Visitors / users ◀──web──▶ ┌──────────────────────────┐ ◀──webhook── Payment provider
                            │  Product API + database  │                (phase 4)
 Owner (ops pages) ◀──────▶ │  (Cloudflare Worker + D1)│ ──email API──▶ Email provider ──▶ users
                            └────────────┬─────────────┘
                                         │ (2) verdict totals, pulled by the engine
                                         ▼
                                  threshold tuning (owner)
```

Two arrows cross the boundary between the engine and the product, and both are
narrow:

1. **Engine → product:** a signed snapshot of deals and recent route prices.
   No user data.
2. **Product → engine:** per-deal verdict counts, pulled by the engine.
   No emails, no identities.

## 4. Components

| Component | Runs on | Responsibility | New? |
|---|---|---|---|
| Deal engine | GitHub Actions (`collect.yml`, `gf.yml`) | Collect, detect, confirm on Google, near-duplicate rules | Existing |
| **Exporter** (`src/export.py`) | GitHub Actions, last step of `gf.yml` | Read confirmed deals and route prices, filter to the allowlist, build the snapshot, publish it | New |
| **Static site** | Cloudflare Pages | The screens from the canvas: landing, feed, deal pages, account pages | New |
| **Product API** | Cloudflare Worker | Ingest, deals API, sign-in, preferences, saved deals, watches, matching, sending, digest, feedback, unsubscribe, deletion | New |
| **Product database** | Cloudflare D1 (SQLite) | Users, sessions, preferences, saved deals, watches, mirrored deals, sent log, feedback, subscriptions | New |
| Email provider | e.g. Resend | Sends sign-in codes, alerts, digests, account emails | New |
| Payment provider | e.g. Razorpay | Plus subscriptions (phase 4 only) | New |
| Ops pages | Worker routes behind Cloudflare Access | Pipeline health, deal feedback (the internal screens) | New |

### Why Cloudflare (Workers + D1 + Pages)

- **D1 is SQLite**, the database `src/db.py` already uses, so the dialect,
  habits and tests carry over.
- **No pausing.** Supabase's free projects pause after 7 days of low activity.
  An alert service can go a week without a deal, which is exactly when it must
  not be asleep.
- **One platform** for static hosting, API, database and scheduled jobs (Cron
  Triggers), all on free plans.

Alternatives considered: Supabase (Postgres plus built-in auth; rejected because
of the pausing and the dialect change), Firebase (NoSQL, a poor fit for the
relational matching query), running the API inside GitHub Actions (rejected:
Actions isn't a server and must never hold user data).

## 5. Key flows

### 5.1 A deal reaches users

1. `gf.yml` runs hourly: `gfcollect` → `verify` → `notify` (owner email,
   unchanged until cutover) → **`export`**.
2. The exporter builds a **full snapshot** of every deal that is live or that
   changed in the last 14 days, and POSTs it to `/internal/ingest`, signed with
   HMAC.
3. The Worker upserts the deals and diffs them against the previous state:
   **new**, **price changed**, **ended**.
4. For each new deal it runs **matching** (city, region, trip length, minimum
   saving, plan), applies the per-user **near-duplicate rule** (the same
   14-day / 7-day / 5% rule as `notify.near_duplicates`), respects **quiet
   hours**, and either sends an instant email (Plus) or holds the deal for the
   digest (Free).
5. For ended or changed deals, users who saved them get a "saved fare changed"
   email.

A snapshot, rather than a list of changes, makes ingest idempotent: a missed or
repeated run fixes itself on the next one.

### 5.2 Sign-in (no passwords)

Email → 6-digit code (expires in 10 minutes, 5 attempts) → session cookie.

### 5.3 Weekly digest

A Worker Cron Trigger on Sunday at 09:00 IST picks, per user, the best deals
from the week that are still live, and sends one email.

### 5.4 Watched routes

A user sets a target price on one of the exported routes. Each snapshot carries
the latest Google price per route and month (from `gf_quote`, at no extra
lookups). When a price falls under a target, the user is emailed. Freshness is
whatever the pipeline already has: each route is looked up about every few days.
The UI must say so.

### 5.5 Feedback loop

Each alert email carries three signed one-click links (Great deal / Not my kind
of trip / Price was different) that write to `feedback`. The engine pulls
per-deal totals from `/internal/verdicts` to tune `GF_BELOW_RANGE_LOW` and
`MIN_ABS_SAVING`. This replaces the private review page.

### 5.6 Unsubscribe and delete

- **Unsubscribe:** signed links plus the `List-Unsubscribe` email header, with
  pause, digest-only, big-savings-only or all.
- **Delete:** removes every row for the user, and the confirmation email is the
  last thing ever sent to them.

## 6. Data ownership and privacy boundary

| Data | Lives in | Never in |
|---|---|---|
| Fares, raw Google pages, baselines | Engine SQLite (`data` release, encrypted) | D1 (only the exported, derived deal fields go there) |
| Email addresses, sessions, preferences, saved deals, watches, feedback, payments | D1 | The repo, Actions logs, the engine database |
| Secrets | GitHub secrets, Worker secrets | Code, URLs, logs |

Personal data is minimal: an email address and preferences. No phone number,
because WhatsApp is dropped. Payment card or UPI details stay with the payment
provider.

## 7. Reliability

| Failure | Effect | Handling |
|---|---|---|
| Pipeline misses runs | No new deals; prices go stale | The feed shows a "prices last checked N h ago" banner (states sheet #3); the Worker alerts the owner if no ingest for 6 h |
| Export or ingest fails | That run's deals are late | The step is non-blocking; the next run's snapshot catches up |
| Worker or D1 down | Site and alerts down; engine unaffected | The engine keeps collecting; the snapshot is re-sent next run |
| Email daily cap reached | Some instant alerts can't go out | Send in order of saving; the rest roll into the next day or the digest; the owner is alerted |
| Google blocks the scraper | No new deals at all | Already handled by the budget and back-off rules; product-wide, this is the main business risk (section 10) |

## 8. Capacity on free tiers

| Service | Free allowance (checked 2026-11-15) | Our expected use | First to break? |
|---|---|---|---|
| Cloudflare Workers | 100,000 requests/day, 10 ms CPU per request | Hundreds to low thousands/day | No |
| Cloudflare D1 | 5 GB storage, 5 M rows read/day, 100,000 rows written/day | Small | No |
| Cloudflare Pages | Static hosting | Small | No |
| Resend (email) | **100 emails/day**, 3,000/month | 1 email per matched user per deal + codes + digests | **Yes**: beyond a few dozen active users |
| GitHub Actions | Unchanged | Unchanged | No |

Sources: [Workers limits](https://developers.cloudflare.com/workers/platform/limits),
[D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/),
[Resend free tier](https://www.activepieces.com/blog/resend-pricing-2026-free-tier-plans-and-limits),
[Supabase pausing](https://supabase.com/kb/faqs/platform/free-project-pausing).

**Unavoidable costs:**
- **A domain** (yearly fee), needed for email authentication (SPF/DKIM) and the
  site.
- **Payment fees** per transaction, only once Plus exists.
- **Email beyond 100 a day:** Resend Pro is $20/month. This is the first paid
  step as users grow.

## 9. Security

- **Engine → Worker:** HMAC-SHA256 over timestamp + body with a shared secret,
  rejecting anything older than 5 minutes.
- **Sessions:** random 256-bit token, stored hashed, in an `HttpOnly`, `Secure`,
  `SameSite=Lax` cookie.
- **Sign-in codes:** stored hashed, rate-limited per email and per IP.
- **Email links** (feedback, unsubscribe): HMAC-signed, scoped to one purpose,
  with an expiry. They never contain the email address.
- **Ops pages:** behind Cloudflare Access (owner only).
- **Payment webhooks:** provider signature verified.
- **No personal data in URLs or query strings.**

## 10. Risks

1. **Deal supply** (business risk). The product's output is bounded by the
   pipeline's Google budget and the scraper not being blocked. More users don't
   make this worse, but more cities, more freshness or more watches do.
2. **Email deliverability.** A new domain sending alerts can land in spam.
   Needs SPF/DKIM/DMARC from day one and a slow ramp.
3. **Compliance** (DPDP Act, India). Consent at sign-up, export/delete, and a
   grievance contact. The privacy page is a draft that needs legal review.
4. **Price mismatch.** Users may see a different price than the scraped one
   (the CCU→FRA ~6% gap). The UI already says so and offers "Price was
   different".

## 11. Phased rollout

| Phase | Ships | Needs | Cost |
|---|---|---|---|
| 1. Read-only site | `export.py` writes `deals.json`; Pages serves feed, deal pages, landing | Pages | Free |
| 2. Accounts and instant email | Worker + D1, sign-in, preferences, ingest, matching, sending, unsubscribe, delete; the owner becomes user #1 and `notify.py` is retired | Domain, email provider | Domain fee |
| 3. Retention | Saved deals, saved-fare emails, watched routes, digest, feedback links, ops pages | — | Free within caps |
| 4. Plus | Payments, plan gating, receipts | Payment provider | Per-transaction fee |

Each phase is useful on its own, and each can be stopped without undoing the
previous one.

## 12. Open decisions (owner)

- Plus price, and the city limit (mocks say 5).
- Domain name and sender address.
- Email provider (Resend assumed).
- Whether Free users get instant alerts for one city or the digest only (mocks
  say digest only).
