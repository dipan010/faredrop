# faredrop product build plan

Status: plan, 2026-11-15. Nothing in it is built yet.

One phase per chat thread. Each phase has a copy-paste prompt below. Every
prompt starts by pointing the new thread at **Shared context**, so a cold
thread has everything it needs. Run the phases in order; the table says what
each needs from earlier ones.

| # | Phase | Kind | Needs | Ships |
|---|---|---|---|---|
| 0 | Canvas → written UI spec | Spec | — | `docs/ui-spec.md`, fixtures |
| 1 | Frontend foundations | Frontend | 0 | `web/` app, tokens, components, component gallery |
| 2 | Public pages on fixtures | Frontend | 1 | Landing, feed, deal, ended, shared, privacy, contact, states |
| 3 | Exporter | Backend (engine) | 0 | `src/export.py`, snapshot schema, `deals.json` |
| 4 | Read-only site live | Integration | 2, 3 | Public site on real deals (product phase 1) |
| 5 | Product API core | Backend (Worker) | 3 | Worker + D1, ingest, deals API, sign-in, prefs, unsubscribe, delete |
| 6 | Account pages | Frontend + integration | 4, 5 | Sign-in, setup, first visit, My alerts, unsubscribe, delete |
| 7 | Matching and sending | Backend | 5, 6 | Per-user alerts, duplicate check, queue, cap; `notify.py` cutover |
| 8 | Retention | Backend + frontend | 7 | Saved, hidden, watches, digest, feedback links, ops pages |
| 9 | Plus | Backend + frontend | 8 | Plans, trial, payments, upgrade, manage Plus, account emails |

Phases 0–4 are product phase 1 (read-only site). 5–7 are product phase 2.
8 is product phase 3. 9 is product phase 4.

---

## Shared context (every thread reads this first)

**Project.** faredrop: a fare-deal alert for Indian cities. A working deal
engine runs on GitHub Actions (collect → gfcollect → detect → verify → notify),
storing an encrypted SQLite DB on the `data` release. We are turning it into a
consumer product.

**Read before doing anything:**
- `CLAUDE.md` (project rules), `STATUS.md` (Handoff), `README.md`.
- `docs/hld.md` and `docs/lld.md`: the backend design. Treat `docs/lld.md` as
  the contract: table names, endpoints, payload fields, rules.
- Design canvas (all screens, private, same account):
  https://claude.ai/artifact/GBnLGrXQ5L1bnpGKmnPGDr. Read its files with the
  Artifact tool (`action: "read"`, `path: "project/<Name>.dc.html"`); never
  publish to it unless the phase says so.
- Architecture page: https://claude.ai/artifact/6rCxMX8jAVoeionrv1dJJ8.
- `docs/ui-spec.md` once phase 0 has produced it.

**Product decisions (fixed, don't revisit):**
- No WhatsApp. Email only: instant email for Plus, Sunday digest for Free.
  Sign-in is an emailed 6-digit code.
- No test cards or experiment output in the UI (calendar scan, probes,
  simulations stay out).
- Product coverage = 8 airports (BLR, MAA, COK, HYD, GOI, GOX, BOM, CCU) × the
  original 25 destinations. The 14 Nov 2026 additions (DEL, JAI, LKO, ATQ, VNS,
  PNQ, AMD, TRV and the new destinations) are hidden from the product via an
  export allowlist, not by changing `ALERT_ORIGINS`.
- Plus: up to 5 departure cities; Free: 1 city. Prices are `[PRICE]` until the
  owner decides.

**Engineering rules (from CLAUDE.md and the owner):**
- Free tools only; state the free limits of anything new.
- Public repo: no secret, token or key in code, commits, URLs or output.
  Writing GitHub/Cloudflare secrets is the owner's job: say exactly which ones
  are needed and stop.
- The collector must not miss days: engine-side changes stay read-only or
  non-blocking; never weaken `dbstore.py` guards; Google data stays in
  `gf_raw`/`gf_quote`; stay within `GF_DAILY_LOOKUPS`.
- Commit messages carry no `Co-Authored-By` or other trailer. Ask before every
  commit; work on a branch named `phase-N-<slug>`.
- Run `python3 tests/test_pipeline.py` before finishing any engine change.

**Stack:** web = Astro + Preact islands + TypeScript + plain CSS with the
canvas tokens, in `web/`, deployed to Cloudflare Pages. API = Cloudflare Worker
(TypeScript) + D1, in `api/`. Engine stays Python in `src/`.

**Every thread ends by:** listing what changed, what was verified and how, what
is left; updating `STATUS.md` (Handoff and Open items) per CLAUDE.md; asking
before committing.

---

## Phase 0: canvas → written UI spec

```
Phase 0 of docs/build-plan.md: turn the design canvas into a written UI spec.
Read the "Shared context" section of docs/build-plan.md first and follow it.
Do not write application code in this phase.

Goal: produce docs/ui-spec.md and fixture data so later phases build from text,
not by re-reading 48 artboards.

1. Read the canvas files (project/canvas.json, then each .dc.html). Group the
   48 boards into ~20 real pages: desktop and phone boards of the same page
   become one responsive page; the deal-page variants become one template.
2. For each page write: route, purpose, sections in order, every interactive
   control and what it does, states (loading/error/empty/stale/ended where
   relevant), data it needs (fields, mapped to docs/lld.md names), which phase
   ships it, and the canvas boards it comes from.
3. Extract design tokens exactly from the canvas: the light and dark colour
   variables (from the themed boards' .fd blocks), type (Space Grotesk headings,
   Inter text, sizes used), spacing, radii, focus outline. Note contrast pairs.
4. List the reusable components (~20) with props, variants and states, and
   which pages use them.
5. Copy: collect every user-facing string per page into the spec so wording
   stays identical. Mark placeholders ([PRICE], [RENEWAL DATE], ...).
6. Create the fixture file docs/fixtures/snapshot.sample.json, shaped exactly like
   the snapshot in docs/lld.md section 3, using the real deals shown on the
   canvas (BOM-SGN, GOX-BKK, CCU-FRA, BOM-BAH, BLR-SGN, GOI-CMB group, GOI-DXB
   ended). No invented deals.
7. List gaps or contradictions between canvas and docs/lld.md and propose a
   resolution for each; don't silently pick.

Done when: docs/ui-spec.md covers every board, the token table matches the
canvas values, fixtures validate against docs/lld.md's field list, gaps listed.
```

## Phase 1: frontend foundations

```
Phase 1 of docs/build-plan.md: frontend foundations.
Read the "Shared context" section of docs/build-plan.md, then docs/ui-spec.md.

Goal: a web/ app with tokens, theming and every reusable component, shown on
one gallery page. No product pages yet.

1. Scaffold web/ with Astro + Preact + TypeScript (pin versions; state the free
   hosting limits of Cloudflare Pages you rely on). Keep the Node toolchain
   inside web/.
2. tokens.css from the spec: light on :root, dark under prefers-color-scheme
   (guarded :root:not([data-theme=light])) and :root[data-theme=dark]; a manual
   theme switch stored in localStorage (try/catch). Visible :focus-visible.
3. Build every component in the spec's list, with all variants and states.
   Interactive ones (chips, switches, segmented control, sheets, toasts) as
   Preact islands; everything else plain Astro.
4. A /dev/components gallery page showing each component in light and dark,
   at 390px and 1440px.
5. Checks: add Playwright + axe (free) with one test that loads the gallery in
   both themes and fails on accessibility violations. Wire it into CI
   (.github/workflows/check.yml) as a separate job that needs no secrets.
6. A data module (web/src/data/) with TypeScript types matching docs/lld.md
   (snapshot deal, API shapes) and a fixture adapter reading
   docs/fixtures/snapshot.sample.json. Real adapter left as a stub.

Done when: gallery matches the canvas side by side in both themes and both
widths, axe passes, CI job green.
Out of scope: product pages, backend, deployment.
```

## Phase 2: public pages on fixtures

```
Phase 2 of docs/build-plan.md: build the public pages against fixtures.
Read "Shared context" in docs/build-plan.md, then docs/ui-spec.md.

Pages: landing, deals feed, deal page (one template covering non-stop with
range, one stop with a very wide range, and no range), ended deal, shared deal
(/d/:id, with Open Graph tags and the 1200x630 preview card design), privacy,
contact. All responsive (390px to 1440px), light and dark, using only phase-1
components.

1. Feed: city chips, trip length and sort work on fixture data; "Not
   interested" with Undo is local state only for now (no account yet); paging
   after 12 cards; group chips ("also this cheap on").
2. Deal page: price-range bar per the spec (normal, broken scale when
   range_high is far above, comparison bars when there's no range); booking
   panel uses the exact-dates Google Flights link format from
   src/digest.py booking_url.
3. States from the states sheet: loading skeletons, couldn't-refresh with the
   last copy, data-is-behind banner (from fixture pipeline timestamps), ended,
   empty.
4. Save buttons and sign-in links render but point to "coming soon" behaviour;
   no fake persistence.
5. Playwright: landing → feed → filter → deal → booking panel; shared page has
   OG tags; axe on every page in both themes.

Done when: every page matches its canvas boards at both widths and themes,
tests pass. Out of scope: real data, deployment, accounts.
```

## Phase 3: exporter (engine side)

```
Phase 3 of docs/build-plan.md: the exporter.
Read "Shared context" in docs/build-plan.md, then docs/lld.md sections 2 and 3.
This touches the engine: CLAUDE.md's collector rules apply in full.

1. src/export_rules.py (pure functions, no I/O): EXPORT_ORIGINS and
   EXPORT_DESTINATIONS allowlists, region map, status rule (live/stale/ended),
   deal_id and group_id, and the near-duplicate grouping moved here from
   notify.near_duplicates so notify.py imports it (behaviour unchanged; prove it
   with the existing tests).
2. src/export.py: opens the DB read-only, runs the selection in lld 2.2
   (including recently re-checked deals), joins gf_quote for usual/range,
   computes route_prices (Google data only), renders card_html with the existing
   notify._card, writes web/public/deals.json, and (when FAREDROP_INGEST_URL is
   set) POSTs the HMAC-signed snapshot. Never writes to the DB.
3. api/schema/snapshot.schema.json matching lld section 3; export.py validates
   its own output against it.
4. tests/test_export.py, token-free, fixture DB: allowlist excludes the 14 Nov
   origins/destinations; status rules; grouping equals the old notify behaviour;
   no gf_cal_* data; schema-valid output.
5. gf.yml: add the export step after notify, before dbstore push, non-blocking
   (`|| echo "::warning::export failed"`). Don't enable the POST yet.
6. Decide with the owner how deals.json reaches the site (Pages redeploy each
   run vs a separately hosted file); check Cloudflare Pages' current deploy/build
   limits first and report them.
7. Run tests/test_pipeline.py and tests/test_export.py; run export.py on a
   decrypted copy of the production DB in a scratch path (never into
   data/faredrop.db) and report what it would publish.

Done when: tests pass, a real export looks right and contains only
allowlisted routes, gf.yml step added. Secrets: list any needed; owner sets them.
```

## Phase 4: read-only site live

```
Phase 4 of docs/build-plan.md: put the read-only site live on real deals.
Read "Shared context" in docs/build-plan.md. Phases 2 and 3 are done.

1. Implement the real data adapter in web/src/data/ reading deals.json the way
   phase 3 decided; keep the fixture adapter for tests.
2. Data-is-behind banner driven by the snapshot's pipeline timestamps; honest
   "checked X ago" from checked_at.
3. Shared deal pages and preview images for real deal_ids (build-time or
   on request, per phase 3's hosting decision).
4. Deploy to Cloudflare Pages (free pages.dev address is fine; custom domain
   later). Tell the owner exactly what to create in Cloudflare and which
   GitHub secrets/settings to add; don't create accounts yourself.
5. Watch two pipeline runs end to end: export → deals.json → site shows the
   new state. Check a missed run shows the stale banner.

Done when: the public site shows live, allowlisted deals and updates after each
run; tests still pass. Update STATUS.md: product phase 1 shipped.
```

## Phase 5: product API core

```
Phase 5 of docs/build-plan.md: the Worker and D1 core.
Read "Shared context" in docs/build-plan.md, then docs/lld.md sections 4, 5,
6, 9, 10, 11, 12.

1. api/ with wrangler, TypeScript, vitest + Miniflare local D1. No secrets in
   wrangler.toml.
2. migrations/0001_init.sql exactly as lld section 4 (all tables; billing
   tables created but unused).
3. POST /internal/ingest: HMAC check (300 s window), run_id idempotency, one
   D1 batch upsert, diff new/changed/ended, ingest_runs row. Ingest-only: no
   sending yet.
4. Public: GET /api/deals (filters, 12 per page), /api/deals/:id, /api/meta.
5. Auth: /api/auth/start, /verify, /logout per lld (hashed codes, 10 min,
   5 attempts, rate limits, same answer whether or not an account exists),
   session cookie. Sign-in code email through the email provider (free tier;
   state the limits).
6. /api/me, PUT /api/me/prefs (allowlist + plan validation), /api/me/export,
   POST /api/me/delete (cascade), signed unsubscribe links /u/:token with
   List-Unsubscribe-Post.
7. Tests for each of the above, including the contract test against
   docs/fixtures/snapshot.sample.json and api/schema/snapshot.schema.json.
8. Owner steps (list, then stop): Cloudflare account, D1 database, domain for
   email (SPF/DKIM/DMARC), email provider account, secrets FAREDROP_INGEST_KEY,
   FAREDROP_LINK_KEY, FAREDROP_CODE_PEPPER, EMAIL_API_KEY. Then enable the
   exporter's POST.

Done when: tests pass locally and in CI; deployed Worker accepts real
snapshots from the engine; sign-in works for the owner's address.
Out of scope: matching, alert sending, saved/watches, payments.
```

## Phase 6: account pages

```
Phase 6 of docs/build-plan.md: account pages, connected to the Worker.
Read "Shared context" in docs/build-plan.md and docs/ui-spec.md. Phases 4 and
5 are done.

Pages: sign in (email, then code), alert setup (3 steps: cities, regions + trip
length, how to tell you), first visit (no deals yet), My alerts, unsubscribe
(pause / digest only / big savings / all), delete account (type DELETE).

1. Switch web/src/data to the real API for auth, me, prefs, export, delete;
   same-origin cookies.
2. Plan limits in the UI match the API (Free 1 city, Plus 5); server errors
   shown in plain words.
3. Header shows signed-in state; protected pages redirect to sign in.
4. Playwright against a local Worker (Miniflare) with a test inbox stub:
   sign up → set preferences → sign out → sign in → delete account.

Done when: the full account loop works on the deployed site for the owner;
tests pass; axe clean in both themes.
```

## Phase 7: matching and sending

```
Phase 7 of docs/build-plan.md: per-user matching and alert email.
Read "Shared context" in docs/build-plan.md, then docs/lld.md section 7 and the
"Per-user duplicates" section of the architecture page.

1. Matching after ingest (ctx.waitUntil): verified, not paused, city/region/
   nights/min saving in one indexed query, minus hidden deals.
2. Per-user duplicate check against alerts_sent using pipeline.dup_rule from
   the snapshot (14/7/5%). Test it with the real GOI-CMB January case from the
   architecture page: 5-12 Jan sent, 7-12 Jan held, 16-19 Jan sent; a second
   user who never got 5-12 Jan does get 7-12 Jan.
3. send_queue with quiet hours (IST) and priority = saving; 15-minute cron
   drainer; email_counter daily cap (EMAIL_DAILY_CAP, default 95; sign-in codes
   keep 10 in reserve); drop deals that end while queued.
4. Alert email = card_html wrapped with header, footer, "why you got this",
   three signed feedback links, List-Unsubscribe headers. Check it in Gmail
   and a phone mail app.
5. Cutover per lld section 14: owner = user #1; a week of Worker emails
   side by side with notify.py, compared deal by deal; then notify.py to
   dry-run in gf.yml (keep its tests). Ask the owner before each step.

Done when: side-by-side week matches; owner approves cutover; tests cover the
duplicate rule, quiet hours and cap ordering.
```

## Phase 8: retention

```
Phase 8 of docs/build-plan.md: saved, hidden, watches, digest, feedback, ops.
Read "Shared context" in docs/build-plan.md, docs/ui-spec.md, docs/lld.md
sections 5, 7.3, 7.4, 7.6.

Backend: /api/me/saved, /hidden, /watches; saved-fare-changed emails (ended,
drop >= Rs 1,000, rose above range_low; one per deal per day); watch emails
from route_prices (Google data only; 5% better than last notified; once per
3 days); Sunday 09:00 IST digest cron (top 5 live matches, no empty emails);
GET /f/:token feedback links; GET /internal/verdicts (counts only); /ops/*
pages behind Cloudflare Access.

Frontend: Saved page (live, ended, watched routes), save/hide wired in feed and
deal pages, watch-this-route on deal pages, ops health and deal feedback pages
from the canvas.

Engine: a small tool (tools/, not the pipeline) that pulls /internal/verdicts
for threshold tuning; retire the private review page once verdicts flow.

Done when: each email type tested and checked in a real inbox; saved state
consistent across pages and devices; ops pages owner-only.
```

## Phase 9: Plus

```
Phase 9 of docs/build-plan.md: plans, trial and payments.
Read "Shared context" in docs/build-plan.md, docs/lld.md sections 4 (billing
tables), 5 (billing endpoints), 8 (plans).

Needs owner decisions first: Plus price, payment provider (Razorpay assumed),
trial length (14 days assumed). Ask before starting if any is missing.

1. Plan gating server-side (cities, instant email, watches); daily cron moves
   lapsed trials/Plus to Free, keeping the first city and pausing watches.
2. Payment provider in test mode only: subscription create, webhook with
   signature check, cancel at period end, resume; receipts and GST invoice
   numbers in payments.
3. Pages: upgrade (yearly/monthly, UPI or card handled by the provider's own
   checkout), manage Plus (status, change payment method, receipts, cancel
   flow).
4. Account emails: trial ending (3 days before), payment failed (7-day grace),
   receipts.
5. Privacy review checklist for the owner (DPDP consent, export, delete,
   grievance contact); the privacy page stays marked draft until reviewed.

Done when: test-mode payments work end to end; gating enforced by the API, not
just the UI; owner switches to live keys themselves.
```

---

## Side thread (any time): live-deal re-checks

```
Side thread from docs/build-plan.md: should the engine re-check live, exported
deals on a schedule? Read "Shared context" and docs/lld.md section 2.3.
Today a confirmed Google deal is only looked up again when discovery revisits
it, so freshness labels show days. Measure from the production DB (decrypted to
a scratch path) how old checked_at is for live deals, estimate the lookups a
re-check schedule would cost against GF_DAILY_LOOKUPS, and propose options with
numbers. Change nothing until the owner chooses.
```
