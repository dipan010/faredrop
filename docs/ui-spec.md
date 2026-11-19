# faredrop UI spec

Status: phase 0 output, 2026-11-19. Written from the design canvas
(https://claude.ai/artifact/GBnLGrXQ5L1bnpGKmnPGDr, version `1795082767-d03c`,
41 boards) so later phases build from text instead of re-reading the boards.
`docs/lld.md` is the backend contract; field names below are its names.
Where the canvas and the LLD disagree, section 7 lists the gap and a proposed
resolution. Nothing there has been decided silently.

How to read it:
- **Section 1** maps every canvas board to a page.
- **Section 2** has one block per page: route, purpose, sections, controls,
  states, data and phase.
- **Sections 3–4** cover tokens and components. **Section 5** covers the
  fixtures and **section 6** the placeholders.
- **Section 7** lists gaps. **Appendix A** has every user-facing string,
  verbatim, per page.
- The canvas's sample user is "Priya", `priya@example.com`, on a Plus trial with
  4 cities (Mumbai, Goa, Bengaluru, Kolkata). Those values are sample data, not
  copy.

Product rules that apply everywhere (from `docs/build-plan.md` Shared context):
- Email only.
- No test cards or experiment output in the UI.
- Coverage is 8 airports × the original 25 destinations, through the export
  allowlist.
- Plus allows up to 5 cities; Free allows 1.
- Prices show as `[PRICE]` until the owner sets them.

## 1. Boards → pages

Of the 41 boards, 35 are themed: each has `data-theme` and carries the token
block. The other 6 aren't: 4 emails, the link-preview image and the dark-mode
reference sheet. Desktop and phone boards of one page become one responsive
page, with the phone layout at ≤ 640 px. The three deal boards become one
template.

| # | Page | Route | Boards | Ships in phase |
|---|---|---|---|---|
| P1 | Landing | `/` | Landing, PhoneLanding | 2 |
| P2 | Deals feed | `/deals` | Main, Mobile, DarkMode (feed), States 1, 2, 3, 6, 7 | 2 (public), 6 (signed-in header), 8 (save/hide wired) |
| P3 | Deal page (template) | `/deals/:deal_id` | DealDetail, DealOneStop, DealNoRange, PhoneDeal, DarkMode (deal), States 4, 5 | 2; watch + save wired in 8 |
| P4 | Deal ended / gone | `/deals/:deal_id` when `status = ended` or unknown id | Expired, States 8 | 2 |
| P5 | Shared deal | `/d/:deal_id` | ShareDeal, PhoneShare | 2 (static on fixtures), 5 (Worker-rendered OG tags) |
| P6 | Link preview image | `/og/:deal_id.png` | SharePreview | 2 (design), 5 (rendered) |
| P7 | Set up alerts | `/start` | OnboardingWeb, Onboarding | 6 |
| P8 | Sign in | `/signin` | SignIn, PhoneSignIn | 6 |
| P9 | First visit (no deals yet) | `/welcome` | Empty | 6 |
| P10 | My alerts | `/alerts` | Settings, PhoneSettings | 6 (Plus banner and billing link in 9) |
| P11 | Saved | `/saved` | Saved, PhoneSaved | 8 |
| P12 | Unsubscribe | `/u/:token` | Unsubscribe, PhoneUnsubscribe | 6 |
| P13 | Delete account | `/alerts/delete` | DeleteAccount, PhoneDelete | 6 |
| P14 | Contact | `/contact` | Contact, PhoneContact | 2 (form posts in 5+) |
| P15 | Privacy | `/privacy` | Privacy, PhonePrivacy | 2 (export button wired in 6) |
| P16 | Upgrade to Plus | `/plus` | Upgrade, PhoneUpgrade | 9 |
| P17 | Plus and billing | `/alerts/plus` | ManagePlus, PhoneManagePlus | 9 |
| P18 | Ops: pipeline health | `/ops/health` | OpsHealth | 8 |
| P19 | Ops: deal feedback | `/ops/feedback` | Feedback | 8 |
| E1 | Deal alert email | — | Email | 7 |
| E2 | Weekly digest email | — | DigestEmail | 8 |
| E3 | Saved fare changed email | — | PriceChangeEmail | 8 |
| E4 | Trial ending email | — | AccountEmails (top) | 9 |
| E5 | Payment failed email | — | AccountEmails (bottom) | 9 |
| — | Design system references | — | States (all 8 sections), DarkMode (token table) | 1 |

Every board is covered. The States and DarkMode boards are references: their
parts are assigned to the pages above, and their tokens are in section 3.

Routes are proposals; only `/d/`, `/og/`, `/u/` and `/f/` are fixed by
`docs/lld.md` §5 (see gap G1). Pages that exist in the LLD but have no board:
- the sign-in code email,
- the account-deleted confirmation email,
- the feedback thank-you page `/f/:token`,
- the watch-triggered email.

Gap G2 covers them.

## 2. Pages

Conventions for every page:
- **Header:** the `SiteHeader` variant is named per page.
- **Phone:** phone layouts use `PhoneTabBar` on Deals, Saved and My alerts.
- **Max widths:** content is centred at a max width of 1200 px (1240 on the
  feed, 1080 on the deal page, 880 or 680 on forms and text pages), with 24 px
  side padding, or 16 px on phone.
- **Prices:** always `₹` + `en-IN` grouping (`₹3,05,000`). A saving
  percentage is `round((1 − price/usual) × 100)`, and the LLD's `saving_pct`
  29.8 shows as 30%.
- **Dates:** a short form "5–11 Apr" (same month) or "27 Nov–6 Dec"; a
  long form adds the year on deal pages ("5–11 Apr 2027"); flight rows use the
  weekday ("Mon 5 Apr 2027").
- **City names:** from airport codes: BOM Mumbai, BLR Bengaluru, GOI and GOX
  Goa, CCU Kolkata, HYD Hyderabad, MAA Chennai, COK Kochi. GOX shows as
  "Goa (Mopa)" in the deal-page subtitle only.
  - Destination names, as the canvas shows them: SGN Ho Chi Minh City, BKK
    Bangkok, FRA Frankfurt, BAH Bahrain, CMB Colombo, DXB Dubai, SHJ Sharjah.
  - The rest come from the engine's place names (gap G3).
- **Trip kind:** `nights ≤ 5` is "Short break", `nights ≥ 14` is "Long
  holiday", and anything else is "A week away". The filter values are `short`,
  `week` and `long`, with `any` for all.
- **Stops:** "non-stop" or "1 stop", from `stops`. On deal pages the long
  form is "Non-stop both ways" or "1 stop each way, in {via city}".
- **Freshness:** "Checked {40 min | 2 h | yesterday | 2 days} ago", from
  `checked_at`. The dot is `--good-dot` when `checked_at` is within 24 h and
  amber `#C98A0B` when older (gap G4).

### P1 Landing `/`

Purpose: explain the product and take a departure city plus an email straight
into setup.

Sections in order:
1. **Header (`SiteHeader` public):**
   - logo,
   - anchor links "How it works" (`#how`), "Recent deals" (`#deals`) and
     "Pricing" (`#pricing`),
   - a "Sign in" pill linking to `/signin`.

   On phone, the anchors collapse and only the logo and Sign in remain.
2. **Hero:**
   - eyebrow, H1 and lede;
   - a form with an "I fly from" select (the 7 cities) and an Email input;
   - the primary CTA "Get deal alerts, free", which goes to `/start` with
     `?city=&email=` prefilled;
   - three check-marked facts.

   On the right, the hero shows a stacked teaser of two deal cards: BOM→SGN
   and, behind it, GOX→BKK. The front card has "New deal · just now", the
   price, the struck usual price, a `PriceBar` at 70 %, the pill "You save
   ₹10,730" and "Book →".

   On phone, the teaser follows the form and is titled "What an alert looks
   like".
3. **How it works (`#how`):** H2 and 3 numbered steps.
4. **Recent deals (`#deals`):**
   - H2 and the note "Return fares, one adult, at most one stop.";
   - a grid of `DealCard` (variant `mini`): from, to, price, struck usual and
     a pill "{pct}% off usual".

   Only deals with a known `usual` are shown; the canvas filters out GOI→DXB
   for that reason.
5. **Trust band:** a dark band (`--ink` background), three columns, H3 + body.
6. **Pricing (`#pricing`):**
   - **Free card:** ₹0, 3 bullets, an outline button "Start free" to `/start`.
   - **Plus card:** accent border, "Recommended" tag, `[PRICE] / year`, 4
     bullets, an accent button "Try Plus" to `/plus`.
7. **Footer:** "© faredrop", the disclaimer, and Privacy and Contact links.

States: the recent-deals grid uses skeleton cards while loading. If it can't
load, the section is hidden; the page never shows an empty grid.

Data: `deals[]` with `status in (live, stale)`, sorted by `saving_pct`; the
canvas shows 7, including one ended (BOM→SGN, BOM→BAH, GOX→BKK, BLR→SGN,
CCU→FRA, HYD→SHJ, GOI→CMB). The fields used are `origin`, `destination`,
`price`, `usual` and `saving_pct`.

The headline counts "7 departure cities" and "25 destinations" are product
constants: the 7 cities are the 8 airports with Goa's two merged.

### P2 Deals feed `/deals`

Purpose: every live deal, filterable. Public in phase 2; personalised once
signed in (phase 6).

Sections:
1. **Header:**
   - **Signed in (`SiteHeader` app):** nav "Deals" (current), "Saved" with a
     count badge, "My alerts"; the status pill "Email alerts on" (to
     `/alerts`); an avatar initial (to `/alerts`, `aria-label="Your
     account"`).
   - **Public:** the same nav with "Sign in" in place of the pill and avatar.
2. **Intro:**
   - **Signed in:** the greeting "Good morning, {name}" (gap G5: the LLD has no
     name field); the H1 "{n} international fares well under their usual
     price"; the sub "From {user's cities}. Every fare here was priced twice
     before we showed it to you."; a link "Change cities" to `/alerts`.
   - **Public:** the H1 counts all deals; the sub drops "From …" (gap G5).
3. **Filters (`aria-label="Filters"`):**
   - city chips (`ToggleChip`, single-select): "All my cities" plus each of the
     user's cities; public shows all 7 cities;
   - a "Trip" select: `any`, `short`, `week`, `long`;
   - a "Sort" select: `saving` (by `saving_pct` descending), `price`
     (ascending), `soon` (`depart_date` ascending).

   On phone, the chips scroll horizontally under the header ("All", then the
   cities), the Trip and Sort selects are absent, the default sort is saving,
   and the count line reads "{n} deals · biggest saving first".
4. **Undo toast:** `role="status"`, "Hidden {from} → {to}. We'll show you
   fewer trips like it." with an "Undo" button. It appears after "Not
   interested".
5. **Empty result:** "No deals match right now", the body text, and a "Clear
   filters" button that resets the city, the trip and any hidden deals.
6. **Card grid of `DealCard` (variant `feed`):**
   - destination city, "from {city} · {ORIG} → {DEST}";
   - a save bookmark (`aria-pressed`, `aria-label="Save this deal"`);
   - the price, "usually" and the struck usual price;
   - the pill "Save ₹x (y%)";
   - a facts row: dates · "{n} nights" · "{airline} · {stops}" · trip kind;
   - when the group has other dates, a `DateChips` block titled "Also this
     cheap on {k} other date(s)";
   - a freshness dot and text;
   - a "Not interested" text button and a "See deal" link.

   The phone variant (`compact`) is one row per deal: "BOM → SGN", meta
   "14–18 Apr · Kuwait Airways, 1 stop" (+ "· +{k} dates" when grouped), the
   price and "−{pct}% vs usual". The whole row links to the deal.
7. **Paging (States 6):** after 12 cards, show "Showing 12 of {n} deals" and a
   "Show more deals" button; the API page size is 12.
8. **Footnote:** the "Prices are for one adult…" disclaimer.

States:
- **Loading (States 1):** 2–3 skeleton cards in the card's shape.
- **Couldn't refresh (States 2):**
  - a `Banner` (error, `role="alert"`) reading "We couldn't refresh deals" /
    "Showing what we had at {HH:MM} today. Check prices before booking.",
    with a "Try again" button, over the last copy from `sessionStorage`;
  - with no copy at all, a full-page message and "Try again", with no empty
    grid.
- **Data is behind (States 3):**
  - a `Banner` (warn, `role="status"`): "Prices below were last checked {2
    days ago}. We're catching up; check the price before you book.";
  - it shows when `/api/meta` (`/deals.json`'s `pipeline` in phase 2) says
    the last check is more than 72 h old, or when every shown deal is `stale`;
  - in dark mode it sits at the bottom of the feed.
- **Phone offline (States 7):** a slim top bar "You're offline · last update
  {HH:MM}" with a "Retry" button, over the cached list.
- **No match:** see item 5.

Data:
- **Deal fields:** `deals[]` (`status in (live, stale)`) with `deal_id`,
  `group_id`, `origin`, `destination`, `depart_date`, `return_date`, `nights`,
  `price`, `usual`, `saving`, `saving_pct`, `airline_name`, `stops`, `status`
  and `checked_at`.
- **Group dates:** the other deals with the same `group_id`.
- **Signed in:** `GET /api/me` (cities, saved count), `saved` and `hidden`.
- **Phase 2:** "Not interested" and Undo are local state only. Save renders
  but leads to sign-in or "coming soon" (plan, phase 2, step 4).

### P3 Deal page `/deals/:deal_id` (one template, three variants)

Purpose: everything needed to trust and book one fare.

Layout:
- **Desktop:** a main column with an aside on the right (the aside comes first
  in the reading order on phone).
- **Phone (PhoneDeal):**
  - a top bar with "Back to deals", "{ORIG} → {DEST}" and a Share icon button;
  - a sticky bottom bar with the save bookmark and the primary button "Book for
    ₹{price}";
  - the booking panel opens as a bottom sheet (`role="dialog"`,
    `aria-label="Where to book"`, with a Close button).

Main column:
1. **Back link** "All deals" to `/deals`.
2. **Status line:** a "Price checked twice" chip and "Last checked {age}".
3. **H1:** "{ORIG} → {DEST}" in large codes (on phone the H1 is the
   destination city name instead).
4. **Subtitle:** "{Origin city} to {Dest city} · {5–11 Apr 2027} · {n} nights
   · return, 1 adult".
5. **Price block:** the price, then "₹{saving} ({pct}%) below" and "the usual
   ₹{usual}".
6. **Price section (`PriceRangeBar`),** in one of three variants chosen from
   the data:
   - **`range`:** used when `range_low` and `range_high` are present and
     `range_high ≤ 2.5 × usual`. Proposed rule (gap G6).
     - Title "Where this price sits", sub "What this trip normally costs on
       these dates, and where today's fare lands.";
     - the bar shows the normal range from `range_low` ("cheapest normal") to
       `range_high` ("priciest normal"), a "usual ₹x" tick and a "this deal"
       marker.
     - Canvas: BOM-SGN, 30,500–44,000.
   - **`broken`:** used when `range_high` is far above the usual price.
     - Sub "The normal range for these dates is unusually wide, so the scale is
       cut at ₹{cap}.";
     - the scale ends with a break glyph and the label "up to ₹{range_high}" /
       "long multi-airline trips";
     - the marker reads "₹{price} this deal";
     - a note follows: "The top of the range comes from long trips with several
       airlines. We judge this fare against the usual price and the cheapest
       normal fare, not the top."
     - Canvas: GOX-BKK, 36,500–3,05,000, cap ₹60,000. Proposed cap is
       `ceil(1.1 × usual / 10,000) × 10,000` (gap G6).
   - **`none`:** used when `range_low` or `range_high` is null.
     - Title "How it compares", sub "We know the usual price for these dates
       but not the full range, so this is a straight comparison.";
     - two horizontal bars, "Usual price" and "This deal";
     - a note follows: "Prices can differ a little between sites, and a
       signed-in browser sometimes shows a lower one. If you see a different
       price, tell us from the booking panel."
     - Canvas: CCU-FRA.
     - When `usual` is an estimate, show "about" / "~" (States 5, gap G7).
7. **"Why it counts as a deal" (`CheckList`, 5 rows),** each built from the
   data:
   1. `{pct}% under what this trip usually costs`, whose detail depends on the
      variant:
      - **range:** "Normal fares for these dates run ₹{low}–{high}. This is
        ₹{low − price} below even the cheapest of those."
      - **broken:** "The usual price for these dates is ₹{usual}. This is also
        below the cheapest normal fare, ₹{low}."
      - **none:** "The usual price for these dates is ₹{usual}."
   2. `You save ₹{saving}`, with the detail "Against the usual ₹{usual}, for
      one adult, return." (range) or "For one adult, return." (others).
   3. Stops:
      - **non-stop:** "Non-stop both ways" / "We never show deals with more
        than one stop."
      - **one stop:** "One stop, in {via}" / "Allowed: we never show deals with
        more than one stop."
      - **one stop, `via` null:** the title is "One stop", the detail is the
        same, and the "About the stop" card is hidden.
   4. "A real, bookable fare" / "Priced on a public flight search from India,
      not a foreign reseller."
   5. "Still there an hour later" / "We check every fare twice before telling
      anyone about it."
8. **"Why we sent it" (`Timeline`, 4 steps):**
   - Day 1: Spotted / Compared / Re-checked, then Today: Sent to you;
   - the "Spotted" and "Sent to you" lines depend on data the snapshot lacks
     (gap G8).

Aside:
1. **Flight card:**
   - H2 "Flight";
   - rows Airline (`airline_name`), Stops (long form), Out and Back (weekday
     dates);
   - the primary button "Book this fare", which toggles the booking panel.
2. **Booking panel:**
   - title "Where to book";
   - link 1, "{Airline} (airline site)" with the price;
   - link 2, "Compare on Google Flights" / "opens a new tab";
   - the footer "Price gone when you get there? Tell us and we'll mark it."
3. **Booking links:** both use `digest.booking_url()`, which builds
   `https://www.google.com/travel/flights?q=Flights from {O} to {D} on {dep}
   through {ret}`. The canvas has a separate airline-site link, but nothing in
   the LLD provides one (gap G9).
4. **Save toggle:** `aria-pressed`, labelled "Save" or "Saved"; saved uses the
   `--save-bg` background with an orange border.
5. **Share button:** "Share", which changes to "Link copied" after copying
   `/d/:deal_id`.
6. **Note:** "You book directly with the airline or travel site. Fares like
   this usually last a few days."
7. **Second card,** depending on the deal:
   - **Grouped:** "Also this cheap on" / "Flexible? These dates are about the
     same price." with `DateChips`, each linking to that deal.
   - **One stop:** "About the stop", with the text for that stop and a
     trip-kind chip ("Long holiday · 19 nights"). The stop text is
     route-specific copy the snapshot doesn't carry (gap G8).
8. **Watch card (Plus):**
   - "Watch {Origin} → {Dest}" / "Get an email the next time this route drops,
     even if it's not a top deal.";
   - the input "Tell me when it's under", prefilled with a target price;
   - a "Watch this route" button.

   Once watching, the card shows `role="status"` "Watching. We'll message you
   under ₹x." with a "Stop" button. On phone it is a single button: "Tell me
   if it drops under ₹{target}".

States:
- **Price changed since we told you (States 4):** an inline notice on the deal
  page and in Saved. It shows the old price struck through and the new price.
  - **Up:** "Up ₹{d} since our alert. It's now inside the normal price range,
    so it's no longer a deal." with a "See similar deals" link.
  - **Down:** "Down another ₹{d} since our alert. Even better now."
  - It needs the price the user was told about (`alerts_sent.price` or
    `saved.price_at_save`). For the public, use `first_price` (gap G10).
- **Stale:** a `stale` status shows the freshness as "Last checked {n} days
  ago" in the warn colour, together with the feed's data-is-behind banner
  text.
- **Ended or unknown:** see P4.
- **Loading:** a skeleton of the price block and the aside.

Data:
- **Deal:** the full deal object (§3 fields) and `group[]` (the siblings with
  the same `group_id`). `GET /api/deals/:deal_id` returns the deal plus its
  group.
- **Signed in:** saved state and watch state.
- **Default watch target:** the canvas uses ₹28,000 for BOM-SGN, ₹40,000 for
  GOX-BKK and ₹60,000 for CCU-FRA, but no rule produces those values (gap
  G11).

### P4 Deal ended `/deals/:deal_id` (status `ended`) and gone (unknown id)

**Ended (Expired board):**
- **Hero card:**
  - the tag "Deal ended";
  - the H1 "{Origin} → {Dest} has gone back up";
  - the body "The {dates} fare of ~~₹{price}~~ is no longer available. Fares
    like this usually last only a few days.";
  - a primary button "Tell me when {Origin} → {Dest} drops again", which
    creates a watch (Plus; gap G12 covers Free users);
  - after watching, `role="status"` "Watching {route}." with an "Undo" button;
  - a secondary link "See live deals".
- **Note:** "Saw it gone before we did? Thanks: reports like yours make the
  next alert faster."
- **"Still live from {Origin city}":** up to 2 compact rows (destination,
  dates · airline, stops (+ "· +{k} dates"), price, −pct) linking to those
  deals.

**Gone (States 8),** used for an unknown or long-purged id:
- "This deal is long gone" / "Fares like it come back. Here's what's cheap from
  your cities today.";
- a button "See today's deals".

Data: the ended deal (`status`, `price`, the dates) and live deals with the
same origin. The API returns 200 with the status for ended deals (LLD §5).

### P5 Shared deal `/d/:deal_id`

Purpose: a public landing page for a friend's link. No login.

Sections:
1. **Header:** the logo and a "Sign in" link.
2. **Deal card:**
   - the eyebrow "A friend shared this fare with you";
   - the H1 "{Origin city} → {Dest city}";
   - the meta "{5–11 Apr 2027} · {n} nights · {airline}, {stops} · return, 1
     adult";
   - the chip "Still live · checked {age}";
   - the price, the struck usual price and "{pct}% under the usual";
   - the primary link "Check it and book", using `booking_url`;
   - a "Copy link" button, which changes to "Link copied";
   - the note "Fares like this usually last a few days. We'll mark this page
     if it ends."
3. **Aside, the join form:**
   - "Get fares like this from your city" / "We watch international fares from
     7 Indian cities and only message you when one is well below normal.
     Free.";
   - the "I fly from" select: the canvas lists 5 cities, and it should list all
     7 (gap G13);
   - Email, and the button "Get free alerts".

   After joining, it shows the copy in gap G14. On phone, the copy differs (see
   Appendix A).

States:
- **Ended:** the chip changes to the ended form and the page says so. The
  canvas promises "We'll mark this page if it ends" but has no ended board, so
  reuse P4's hero.
- **Unknown id:** States 8.

Data: one deal. The OG tags (`og:title`, `og:description`, `og:image` =
`/og/:deal_id.png`) are server-rendered in phase 5. In phase 2 they are static
per fixture page.

### P6 Link preview image `/og/:deal_id.png` (1200 × 630)

Contents:
- the logo;
- the pill "{pct}% off usual";
- "{Origin city} →", with "{Dest city}" large below it;
- "{5–11 Apr} · {non-stop | 1 stop} · return";
- the price and the struck usual price.

Colours are fixed hex, not themed: `#15171C` background, `#F6F5F1` text,
`#C9CBD0` secondary, `#F08A4B` brand, `#9A9DA4` faint and `#C2410C`.

### P7 Set up alerts `/start` (3 steps)

**Layout:**
- **Desktop:** a step list on the left. Each step shows a badge (number, or ✓
  when done), a title and a sub: "Your cities" / "{n} selected",
  "Destinations" / "{n} of 6 regions", "Alerts" / "Instant email" or "Weekly
  email". The current step's card is on the right. The header has the logo and
  "Already a member? Sign in".
- **Phone:** a header with a Back button and "Step {n} of 3", and 3 progress
  bars. The footer holds the summary and the primary button.

**Steps:**
1. **"Where do you fly from?"**
   - `ToggleChip` per city, 7 in total (Mumbai, Bengaluru, Goa, Kolkata,
     Hyderabad, Chennai, Kochi), each with `aria-pressed`.
   - Limit: 5 on desktop (summary "{n} of 5 cities"; at 5, "5 of 5 cities.
     Remove one to swap."). Continue is disabled with 0 cities.
   - The Free limit is 1 (gap G15).
2. **"Where would you go?"**
   - 6 region `OptionCard`s with checkboxes: gulf, sea, near, east, europe,
     aus, each with its example line. All are on by default on desktop; phone
     defaults to gulf, sea and europe (gap G15).
   - The "Trip length" select maps to `nights_min`/`nights_max`: Any 2–21,
     Short breaks 2–5, About a week 6–13 (proposed), Long holidays 14–21.
3. **"How should we tell you?"**
   - 2 radio `OptionCard`s: "Instant email" (Plus) and "Weekly email" (Free).
     They map to `instant_email` / `weekly_digest`.
   - The input "Email address".
   - On phone, the Trip length select is on step 3, not step 2.

**Footer:** the summary text, Back (steps 2–3), Continue (steps 1–2), and
"Start watching fares" on step 3, which goes to `/welcome`.

**Flow:** the canvas doesn't show where the sign-in code step fits. Proposed
order: step 3 → `POST /api/auth/start {email, consent: true}` → the code screen
(P8, step 2) → `PUT /api/me/prefs` → `/welcome`. Consent wording is missing
(gap G16).

**Data:** `prefs.origins` (city → airports, Goa = GOI + GOX), `regions`,
`nights_min`, `nights_max`, `instant_email`, `weekly_digest`.

### P8 Sign in `/signin`

1. **Email step:**
   - "Welcome back" / "We'll email you a 6-digit code. No password needed.";
   - the Email input and a "Send code" button;
   - "New here? Set up free alerts", linking to `/start`.
2. **Code step:**
   - "← Change email";
   - "Enter your code" / "Sent to {email}. Check spam if it's not there in a
     minute.";
   - a `CodeInput` of 6 boxes (`inputmode="numeric"`, `aria-label="Digit
     1…6"`);
   - the primary button "Sign in";
   - "Didn't get it? Resend in 0:24", a countdown button.

States:
- **Wrong code:** the canvas has no copy for it (gap G17).
- **Rate limited:** 3 per 15 min, per LLD §5 (gap G17).
- **Code expired:** after 10 min (gap G17).
- **Success:** goes to `/deals`.

The API always returns 200 on start, so the UI never says "no such account".

Data: `POST /api/auth/start`, `POST /api/auth/verify`.

### P9 First visit `/welcome`

Shown after setup when no live deal matches the user's cities.

Sections:
1. **Main panel:**
   - the H1 "You're all set";
   - the body "We're now watching fares from **{cities}** to 25 destinations.
     No deal from {cities} right now, and that's normal: real drops come in
     bursts, not every day.";
   - the button "Send me a sample alert", which changes to "Sent ✓" (gap G18);
   - the link "Browse deals from other cities", to `/deals`.

   After a sample is sent: `role="status"` "Sent a sample alert to {email}.
   That's what a real one looks like."
2. **"Get more out of faredrop" checklist,** 3 rows, each with a done state:
   - "Alerts by email" / {email} / "Edit";
   - "Add a second city" / "Goa or Bengaluru gives you more deals to choose
     from" / "Add city";
   - "Get alerts within the hour" / "Free members get a weekly email; Plus is
     instant" / "Try Plus".

If deals do match, go straight to `/deals`.

### P10 My alerts `/alerts`

**Sections:**
1. **Plan banner** (trial or Free):
   - "Plus trial · {n} days left" / "After that you move to Free: one city and a
     weekly email, no instant alerts.";
   - the button "Keep Plus", to `/plus`.

   On phone: "Then weekly email only".
2. **"I fly from":**
   - the counter "{n} of 5 on Plus";
   - city tags, each with a remove button (`aria-label="Remove {city}"`);
   - the select "+ Add a city", listing only cities not yet chosen and hidden
     at the limit.

   On phone, "+ Add" goes to the setup step.
3. **"Send deals to":** 6 region rows with a `Switch` each (`role="switch"`,
   `aria-label` = the region name).
4. **"How we tell you":**
   - two `Switch` rows: "Instant email" / "The hour a deal is confirmed, to
     {email}" and "Weekly digest" / "The best of the week, every Sunday
     morning";
   - the select "Only deals that save at least": ₹4,000, ₹7,500, ₹10,000 or
     ₹20,000 (phone lists 3), mapping to `min_saving`;
   - the select "Trip length", 4 options;
   - the select "Quiet hours": 11 pm – 7 am, None, or 10 pm – 8 am (phone lists
     2), mapping to `quiet_start`/`quiet_end`.
5. **Account:**
   - the email, shown read-only;
   - links: Sign out, Plus and billing (`/alerts/plus`), Privacy, Contact us,
     Delete my account (danger style).
6. **Sticky save bar:**
   - the status text: "All changes saved", "You have unsaved changes", or
     "Saved. New alerts use these settings.";
   - a "Save changes" button.

   Phone has no save bar; it saves on each change (gap G19).

**Plan gating** (LLD §8):
- **Free:** 1 city, instant email off and disabled, with an upgrade hint.
- **Trial and Plus:** 5 cities.
- Server errors are shown in plain words.

**Data:** `GET /api/me`, `PUT /api/me/prefs`.

### P11 Saved `/saved`

1. H1 "Saved", with the sub "We re-check saved fares and tell you if the price
   moves or the deal ends." (on phone: "We tell you if a saved fare changes or
   ends.").
2. **"Deals" list, as `SavedRow`s:**
   - each row shows the title "{Origin} → {Dest}", the meta "{dates} · {n}
     nights · {airline}, {stops}", the price and a note;
   - notes include "Same price as when you saved it", "Leaves in 19 days",
     "Saved just now" and "Deal ended";
   - each row has a CTA, "See deal" (or "Similar deals" when ended), and a
     remove button (`aria-label="Remove {title}"`).

   Ended rows use a `--chip` background and a struck-through, muted price.
   Empty: "Nothing saved. Tap the bookmark on any deal to keep it here." with
   "Browse deals".
3. **"Routes you're watching," as `WatchRow`s:**
   - each row shows the route, "Tell me under **₹x**" and a status;
   - statuses include "Now ₹25,218, under your target", "Watching since 2 Nov"
     and "Closest so far ₹30,065";
   - the section header links to "Manage in My alerts" (gap G20: My alerts has
     no watches section).

Data:
- `GET /api/me/saved` (deal + `price_at_save` + `saved_at`);
- `GET /api/me/watches` (`origin`, `destination`, `target`, `created_at`,
  plus the current `route_prices` low).

The note rules:
- **"Same price…":** `price == price_at_save`.
- **"Leaves in N days":** when the departure is within 30 days (proposed).
- **"Saved just now":** when `saved_at` is under 1 h old.
- **"Deal ended":** when `status = ended`.

### P12 Unsubscribe `/u/:token`

No sign-in; the page works from the signed token.

1. **Choosing:**
   - "Too many deal emails?" / "For {email}. Pick what suits you; you don't
     have to leave altogether.";
   - a radiogroup of 4 options:
     - "Pause for a month" (`paused_until` = +1 month),
     - "Weekly digest only" (`instant_email` = 0),
     - "Only big savings" (`min_saving` = 10000),
     - "Unsubscribe from all emails" (`instant_email` = 0, `weekly_digest` =
       0);
   - the button "Save preference", or "Unsubscribe" when the all option is
     picked.
2. **Done:** `role="status"`, with the title and body for the chosen option, a
   "Changed my mind" button (it reverts), and "See current deals".

The `POST /u/:token` one-click target unsubscribes from everything with no
page. For Free users, "Weekly digest only" changes nothing (gap G21).

### P13 Delete account `/alerts/delete`

1. **Asking:**
   - "Delete your account?" / "This can't be undone. We will permanently
     delete:" followed by 4 bullets; the 4th bullet, "Your Plus trial ({n} days
     left)", shows only for trial or Plus users;
   - the hint "Just want a break? …" with a "Pause instead" link;
   - the optional reason select, 6 options;
   - "Type DELETE to confirm", an input checked case-insensitively after
     trimming;
   - the danger button "Delete my account", which is `aria-disabled` until the
     input matches.
2. **Gone:** "Your account is deleted" / "We've removed your details and
   stopped all alerts. A confirmation is on its way to {email}. Safe travels."
   with "Go to faredrop home".

Data: `POST /api/me/delete {confirm: "DELETE"}`. The reason isn't in the LLD
(gap G22).

### P14 Contact `/contact`

1. H1 "Get in touch", lede.
2. **FAQ accordion:** 3 items, one open at a time (`aria-expanded`, +/−). The
   first is open by default.
3. **Form "Send us a message":**
   - the select "About", 4 options;
   - "Your email", prefilled when signed in;
   - the textarea "Message", with placeholder text;
   - the button "Send message";
   - "Or email [SUPPORT EMAIL]. We usually reply within [REPLY TIME]."

   After sending: `role="status"` "Message sent" / "We'll reply to {email}."
   with "Send another".

There's no endpoint for the form in the LLD (gap G23).

### P15 Privacy `/privacy`

1. **In-page nav** "On this page", 5 anchors: collect, use, share, keep,
   rights.
2. **Draft note** (`role="note"`): "Draft for design review. …". It stays until
   the owner's review (plan, phase 9, step 5).
3. H1 "Privacy, in plain words", lede with "Last updated [DATE]".
4. 5 sections, one per anchor.
5. **Actions:** the button "Download my data" (it changes to "We'll email you a
   copy of your data"), the link "Edit my details" (`/alerts`) and the link
   "Delete my account".

The export button triggers `GET /api/me/export`. The LLD returns JSON
directly while the canvas promises an email (gap G24).

### P16 Upgrade to Plus `/plus`

**Desktop:**
1. **Header:** the logo and "Not now" (to `/alerts`).
2. **Left column:**
   - the eyebrow "faredrop Plus";
   - the H1 "Hear about deals while they still exist.";
   - the lede;
   - 5 perks;
   - the proof line "**One deal pays for it.** The last deal from {city} saved
     ₹{saving} on a return to {dest}.", computed from the newest live deal from
     the user's cities.
3. **Right column:**
   - a billing radiogroup: Yearly `[PRICE]` "per year · best value", and
     Monthly `[PRICE]` "per month";
   - "Pay with" UPI or Card;
   - the field "UPI ID" or "Card number" (gap G25);
   - the button "Start Plus · [PRICE] / year";
   - the note "Cancel any time…".
4. **Done state** (`role="status"`): "You're on Plus" / "Instant email alerts
   are on for {cities}." with "Back to deals".

**Phone:** a Close button and 4 perks; the button is "Pay with UPI ·
[PRICE]/yr".

**Data:** the billing endpoints (phase 4 of the LLD).

### P17 Plus and billing `/alerts/plus`

1. "← My alerts", then the H1 "Plus and billing".
2. **Cancelled banner:** "**Plus ends on [RENEWAL DATE].** You keep instant
   alerts until then, then move to Free. You won't be charged again." with a
   "Keep Plus after all" button (resume).
3. **Plan card:**
   - "Plus · yearly", with a badge ("Active" or "Ending");
   - the renew text: "Renews [RENEWAL DATE] via UPI autopay." or "Ends [RENEWAL
     DATE]. No further charges.";
   - `[PRICE]`, "per year, incl. GST".
4. **Payment method:**
   - "UPI", the UPI id and "Autopay mandate active";
   - a "Change" button opens an inline editor: "New UPI ID", with the buttons
     "Approve in UPI app" and "Cancel".
5. **Receipts:** a table (`role="table"`) with the columns Date, What, Amount
   and GST invoice; each row links "Download PDF".
6. **Cancelling:**
   - the link button "Cancel Plus" opens the confirm section "Cancel Plus?";
   - the confirm section has the text, an optional reason select (5 options),
     and the buttons "Keep Plus" and "Cancel at end of period".

**Data:** `subscriptions`, `payments`, and `GET /api/me/billing`, `/cancel`
and `/resume`.

### P18 Ops: pipeline health `/ops/health` (owner only, Cloudflare Access)

**Header:**
- "faredrop" with an "ops" tag;
- nav "Pipeline" and "Deal feedback";
- "Data as of {date} · team only".

**Content:**
1. H1 "Pipeline health".
2. **Five `StatTile`s,** each with an ok or warn icon:
   - "Travelpayouts history" 440/440,
   - "Google budget" 60 / day,
   - "Routes watched" 200,
   - "Answered, {range}" with a percentage range,
   - "Deals rated since 12 Oct".
3. **Bar chart** "Google lookups answered, by day":
   - one focusable bar per day;
   - a 75 % line;
   - the rule text "Rule: two full days under 75% → lower the daily budget";
   - a live text "{day}: {pct}% answered[, under the 75% line]", or "Hover or
     tab to a bar for details."
4. **"Recent changes"** log, with when and what.
5. **"Discovery by city"** table: City, Lookups (as a bar), Candidates, Deals.
6. **"Routes on back-off (priced nothing 3 times)"** chips, with "Probed again
   after 14 days, doubling up to 60."

**Data:** the snapshot's `pipeline` block is too thin for this page (gap G26).
The canvas numbers come from STATUS.md as of 14 Nov and are sample data.

### P19 Ops: deal feedback `/ops/feedback`

1. H1 "Is each deal actually good?".
2. **4 summary tiles:**
   - "Rated {n} of {total}";
   - "Not wrong (precision)", with "95% lower bound ~{x}% (rule of three)";
   - "Would book (good)";
   - "Biggest single route".
3. **Filter chips,** with counts: All, Unrated, Good, Not for me, Wrong.
4. **Table:** Route, Trip, Price, Emailed, Verdict. The verdict cell is 3
   toggle chips.
5. **Footnote** about the excluded pre-fix deal.

**Data:** `GET /internal/verdicts`, which has counts only. The owner's own
verdict buttons need a write path (gap G27). The verdict names differ between
the canvas and the LLD (gap G28).

### E1 Deal alert email

The from line is "faredrop · deals@faredrop" (domain undecided). The subject
is "{Origin} → {Dest}, ₹{price} return ({pct}% off)".

**Content:**
1. **Dark header:**
   - the eyebrow "New deal from {Origin}";
   - "{Dest} for ₹{price} return";
   - "Usually ₹{usual}. You save ₹{saving}."
2. **Facts:** three tiles, "When" / "Trip" / "Flight".
3. **Price bar**, labelled "₹x this fare" and "₹y usual".
4. **Button** "See the deal and book", linking to the deal page.
5. **Group line:** "Also about this price: **{dates}** and **{dates}**. Fares
   like this usually last a few days."
6. **Feedback:** "Was this useful?" with 3 buttons:
   - "Great deal" (`good`);
   - "Not my kind of trip" (`not_for_me`);
   - "Price was different" (`price_different`).

   Each is a signed `/f/:token?v=` link, and the notes that follow are
   messages on the thank-you page.
7. **"Still live from your cities":** up to 2 rows.
8. **Footer:** "You're getting this because {Origin} is one of your cities.",
   with the links "Change alerts" and "Unsubscribe".

The body comes from the exporter's `card_html` plus the Worker's wrapper (LLD
§2.6). The colours are the email palette (section 3.3).

### E2 Weekly digest email

1. The subject is "Your week: {n} deals from {cities}, best saves ₹{max}".
2. The header is "Sunday digest · {date}" / "This week's best fares from your
   cities" / "Biggest saving first. Prices were right when we last checked;
   they may have moved since."
3. **Up to 5 deal rows:** route, meta, status ("Still live" in green or "Ended
   {day}" in grey), the price, and "Save ₹x" (or "Below the usual" when there's
   no usual).
4. The button "See all live deals".
5. **"Routes you're watching":** each route with its status.
6. **Plus nudge, for Free users only:** "Plus members heard about {Dest} a week
   ago" / "The {route} fare went to Plus members by instant email on {date}.
   Weekly emails are free; instant alerts are Plus." with "Try Plus".
7. **Footer:** "You get this every Sunday because you chose the weekly
   digest.", with "Change alerts" and "Unsubscribe".

The digest includes ended deals ("Ended Thursday"), but LLD §7.6 says digest
deals are still `live` (gap G29).

### E3 Saved fare changed email

1. The subject is "Price drop: {route} you saved is now ₹{price}".
2. The heading is "A fare you saved got cheaper". The other two triggers need
   their own headings (gap G30).
3. **Route card:** "{route} · {dates}", "{airline}, {stops} · {n} nights", and
   3 figures: "When you saved it", "Now" and "Usually".
4. The text "Down another ₹{d}. That's ₹{usual − price} under the usual price
   for these dates." and the button "See it and book".
5. **"Also in your saved list":** other saved rows ("Ended · similar deals",
   "Unchanged at ₹x").
6. **Footer:** "We email when a saved fare drops by ₹1,000 or more, rises out
   of deal territory, or ends.", with "Change alerts" and "Unsubscribe".

### E4 Trial ending email

1. The from line is "hello@faredrop" and the subject is "Your Plus trial ends
   in 3 days".
2. The tag is "Trial ends {date}" and the heading is "Keep hearing about deals
   the hour they appear?"
3. **Two-column comparison:** "With Plus" (instant, {n} cities, watched
   routes) versus "On Free" (Sunday email, 1 city you pick, no watched
   routes).
4. The button "Keep Plus · [PRICE]/year".
5. The note "Do nothing and you move to Free on {date}. We won't charge you; we
   never took a payment method for the trial."
6. **Footer:** "My alerts" and "Unsubscribe".

### E5 Payment failed email

1. The from line is "billing@faredrop" and the subject is "Action needed: we
   couldn't renew your Plus".
2. The tag is "Payment didn't go through" and the heading is "Your UPI autopay
   for Plus was declined".
3. **Facts:** Plan, Amount `[PRICE]`, and "Tried: Today, via {upi}".
4. The text "Your instant alerts keep running for **7 more days**. We'll try
   again in 3 days. After that you move to Free; nothing is deleted."
5. The button "Update payment method", linking to `/alerts/plus`.
6. The hint "Common reasons: …" and "Need help?" (to `/contact`).

## 3. Design tokens

### 3.1 Colour variables

All 35 themed boards carry one identical `.fd{…}` light block and one identical
`.fd[data-theme="dark"]{…}` block. A script in the phase-0 session checked
that they are byte-identical. The table below was generated from those blocks,
so its values are the canvas's own. In `web/`:
- the light values go on `:root`;
- the dark values go under
  `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) }` and
  again under `:root[data-theme="dark"]`, per the phase 1 prompt.

| Token | Light | Dark | Where the boards use it (inferred) |
|---|---|---|---|
| `--bg` | `#F6F5F1` | `#121316` | Page background |
| `--surface` | `#FFFFFF` | `#1C1E23` | Cards, header, inputs |
| `--ink` | `#15171C` | `#ECEBE6` | Text; primary button fill |
| `--muted` | `#5B606B` | `#A3A7B0` | Secondary text, labels |
| `--ink2` | `#3F444D` | `#C9CBD0` | Body text on surface, nav links |
| `--line` | `#E3E1DA` | `#2E3138` | Card borders, dividers |
| `--line2` | `#D5D2C9` | `#3A3D45` | Input and outline-button borders |
| `--line3` | `#EFEDE7` | `#26282E` | Inner dividers (footers of cards) |
| `--chip` | `#F1F0EC` | `#26282E` | Ended rows, neutral chips |
| `--track` | `#ECEAE4` | `#2A2D33` | Price-bar track |
| `--surface2` | `#F7F6F2` | `#18191D` | Subtle panels |
| `--chip2` | `#F3F1EA` | `#26282E` | Fact tiles |
| `--accent` | `#0B6B66` | `#4FB3AC` | Links, Plus, selected states, focus ring |
| `--accent-hover` | `#084F4B` | `#7FD0C9` | Link hover |
| `--accent-bg` | `#EEF5F4` | `#16302E` | Selected chip / plan background, tags |
| `--range` | `#CFE3E1` | `#2B5552` | Normal-range band on the price bar |
| `--save-bg` | `#FBEDE4` | `#3A2215` | Saving pill background, saved button |
| `--save` | `#9A3A09` | `#F5A877` | Saving pill text |
| `--eyebrow` | `#B4430B` | `#F5A877` | Eyebrow text (orange) |
| `--save-strong` | `#7A2E07` | `#F5A877` | Strong saving text |
| `--good-bg` | `#E3F2EC` | `#16301F` | Live / success background |
| `--good` | `#13603F` | `#7BD3A2` | Live / success text |
| `--good-dot` | `#1F8A5B` | `#7BD3A2` | Fresh dot, check marks |
| `--warn-bg` | `#FFF4D6` | `#33280F` | Warning banner background |
| `--warn` | `#6B4A00` | `#F2C66B` | Warning text |
| `--warn-icon` | `#8A6100` | `#F2C66B` | Warning icon |
| `--bad-bg` | `#FBE9E7` | `#3A1A16` | Error / danger background |
| `--bad` | `#A12A1C` | `#F28B7D` | Error / danger text |
| `--bad-line` | `#C2412D` | `#E0705F` | Danger borders |
| `--faint` | `#9A9DA4` | `#7D818A` | Unchecked box / radio borders, decorative chevrons |
| `--switch-off` | `#C9C6BD` | `#4A4D55` | Switch track when off |
| `--band-muted` | `#C9CBD0` | `#3F444D` | Secondary text on the dark band |
| `--band-input` | `#22252B` | `#D9D8D2` | Input on the dark band |
| `--band-active` | `#2A2D34` | `#D2D1CB` | Active item on the dark band |
| `--muted2` | `#6B6F77` | `#8A8E96` | Tertiary text |
| `--line4` | `#3A3D45` | `#4A4D55` | Borders on dark surfaces |

Colours used outside the variables, as fixed hex:
- **`#F08A4B` brand orange:** the logo's arrow, the saved bookmark fill, the
  saved button border and the email eyebrow. It is the same in both themes, per
  the DarkMode board. Proposed token: `--brand`.
- **`#C98A0B`:** the feed's freshness dot when a deal is older than a day.
  Proposed token: `--fresh-old`. It has no dark value on the canvas (gap G4).
- **`#E0A526`:** the ops page warn tile icon. Proposed: reuse `--warn-icon`.
- **`#C2410C`:** a ring on the share preview and the phone deal page.
- **Shadows:** `0 1px 2px rgba(21,23,28,.04), 0 12px 32px rgba(21,23,28,.08)`
  (cards), `0 18px 40px rgba(21,23,28,.12)` (hero card), `0 8px 24px
  rgba(21,23,28,.08)` (sticky save bar), `0 1px 2px rgba(0,0,0,.2)` (switch
  knob).

### 3.2 Contrast pairs

The ratios below are WCAG 2.x contrast, computed from the tables above. The
DarkMode board states the dark ratios; the light ones are computed here.

| Text on background | Light | Dark |
|---|---|---|
| `ink` on `bg` | 16.4 | 15.6 |
| `ink` on `surface` | 17.9 | 14.0 |
| `ink2` on `surface` | 9.8 | 10.3 |
| `muted` on `surface` | 6.3 | 6.9 |
| `muted` on `bg` | 5.8 | 7.7 |
| `muted2` on `surface` | 5.0 | 5.1 |
| `accent` on `surface` (links) | 6.3 | 6.7 |
| `accent` on `bg` | 5.8 | 7.4 |
| `surface` on `accent` (accent button) | 6.3 | 6.7 |
| `surface` on `ink` (primary button) | 17.9 | 14.0 |
| `accent` on `accent-bg` (selected chip, tags) | 5.7 | 5.6 |
| `accent-hover` on `surface` | 9.4 | 9.3 |
| `save` on `save-bg` (saving pill) | 6.1 | 7.6 |
| `eyebrow` on `bg` | 5.1 | 9.5 |
| `good` on `good-bg` | 6.6 | 7.9 |
| `good` on `surface` | 7.6 | 9.3 |
| `warn` on `warn-bg` | 7.4 | 9.0 |
| `bad` on `bad-bg` | 6.3 | 6.5 |
| `band-muted` on `ink` (dark band) | 11.0 | 8.2 |
| **`faint` on `surface`** | **2.7** | 4.3 |

Every text pair is at least 4.5:1 except `--faint`. The boards use it for:
- unchecked checkbox and radio borders, which are non-text UI and need 3:1
  under WCAG 1.4.11;
- the arrow between airport codes on the deal page;
- the "›" chevrons on phone My alerts.

In light mode, 2.7:1 fails 3:1 for the borders (gap G31).

### 3.3 Email palette

Emails don't use variables: mail clients need inline hex, and emails stay
light-only. They use the light values above.

| Role | Hex |
|---|---|
| Canvas behind the email | `#ECEAE4` (`--track`) |
| Card | `#FFFFFF` |
| Header band | `#15171C`, title `#F6F5F1`, sub `#C9CBD0`, eyebrow `#F08A4B` |
| Text | `#15171C`, secondary `#3F444D`, muted `#5B606B` |
| Tiles | `#F6F5F1` |
| Link and button | `#0B6B66`, hover `#084F4B`, button text `#FFFFFF` |
| Saving | `#9A3A09` |
| Live status | `#13603F` on `#E3F2EC` |
| Account-email tag | `#B4430B`; error panel `#A12A1C` on `#FBE9E7`; info `#EEF5F4` |
| Dividers | `#EFEDE7`, buttons `#D5D2C9` |

### 3.4 Type

- **Fonts:** Space Grotesk (500, 600, 700) for headings, prices, logo and code
  boxes; Inter (400, 500, 600, 700) for everything else; fallback
  `system-ui, sans-serif`. Both are Google Fonts and free under the OFL.
  Phase 1 should self-host them rather than load them from Google, so Pages
  serves everything (gap G32).
- **Base size:** body 16 px on Landing, 15 px on app pages.
- **Sizes in use, in px (count across boards):**
  - 12 (111) small notes, 13 (140) labels and meta, 14 (197) secondary,
    15 (104) app body, 16 (52) body and buttons;
  - 18 (31), 20 (44) H3 and card titles, 22 (20) city names and saved prices;
  - 24 (16), 26 (16), 28 (10) H2 (phone), 30 (18) hero city;
  - 32 (6) sign-in H1, 36 (5) step H1, 40 (15) section H2, 44 (4) hero price;
  - 48 (3), 52 (4) deal price, 64 (1) landing H1, 88 and 96 (1 each) deal H1
    codes.
- **Proposed scale:** 12 / 13 / 14 / 15 / 16 / 18 / 20 / 22 / 26 / 30 / 36 /
  40 / 52 / 64, plus 88 for display.
- **Headings:** Space Grotesk 600–700, letter-spacing −0.02em, or −0.035em at
  64 px; line-height 1 to 1.05 on large headings.
- **Body:** line-height 1.5–1.55.
- **Eyebrows:** 13–14 px, weight 600, uppercase, letter-spacing 0.06em,
  `--eyebrow`.
- **Weights:** mostly 600 (270 uses) and 700 (72); 500 for pills and nav.

### 3.5 Spacing, radii, sizes, focus

- **Gaps in use:** 2 4 6 8 10 12 14 16 18 20 24 28 32 40 48 56 px, mostly
  10, 12, 6 and 8. Proposed scale: `--s1` 4, `--s2` 8, `--s3` 12, `--s4` 16,
  `--s5` 20, `--s6` 24, `--s7` 32, `--s8` 40, `--s9` 48, `--s10` 72 (section
  padding). Keep 6, 10 and 14 as `--s1h` 6, `--s2h` 10 and `--s3h` 14, because
  the boards use them a lot.
- **Radii:**
  - 999 px for pills, chips and switches;
  - 18 px for large cards and form panels, 16 px for pricing cards, 14 px for
    deal cards and rows;
  - 12 px for option cards, 10 px for inputs, buttons and tiles, 8 px for small
    tiles;
  - 6 px for checkboxes and the focus ring, 5 px for the price-bar track.
- **Control heights:** 52 (primary inputs and buttons on sign-in and landing),
  48 (forms), 44 (chips, small buttons), 40 (filter chips, text buttons), 36
  (compact). The 44 px minimum also serves as the touch target.
- **Widths:** content 1200 (1240 feed), 1080 deal, 880 or 820 account pages,
  680 text pages, 440 sign-in card. Phone frame 390 px.
- **Focus:** `:focus-visible { outline: 3px solid var(--accent);
  outline-offset: 2px; border-radius: 6px }` on every themed board. Every
  `web/` page keeps it.
- **Breakpoint:** one layout switch at 640 px (phone ↔ desktop), from the
  390 px and 1440 px boards. Proposed: the hero and two-column layouts wrap
  with flex-basis as the boards do; the tab bar replaces header nav ≤ 640 px.

## 4. Components

Islands (Preact) are interactive; everything else is plain Astro. "Used by"
lists pages from section 2.

| # | Component | Props | Variants / states | Used by |
|---|---|---|---|---|
| C1 | `Logo` | `size` (28, 30, 44) | — | all |
| C2 | `SiteHeader` | `variant`, `current`, `savedCount`, `user?` | `public` (anchors + Sign in), `app` (Deals / Saved [n] / My alerts, alerts pill, avatar), `minimal` (logo + one right link), `ops` (ops tag + internal nav + data-as-of) | all web pages |
| C3 | `PhoneTabBar` | `current` | Deals / Saved / My alerts, `aria-current="page"` | P2, P11, P10 (phone) |
| C4 | `Footer` | — | — | P1, P2 |
| C5 | `Button` | `kind`, `size`, `href?`, `disabled` | `primary` (ink), `accent`, `outline`, `secondary` (surface + line2), `text` (link-styled), `danger`; sizes 52 / 48 / 44 / 40; disabled uses `--line2` / `--muted` + `aria-disabled` | all |
| C6 | `ToggleChip` (island) | `label`, `pressed`, `onToggle` | single-select group, multi-select with max, filter-with-count, vote (email/ops) | P2, P7, P19, E1 |
| C7 | `Select` | `label`, `options`, `value` | label above, 48 or 52 px | P1, P2, P7, P10, P13, P14, P17 |
| C8 | `TextField` | `label`, `type`, `placeholder`, `value` | email, text, textarea | P1, P5, P7, P8, P13, P14, P16, P17 |
| C9 | `CodeInput` (island) | `length=6`, `onComplete` | per-digit boxes, paste fills all, `aria-label="Digit n"` | P8 |
| C10 | `Switch` (island) | `label`, `checked` | `role="switch"`, on `--accent` / off `--switch-off`, disabled for plan-gated | P10 |
| C11 | `OptionCard` (island) | `label`, `sub`, `selected`, `control` | `checkbox` (regions), `radio` (channels, unsubscribe, billing plan) | P7, P12, P16 |
| C12 | `Stepper` | `steps`, `current` | desktop list (badge + title + sub), phone bars + "Step n of 3" | P7 |
| C13 | `DealCard` | `deal`, `group`, `saved`, `variant` | `feed` (desktop card), `compact` (phone row), `mini` (landing recent), `teaser` (landing hero), `row` (ended page "still live") | P1, P2, P4 |
| C14 | `PriceBlock` | `price`, `usual`, `estimate` | large (deal page), card, inline; "~"/"about" when estimate | P2, P3, P5, P6 |
| C15 | `SavingPill` | `saving`, `pct`, `format` | "Save ₹x (y%)", "{y}% off usual", "−{y}%", "You save ₹x" | P1, P2, P3, P5 |
| C16 | `Freshness` | `checkedAt`, `status` | fresh dot (good) / older (amber), stale text in warn | P2, P3, P5 |
| C17 | `DateChips` | `dates[]`, `links` | title "Also this cheap on…", chips link to sibling deals | P2, P3 |
| C18 | `PriceRangeBar` | `price`, `usual`, `rangeLow`, `rangeHigh` | `range`, `broken` (cap + break glyph), `none` (two comparison bars) | P3 |
| C19 | `CheckList` | `items[{title, detail}]` | check icon in `--good-dot` | P3 |
| C20 | `Timeline` | `steps[{when, title, detail}]` | — | P3 |
| C21 | `BookingPanel` (island) | `deal` | inline expand (desktop), bottom sheet `role="dialog"` with focus trap (phone) | P3 |
| C22 | `WatchRoute` (island) | `origin`, `destination`, `target` | input + button / watching status + Stop / single phone button / locked for Free | P3, P4 |
| C23 | `Banner` | `tone`, `title`, `body`, `action?` | `error` (`role="alert"`), `warn` stale (`role="status"`), `offline` slim bar, `info` (trial, cancelled), `note` (privacy draft) | P2, P3, P10, P15, P17 |
| C24 | `Toast` (island) | `message`, `action` | Undo toast, "Link copied", `role="status"` | P2, P3, P5 |
| C25 | `EmptyState` | `title`, `body`, `action` | no match, nothing saved, long gone, couldn't load (full page) | P2, P4, P11 |
| C26 | `Skeleton` | `shape` | deal card, deal page blocks | P1, P2, P3 |
| C27 | `Accordion` (island) | `items[{q, a}]` | one open at a time, `aria-expanded`, +/− | P14 |
| C28 | `SavedRow` / `WatchRow` | `item` | live / ended (muted, struck price) / price-changed notice | P11 |
| C29 | `StatTile`, `BarChart`, `DataTable` | — | ok / warn icon; focusable bars with live text; `role="table"` grids | P18, P19, P17 (receipts) |
| C30 | `ThemeSwitch` (island) | — | light / dark / system, stored in `localStorage` in try/catch | header (not on canvas; gap G33) |
| C31 | `EmailShell` | `kind` | table-based, inline hex, light only; header band, card, footer links | E1–E5 |

## 5. Fixtures

`docs/fixtures/snapshot.sample.json` is shaped exactly like LLD §3. It holds
only the deals the canvas shows, plus the facts STATUS.md records about them.
No value is estimated:
- a field the canvas and STATUS.md don't give is `null` where the LLD's D1
  column allows null;
- otherwise it's listed as a gap.

`docs/fixtures/README.md` gives each value's source.
`tools/check_fixture.py` validates it against LLD §3 and §4.

| Deal | Status | Note |
|---|---|---|
| BOM-SGN 2027-04-05/11 | live | range 30,500–44,000; group of 3 (canvas chips 31 Mar–6 Apr, 1–8 Apr: dates only, see G34) |
| GOX-BKK 2026-12-03/22 | live | the broken-scale case, range 36,500–3,05,000 (STATUS 2026-11-14) |
| CCU-FRA 2027-01-24/28 | live | no range; user rated it wrong on 15 Nov because a cheaper fare exists (STATUS) |
| BOM-BAH 2027-04-14/18 | live | via KWI (STATUS); range unknown → null |
| BLR-SGN 2027-02-10/26 | live | non-stop; range unknown → null |
| GOI-CMB 2027-01-16/19 | live | usual ~39,000 is an estimate (States 5); group dates on the canvas; `via` null (G35) |
| GOI-DXB 2026-11-01/15 | ended | departure passed; usual not shown on the canvas |

`generated_at` is pinned to `2026-11-15T10:19:40Z`, the LLD's example.
`checked_at` values are back-computed from the canvas's "Checked {age}" labels
relative to it. They are fixture timestamps, not real check times.

**Fixture clock:** in fixture mode, the data adapter and every test take "now"
from `snapshot.generated_at`, not the wall clock. Otherwise every render after
18 Nov 2026 would show "Checked 4+ days ago" and a permanent data-is-behind
banner, and the Playwright results would change with the date. The real adapter
(phase 4+) uses the wall clock.

## 6. Placeholders

These stay verbatim in the UI until the owner fills them:

| Placeholder | Where | Decided by |
|---|---|---|
| `[PRICE]` | Landing pricing, Upgrade (yearly, monthly, button), Manage Plus, E4, E5, receipts | owner (Plus price) |
| `[RENEWAL DATE]` | Manage Plus | data (subscription `period_end`) |
| `[DATE]` | Privacy "Last updated", receipts | owner / data |
| `[SUPPORT EMAIL]`, `[REPLY TIME]` | Contact | owner |
| `[EMAIL PROVIDER]`, `[PAYMENT PROVIDER]` | Privacy | owner (Resend and Razorpay assumed) |
| `[N]` | Privacy ("removed within [N] days") | owner (LLD §11 retention) |
| `[GRIEVANCE CONTACT]` | Privacy | owner (DPDP) |
| `deals@` / `hello@` / `billing@faredrop` | email from lines | owner (domain) |

Sample values that look like copy but are data: "Priya", `priya@example.com`,
`priya@bank`, "9 days left", "0:24", "09:40", "14 Dec", "15 Nov", "23 Nov",
"8 Nov", every price and date, and ops numbers.

## 7. Gaps and contradictions

Each gap has a proposed resolution, and none has been decided. The tag on
each gap says who decides it:
- **owner:** a product call.
- **spec:** this file can settle it if the owner doesn't object.
- **lld:** `docs/lld.md` should change.
- **data:** phase 3's real snapshot will close it.

Checked first:
- None of the 13/14 Nov cities or destinations (DEL, JAI, LKO, ATQ, VNS, PNQ,
  AMD, TRV, BJS, …) appear on any board.
- No board shows calendar-scan, probe or simulation output. The ops page's
  "Probed again after 14 days" line describes the engine's back-off, not an
  experiment, and only the owner sees it.

### Canvas versus the plan

- **G37 · spec:** the canvas has **41 boards, not 48**. Its `canvas.json`
  lists 41, and all are mapped in section 1. "48" probably counted the States
  sheet's 8 sections separately. Resolution: use 41 in the tracker and the plan.
- **G1 · spec:** the routes `/deals`, `/start`, `/signin`, `/welcome`,
  `/alerts`, `/alerts/plus`, `/alerts/delete`, `/saved`, `/plus`, `/contact`,
  `/privacy` and `/ops/*` are proposals (the canvas uses file names). Only
  `/d/`, `/og/`, `/u/` and `/f/` come from the LLD. Resolution: adopt them
  unless the owner objects.
- **G2 · spec:** some screens exist in the LLD but have **no board**:
  - the sign-in code email,
  - the account-deleted confirmation email,
  - the `/f/:token` feedback thank-you page,
  - the watched-route email,
  - Plus receipts (an email).

  Resolution: build them from existing components and the E1 shell, with copy
  in the voice of the nearby boards. Mark the copy "not from canvas" in
  Appendix A, and the owner reviews it in phase 6/8/9.

### Data the snapshot or the LLD doesn't carry

- **G3 · data:** the snapshot has codes, not city names. The canvas names 7
  destination cities; the other 18 need names. Resolution: the exporter adds
  `origin_city` and `destination_city` from the engine's place names (refdata),
  or `web/` ships a static map of the 8 + 25 codes. A static map in `web/` is
  proposed, because the set is fixed by the allowlist.
  `routes/places.json` is the owner's work in progress and is left alone.
- **G4 · spec:** the freshness dot's colour rule isn't on the canvas. The
  canvas uses `#C98A0B` amber for "Checked yesterday" and green otherwise.
  Resolution: green within 24 h, amber after. Proposed dark value: `--warn-icon`
  `#F2C66B`.
- **G5 · lld:** the feed's "Good morning, Priya" needs a first name, and
  `users` has none. Resolution: greet with no name ("Good morning") unless the
  owner wants a name field. The time of day follows IST. The public feed drops
  the "From {cities}" sub.
- **G6 · spec:** the rules for choosing between the range and broken price-bar
  variants, and for the broken scale's cap, aren't on the canvas. Resolution,
  matched to GOX-BKK's 3,05,000 against 53,679:
  - use `broken` when `range_high > 2.5 × usual`;
  - set the cap to `ceil(1.1 × usual / 10,000) × 10,000`, which gives ₹60,000
    for GOX-BKK.
- **G7 · lld:** the canvas shows GOI-CMB's usual as "~₹39,000", an estimate,
  but the snapshot has no estimate flag. Resolution: add
  `usual_is_estimate: bool` to the §3 deal. The engine knows when Google gave
  only a typical price, not a range. Until then, show "about" when
  `range_low` is null and the source says so.
- **G8 · data:** some deal-page text needs data the snapshot doesn't carry:
  - "Spotted" detail: "A Mumbai to Vietnam fare looked low" names a country,
    and "A random check … came back low" means exploration;
  - "Sent to you because {city} is one of your cities";
  - "About the stop": the connection text, and whether the booking mixes
    partner airlines.

  Resolution:
  - add `found_by` (`discovery` | `exploration`) to the §3 deal, from
    `gf_quote.reason`;
  - derive "Sent to you" from the signed-in user's prefs, and hide it for
    public visitors;
  - write "About the stop" from `via` alone ("You change planes in {via city}
    both ways"), and drop the partner-airline sentence unless the data shows
    it.
- **G9 · owner:** the booking panel's "{Airline} (airline site)" link has no
  data source. Resolution: both links use `digest.booking_url` (Google
  Flights, exact dates), and the first is relabelled "Book on Google Flights".
  An airline deep link stays out until there's a source for one.
  **Decided (owner, 2026-11-19):** one link, "**See this fare on Google Flights**",
  with "Your dates are filled in · opens a new tab" under it (`booking_url`).
  Keep the "Book this fare" button and the "Price gone when you get there?
  Tell us" line. No airline-site row.

- **G10 · spec:** "Price changed since we told you" needs the price the user
  was told. Resolution:
  - signed in: `alerts_sent.price`, or `saved.price_at_save` in Saved;
  - public visitors: the notice is hidden, since `first_price` isn't "since our
    alert".
- **G11 · spec:** the default watch target (₹28,000, ₹40,000, ₹60,000 on the
  canvas) has no rule. Resolution: prefill `range_low` rounded down to ₹1,000;
  without a range, prefill `usual × 0.8` rounded down to ₹1,000. The field
  stays editable.
- **G34 · data:** the group chips (2 sibling dates for BOM-SGN, 5 for GOI-CMB)
  have no prices on the canvas, and LLD groups are full deals with a non-null
  price. Resolution: the fixture leaves siblings out. Phase 2 tests the group
  chips with siblings that phase 3's first real snapshot supplies, or with real
  sibling rows the owner approves copying from a decrypted scratch copy of the
  DB. Prices are never made up.
- **G35 · data:** GOI-DXB's airline and stops aren't recorded on the canvas or
  in STATUS or history, and `stops` is NOT NULL in D1. GOI-CMB 16–19 Jan's stop
  airport is also unknown: STATUS has January GOI→CMB trips both via HYD and
  via MAA, so its `via` is null. Resolution: the real
  snapshot fills them in phase 3. `tools/check_fixture.py` lists this as a
  known gap.
- **G36 · lld:** LLD §7.2 says the near-duplicate constants "travel in the
  snapshot's `pipeline` block", and phase 7 names `pipeline.dup_rule`, but §3's
  example has no such key. Resolution: add `"dup_rule": {"days": 14,
  "depart_days": 7, "cheaper": 0.05}` to §3's `pipeline` and to the fixture in
  phase 3.
- **G26 · lld:** the ops health page shows more than the snapshot's `pipeline`
  block carries:
  - Travelpayouts cells,
  - routes watched,
  - answered % per day,
  - discovery by city,
  - routes on back-off,
  - a change log.

  Resolution: the exporter adds an `ops` block (counts only, no user data) to
  the snapshot. The change log stays a hand-edited list. The values on the
  canvas are sample data from STATUS.md as of 14 Nov.

### Product rules against the canvas

- **G15 · owner:** setup lets anyone pick up to 5 cities and pre-selects
  "Instant email (Plus)", but Free is 1 city plus the weekly digest. The phone
  and desktop defaults also differ: 2 cities versus 1, and 3 regions versus 6.
  Resolution: new users start Free. Step 1 allows 1 city with the hint "Plus
  covers up to five"; a second tap offers a trial; step 3 defaults to weekly.
  This depends on the open owner decision on whether Free gets any instant
  alerts and whether sign-up starts a trial. Defaults: all 6 regions, any trip
  length.
- **G38 · owner:** Upgrade lists "Saved-deal tracking" and "Filters that
  stick" as Plus perks, and the phone version says "Know when a saved fare
  changes". LLD §8 gives saved deals to everyone and puts all prefs in
  `prefs` for everyone. Resolution: either gate saved-change emails and
  filters to Plus in LLD §8, or drop those perks from Upgrade. Proposed: drop
  them (simpler, and Free keeps the save-and-track loop).
  **Decided (owner, 2026-11-19):** drop "Filters that stick" and "Saved-deal
  tracking". The Upgrade perks are:
  - **Hear first, not on Sunday:** "Get each deal by email within the hour
    it's confirmed. Free members wait for the Sunday digest, and good fares
    often don't last that long."
  - **Up to 5 departure cities:** "Add the airports you could reach by train or
    a short drive. More airports, more deals."
  - **Name your price on any route:** "Set a target for a route you care
    about, and we'll email you when it dips under."

  On phone, "Know when a saved fare changes" becomes "Deals days before the
  Sunday email".

- **G39 · owner:** the landing Plus card says "Filter by trip length and
  month", but `prefs` has no month. Resolution: drop "and month" from the copy,
  or add `months` to `prefs`. Proposed: drop it.
  **Decided (owner, 2026-11-19):** the landing Plus card's last bullet is "Cancel
  any time from My alerts" (replacing "Filter by trip length and month").

- **G12 · spec:** on the ended page, "Tell me when Goa → Dubai drops again"
  creates a watch, which is Plus only. Resolution: Free users get the same
  button, which leads to `/plus` with the copy "Watching routes is a Plus
  feature".
- **G21 · spec:** the unsubscribe option "Weekly digest only" means nothing to
  Free users, who already get only the digest. Resolution: hide that option
  for Free users.
- **G42 · owner:** these are still open: whether Free gets any instant alerts,
  and whether a trial starts at sign-up. The canvas assumes a 14-day trial
  (Settings shows "Plus trial · 9 days left"; E4). Resolution: decided by the
  owner before phase 6, which needs it for setup and My alerts.

### Wording and leftovers on the canvas

- **G14 · spec:** after joining, the shared page says "We sent a link to
  confirm your email", but sign-in is a 6-digit code. Resolution: after
  "Get free alerts", go to the code screen (P8 step 2) with the city
  prefilled, then to setup step 2. Proposed copy: "Check your inbox: we sent a
  6-digit code to {email}."
- **G13 · spec:** the shared page's city select lists 5 cities, while
  everything else lists 7. Resolution: list all 7.
- **G40 · spec:** the SignIn and PhoneSignIn boards call the email state
  `phone`, a leftover from WhatsApp. The name doesn't show in the UI.
  Resolution: call it `email` in `web/`.
- **G41 · spec:** links in the boards point to the wrong places:
  - E1's "Change alerts" links to the phone setup board (it should go to
    `/alerts`);
  - the phone settings "+ Add" goes to setup.

  Resolution: every "Change alerts" link goes to `/alerts`.
- **G18 · owner:** the first-visit page's "Send me a sample alert" button.
  Is a sample alert a "test card"? It isn't experiment output, but the owner
  ruled out test cards in the UI. Resolution: ask the owner. If kept, the
  sample uses a real recent deal and the subject line "Sample:".
- **G16 · owner:** `users.consent_at` needs a consent checkbox or line at
  sign-up, and the canvas has none. Resolution: a line under setup step 3's
  button, "By continuing you agree to our Privacy policy", where submitting
  records consent. Final wording waits for the owner's DPDP review (phase 9,
  step 5).
- **G17 · spec:** sign-in has no copy for a wrong code, an expired code or too
  many attempts. Resolution, as proposed copy:
  - wrong code: "That code doesn't match. Check the latest email."
  - expired: "That code has expired. We've sent a new one."
  - rate limit: "Too many tries. Wait 15 minutes and try again."
- **G19 · spec:** desktop My alerts has a Save bar; phone has none. Resolution:
  both save explicitly with the same sticky bar, because a partly-edited
  preference shouldn't reach matching.
- **G20 · spec:** Saved says "Manage in My alerts" for watches, but My alerts
  has no watches section. Resolution: manage watches in Saved itself, with a
  remove button per `WatchRow`, and drop the link.
- **G22 · lld:** the delete and cancel pages ask for an optional reason, which
  the LLD has no place to store. Resolution: send it as anonymous counts
  (`reason`, `at`, no user id) to a `leave_reasons` table, or drop the
  select. Proposed: drop it until the owner wants the data. DPDP favours
  collecting less.
- **G23 · lld:** the contact form has no endpoint. Resolution: `POST
  /api/contact {topic, email, message}`, rate-limited, which forwards to the
  owner's inbox through the email provider and counts against
  `EMAIL_DAILY_CAP`. Until then, the form becomes a `mailto:` link.
- **G24 · lld:** Privacy's "Download my data" promises "We'll email you a
  copy", while `GET /api/me/export` returns JSON. Resolution: a direct
  download, with the label "Download my data (JSON)". No email is needed.
- **G25 · owner:** Upgrade shows a card-number and UPI ID field on our own
  page. Resolution: use the payment provider's hosted checkout (Razorpay
  assumed), so the page shows only plan, method and "Continue to payment";
  faredrop never handles card numbers. Manage Plus's "Approve in UPI app"
  becomes the provider's mandate flow.
- **G27 · lld:** the ops feedback page lets the owner set verdicts, but
  `/internal/verdicts` is read-only and holds counts. Resolution: the page reads
  per-deal counts and shows the owner's own verdict from the `feedback` table
  (the owner is user #1). Editing goes through the same `/f/` links.
- **G28 · lld:** verdict names differ:
  - ops: `good` / `meh` / `wrong`;
  - the email: "Great deal" / "Not my kind of trip" / "Price was different";
  - the LLD: `good` / `not_for_me` / `price_different`.

  "Wrong" (a bad deal) and "price different" aren't the same thing.
  Resolution: users have the LLD's three; the ops page maps `meh` →
  `not_for_me` and `wrong` → `price_different`, and keeps the owner-only
  label "Wrong" for display. Alternatively, add `wrong` as a fourth,
  owner-only verdict.
- **G29 · lld:** the digest board lists a deal "Ended Thursday", but LLD §7.6
  includes only deals that are still `live`. Resolution: follow the LLD (live
  only), so the digest never sends something unbookable.
- **G30 · spec:** E3 shows only the "got cheaper" case, but LLD §7.3 has three
  triggers. Resolution, as proposed headings for the other two:
  - ended: "A fare you saved has ended" / "Fares like it come back";
  - rose out of range: "A fare you saved went up" / "It's now back inside the
    normal range."
- **G43 · owner:** the landing section "Deals our members got recently"
  includes HYD→SHJ 17–20 Nov, which has departed, and CCU→FRA, which the owner
  rated wrong on 15 Nov. Resolution: recent deals = the last 30 days' deals
  with a `good`-or-unrated verdict; departed ones are allowed (they're
  "recent", not live) but never linked as bookable.
  **Decided (owner, 2026-11-19):** heading "**Fares we caught recently**", sub-line
  "Real return fares from Indian cities, priced twice before we sent them. One
  adult, at most one stop." Show the last 30 days' deals, leaving out any the
  owner rated wrong. Departed deals may show, marked "Ended" and with no
  booking link. Sample set: BOM→SGN, GOX→BKK, BOM→BAH, BLR→SGN, GOI→CMB,
  GOI→DXB (ended); not CCU→FRA.

- **G44 · owner:** some trust claims need to stay true:
  - "Checked twice" and "Still there an hour later" hold only if confirmation
    happens on the next hourly `gf.yml` run;
  - E1's feedback note "We'll re-check this fare in the next hour" depends on
    the open re-check budget decision.

  Resolution: keep "checked twice" and drop "an hour later" in favour of "on a
  later check". Make the re-check note "We'll re-check this fare" until the
  side thread sets a budget.
  **Decided (owner, 2026-11-19):**
  - The deal-page check reads "**Confirmed on a second check**" / "We price
    every fare twice, at different times, before we tell anyone."
  - The landing "Checked twice" body ends "…so the fare is far more likely to
    still be there when you open the alert."
  - E1's "Price was different" note is "Thanks, we'll check this fare again."

- **G45 · spec:** P9 says "to 25 destinations" even when the user switched
  regions off. Resolution: count the destinations in the chosen regions.

### Design system

- **G31 · spec:** `--faint` `#9A9DA4` on white is 2.7:1, under WCAG 1.4.11's
  3:1 for checkbox and radio borders. Resolution (phase 1): light `--faint` is
  `#82858C`, 3.24:1 or better on surface, bg, surface2 and chip. (`#8A8D94`,
  first proposed, is 3.05:1 on bg and 2.91:1 on chip.) axe only checks text
  contrast, so `web/scripts/check-tokens.mjs` verifies it.
- **G32 · spec:** fonts load from Google Fonts on the canvas. Resolution:
  self-host Inter and Space Grotesk (OFL, free) from `web/public/fonts`, so
  Pages serves everything and no third party sees visits.
- **G33 · spec:** LLD §9 asks for a manual theme switch, but no board shows
  one. Resolution: a small icon button in `SiteHeader` and in My alerts →
  Account, cycling system / light / dark.

### Found in phase 1 (2026-11-19)

- **G46 · spec:** no board states the price-bar scale. Resolution: max =
  ceil(range_high × 1.08, ₹2,000), or ceil(usual × 1.1, ₹5,000) when
  range_high > 2 × usual (the cut "broken" bar). min = floor(price − 0.18 ×
  (max − price), ₹5,000). This reproduces both boards (20,000–48,000; cut at
  60,000). It lives in `web/src/components/PriceRangeBar.tsx`.
- **G47 · lld:** where emails are rendered (`notify.py` or the Worker) is open.
  Resolution: phase 1 ships `EmailShell.astro` as a light-only, inline-hex,
  table preview. Phase 7 picks the renderer and ports it.
- **G48 · spec:** the DarkMode board's logo arrow is `#C2410C`, but the other
  themed boards keep `#F08A4B` in dark. Resolution: keep `#F08A4B`
  (`--brand`) in both themes.
- **G49 · spec:** the plan says non-interactive components are "plain Astro".
  Phase 2's feed is a client-side island, and Astro components can't render
  inside one. Resolution: shared components are Preact `.tsx`. With no
  `client:` directive they ship no JS. Page chrome stays `.astro`.
- **G50 · lld:** LLD §9 says `theme.css`; the plan and `web/` use
  `tokens.css`. Resolution: say `tokens.css` in the LLD.
- **G51 · spec:** strings with no board, written in phase 1:
  - WatchRoute locked state: "Route watches are part of Plus." / "See Plus";
  - the email field error: "Enter a full email address, like
    you@example.com.";
  - the ThemeSwitch labels: "Theme: same as device / light / dark. Switch to
    …";
  - aria-only labels: "Loading deals", "6-digit code", "Was" before an ended
    saved price.

  Resolution: the owner approves or rewords them before phase 2 copy is
  final.
  **Decided (owner, 2026-11-19):**
  - The locked watch box reads "**Name your price on this route.** Plus emails
    you the moment it drops below it." with the button "Try Plus".
  - The email error is "That email looks incomplete. Try something like
    you@example.com."
  - Screen-reader-only labels stay as written.

- **G52 · lld:** LLD §5 gives no response bodies. `web/src/data/types.ts`
  proposes `DealsPage`, `DealDetail`, `Meta`, `Me`, `SavedItem` and `Watch`.
  Resolution: phase 5 writes them into LLD §5 or changes the types.
- **G53 · spec:** `/dev/components` would deploy with the site in phase 4,
  including the fixture's CCU-FRA, which the owner rated wrong. Resolution:
  phase 4 excludes `src/pages/dev/` from production builds.

## Appendix A. Copy, verbatim, per page

> **Approved copy changes (owner, 2026-11-19).** Appendix A is the canvas
> verbatim. Where it differs from a decision in §7 (G9, G38, G39, G43, G44,
> G51), the §7 decision wins. Pages built from phase 2 on use the decided
> wording.


Generated from the canvas boards (version `1795082767-d03c`):
- the text in each board's markup, then the strings in its logic, in board order;
- `{{x}}` marks a value filled from data;
- names, emails, prices, dates and counts are sample data (section 6), but sentence wording is copy.

The wordmark `faredrop` is in every header and isn't repeated below; three-letter airport codes are data. A string that's identical on a page's desktop and phone boards is listed once, under the first board. Strings in gaps G14, G17, G30, G39 and G44 have proposed replacements in section 7.

### P1 Landing

**Landing**

- [aria-label] Main
- How it works
- Recent deals
- Pricing
- Sign in
- Flight deals from Indian cities
- Fly abroad for a lot less than usual.
- Tell us where you fly from. We watch international fares around the clock and message you only when one drops well below its normal price.
- I fly from
- Mumbai
- Bengaluru
- Goa
- Kolkata
- Hyderabad
- Chennai
- Kochi
- Email
- [placeholder] you@example.com
- Get deal alerts, free
- 7 departure cities
- 25 destinations
- No spam: only real drops
- Bangkok
- from Goa · 3–22 Dec
- New deal · just now
- Ho Chi Minh City
- from Mumbai · non-stop · 5–11 Apr
- ₹25,218
- ₹35,948
- You save ₹10,730
- Book →
- We do the watching. You just decide whether to go.
- {{h.n}}
- {{h.title}}
- {{h.body}}
- Deals our members got recently
- Return fares, one adult, at most one stop.
- {{r.from}} →
- {{r.to}}
- {{r.price}}
- {{r.usual}}
- {{r.pct}}% off usual
- Real prices you can book
- Many cheap-fare sites show prices from foreign resellers you can't actually buy from India. We only show fares priced for Indian travellers.
- Checked twice
- A fare has to still be there on a second check before we message you, so you don't open an alert to find it's gone.
- Cheap, not painful
- At most one stop, on trips of 2 to 21 nights. No 30-hour trips with three changes just to save ₹2,000.
- Start free. Upgrade when a deal pays for it.
- Free
- ₹0
- One departure city
- A weekly email with the best deals
- Browse every live deal on the site
- Start free
- Plus
- Recommended
- [PRICE]
- / year
- Instant email alerts, while fares are fresh
- Up to 5 departure cities
- Watch specific routes with your own price target
- Filter by trip length and month
- Try Plus
- © faredrop
- We don't sell tickets. You book directly with the airline or travel site.
- Privacy
- Contact
- Bahrain
- Frankfurt
- Dubai
- Sharjah
- Colombo
- Pick your cities
- Choose the airports you fly from and, if you like, the places you dream about. Leave it open and we watch all 25 destinations.
- We watch fares all day
- We compare every fare with what that trip normally costs on those dates, and re-check the good ones before they reach you.
- Book fast
- You get one clear message: where, when, how much, and how much you save. Tap through and book with the airline.

**PhoneLanding** (phone)

- Tell us where you fly from. We email you only when an international fare drops well below its normal price.
- ✓ 7 departure cities
- ✓ 25 destinations
- ✓ Only real drops
- What an alert looks like
- We do the watching. You decide whether to go.
- {{r.route}}
- {{t.t}}
- {{t.d}}
- One city · weekly email · browse every deal
- [PRICE]/yr
- Instant email alerts · up to 5 cities · watched routes
- We don't sell tickets. You book with the airline or travel site.
- The airports you fly from, and the regions you dream about.
- Each fare is compared with what those dates normally cost, and re-checked before it reaches you.
- One clear email: where, when, how much, and what you save.
- Mumbai → Bahrain
- Goa → Bangkok
- Kolkata → Frankfurt
- Bengaluru → Ho Chi Minh City
- Only fares priced for Indian travellers, not foreign resellers.
- A fare must still be there on a second check before we tell you.
- At most one stop, on trips of 2 to 21 nights.

### P2 Deals feed

**Main**

- [aria-label] Main
- Deals
- Saved
- {{savedCount}}
- My alerts
- Email alerts on
- [aria-label] Your account
- P
- Good morning, Priya
- {{liveCount}} international fares well under their usual price
- From Mumbai, Goa, Bengaluru and Kolkata. Every fare here was priced twice before we showed it to you.
- Change cities
- [aria-label] Filters
- {{c.label}}
- Trip
- Any length
- Short break (2–5 nights)
- A week or so
- Long holiday (2 weeks+)
- Sort
- Biggest saving
- Lowest price
- Soonest departure
- Hidden {{lastHidden}}. We'll show you fewer trips like it.
- Undo
- No deals match right now
- Try another city or trip length. We'll message you the moment something fits.
- Clear filters
- {{d.toCity}}
- from {{d.fromCity}} · {{d.from}} → {{d.to}}
- [aria-label] Save this deal
- {{d.price}}
- usually
- {{d.usual}}
- Save {{d.save}}
- {{d.dates}}
- {{d.nights}}
- {{d.flight}}
- {{d.kind}}
- {{d.groupTitle}}
- {{g}}
- {{d.fresh}}
- Not interested
- See deal
- Prices are for one adult, return, economy, with at most one stop. Fares change fast and you book directly with the airline or travel site; faredrop never takes your payment for flights.
- Mumbai
- Bahrain
- 14–18 Apr
- Kuwait Airways · 1 stop
- Checked 2 h ago
- Goa
- Bangkok
- 3–22 Dec
- IndiGo · 1 stop
- Checked 40 min ago
- Ho Chi Minh City
- 5–11 Apr
- Vietjet · non-stop
- Checked 5 h ago
- 31 Mar–6 Apr
- 1–8 Apr
- Kolkata
- Frankfurt
- 24–28 Jan
- Etihad · 1 stop
- Checked yesterday
- Bengaluru
- 10–26 Feb
- Checked 1 h ago
- Colombo
- ~₹39,000
- 16–19 Jan
- Checked 3 h ago
- 4–11 Jan
- 7–12 Jan
- 9–12 Jan
- 16–23 Jan
- 20–24 Jan
- All my cities
- Short break
- A week away
- Long holiday
- Also this cheap on
- other date

**Mobile** (phone)

- [aria-label] Alert settings
- {{countText}}
- {{d.route}}
- {{d.meta}}
- −{{d.pct}}% vs usual
- BOM → BAH
- 14–18 Apr · Kuwait Airways, 1 stop
- ₹20,231
- GOX → BKK
- 3–22 Dec · IndiGo, 1 stop
- ₹35,232
- BOM → SGN
- 5–11 Apr · Vietjet, non-stop · +2 dates
- ₹25,218
- CCU → FRA
- 24–28 Jan · Etihad, 1 stop
- ₹58,831
- BLR → SGN
- 10–26 Feb · Vietjet, non-stop
- ₹22,789
- HYD → SHJ
- 17–20 Nov · SalamAir, 1 stop
- ₹26,631
- GOI → CMB
- 16–19 Jan · IndiGo, 1 stop · +5 dates
- ₹31,395
- All
- GO
- · biggest saving first

### P3 Deal page

**DealDetail**

- [aria-label] Main
- Deals
- Saved
- My alerts
- All deals
- Price checked twice
- Last checked 5 h ago
- Mumbai to Ho Chi Minh City · 5–11 Apr 2027 · 6 nights · return, 1 adult
- ₹25,218
- ₹10,730 (30%) below
- the usual ₹35,948
- Where this price sits
- What this trip normally costs on these dates, and where today's fare lands.
- ₹30,500
- cheapest normal
- ₹44,000
- priciest normal
- usual ₹35,948
- this deal
- Why it counts as a deal
- {{c.title}}
- {{c.detail}}
- Why we sent it
- {{s.when}}
- {{s.title}}
- {{s.detail}}
- Flight
- Airline
- Vietjet
- Stops
- Non-stop both ways
- Out
- Mon 5 Apr 2027
- Back
- Sun 11 Apr 2027
- Book this fare
- Where to book
- Vietjet (airline site)
- Compare on Google Flights
- opens a new tab
- Price gone when you get there?
- Tell us
- and we'll mark it.
- {{saveLabel}}
- {{shareLabel}}
- You book directly with the airline or travel site. Fares like this usually last a few days.
- Also this cheap on
- Flexible? These dates are about the same price.
- 31 Mar–6 Apr
- 1–8 Apr
- Watch Mumbai → Ho Chi Minh City
- Get an email the next time this route drops, even if it's not a top deal.
- Tell me when it's under
- Watch this route
- Watching. We'll message you under {{target}}.
- Stop
- ₹28,000
- Save
- Link copied
- Share
- 30% under what this trip usually costs
- Normal fares for these dates run ₹30,500–44,000. This is ₹5,282 below even the cheapest of those.
- You save ₹10,730
- Against the usual ₹35,948, for one adult, return.
- We never show deals with more than one stop.
- A real, bookable fare
- Priced on a public flight search from India, not a foreign reseller.
- Still there an hour later
- We check every fare twice before telling anyone about it.
- Day 1
- Spotted
- A Mumbai to Vietnam fare looked low.
- Compared
- Measured against what these dates normally cost.
- Re-checked
- Priced again to make sure it is real.
- Today
- Sent to you
- Because Mumbai is one of your cities.

**DealOneStop**

- Last checked 40 min ago
- Goa (Mopa) to Bangkok · 3–22 Dec 2026 · 19 nights · return, 1 adult
- ₹35,232
- ₹18,447 (34%) below
- the usual ₹53,679
- The normal range for these dates is unusually wide, so the scale is cut at ₹60,000.
- ₹36,500
- up to ₹3,05,000
- long multi-airline trips
- usual ₹53,679
- ₹35,232 this deal
- The top of the range comes from long trips with several airlines. We judge this fare against the usual price and the cheapest normal fare, not the top.
- IndiGo
- 1 stop each way, in Hyderabad
- Thu 3 Dec 2026
- Tue 22 Dec 2026
- IndiGo (airline site)
- About the stop
- You change planes in Hyderabad both ways, on one IndiGo booking. Check the connection time on the booking page before you pay.
- Long holiday · 19 nights
- Watch Goa → Bangkok
- ₹40,000
- 34% under what this trip usually costs
- The usual price for these dates is ₹53,679. This is also below the cheapest normal fare, ₹36,500.
- You save ₹18,447
- For one adult, return.
- One stop, in Hyderabad
- Allowed: we never show deals with more than one stop.
- A Goa to Bangkok fare looked low.
- Because Goa is one of your cities.

**DealNoRange**

- Last checked yesterday
- Kolkata to Frankfurt · 24–28 Jan 2027 · 4 nights · return, 1 adult
- ₹58,831
- ₹20,535 (26%) below
- the usual ₹79,366
- How it compares
- We know the usual price for these dates but not the full range, so this is a straight comparison.
- Usual price
- ₹79,366
- This deal
- Prices can differ a little between sites, and a signed-in browser sometimes shows a lower one. If you see a different price, tell us from the booking panel.
- Etihad
- 1 stop each way, in Abu Dhabi
- Sun 24 Jan 2027
- Thu 28 Jan 2027
- Etihad (airline site)
- You change planes in Abu Dhabi both ways. Some itineraries mix Etihad with a partner airline on one leg; the booking page shows which.
- Short break · 4 nights
- Watch Kolkata → Frankfurt
- ₹60,000
- 26% under what this trip usually costs
- The usual price for these dates is ₹79,366.
- You save ₹20,535
- One stop, in Abu Dhabi
- A random check of Kolkata to Frankfurt came back low.
- Measured against the usual price for these dates.
- Because Kolkata is one of your cities.

**PhoneDeal** (phone)

- [aria-label] Back to deals
- BOM → SGN
- [aria-label] Share
- Link copied. Paste it into any chat.
- Ho Chi Minh City
- from Mumbai · 5–11 Apr · 6 nights
- ₹35,948
- You save ₹10,730 (30%)
- normal: ₹30,500–44,000
- Tell me if it drops under ₹28,000
- Watching. We'll message you under ₹28,000.
- [aria-label] Where to book
- [aria-label] Close
- new tab
- Gone when you get there?
- [aria-label] Save this deal
- Book for ₹25,218

### P4 Deal ended / gone

**Expired**

- [aria-label] Main
- Deals
- Saved
- My alerts
- Deal ended
- Goa → Dubai has gone back up
- The 1–15 Nov fare of
- ₹33,883
- is no longer available. Fares like this usually last only a few days.
- Tell me when Goa → Dubai drops again
- Watching Goa → Dubai.
- Undo
- See live deals
- Saw it gone before we did? Thanks: reports like yours make the next alert faster.
- Still live from Goa
- Bangkok
- 3–22 Dec · IndiGo, 1 stop
- ₹35,232
- −34%
- Colombo
- 16–19 Jan · IndiGo, 1 stop · +5 dates
- ₹31,395
- −20%

### P5 Shared deal

**ShareDeal**

- Sign in
- A friend shared this fare with you
- Mumbai → Ho Chi Minh City
- 5–11 Apr 2027 · 6 nights · Vietjet, non-stop · return, 1 adult
- Still live · checked 5 h ago
- ₹25,218
- ₹35,948
- 30% under the usual
- Check it and book
- {{copyLabel}}
- Fares like this usually last a few days. We'll mark this page if it ends.
- Get fares like this from your city
- We watch international fares from 7 Indian cities and only message you when one is well below normal. Free.
- I fly from
- Mumbai
- Bengaluru
- Goa
- Kolkata
- Hyderabad
- Email
- [placeholder] you@example.com
- Get free alerts
- Check your inbox
- We sent a link to confirm your email. Then we'll start watching fares from Mumbai.
- Pick destinations now →
- Link copied
- Copy link

**PhoneShare** (phone)

- 5–11 Apr · 6 nights · Vietjet, non-stop
- 30% under the usual price
- Return, 1 adult. Fares like this usually last a few days.
- Free. We only email when a fare is well below normal.
- Confirm your email and we'll ask which city you fly from.
- Set it up now →
- [aria-label] Copy link

### P6 Link preview image

**SharePreview**

- 30% off usual
- Mumbai →
- Ho Chi Minh City
- 5–11 Apr · non-stop · return
- ₹25,218
- ₹35,948

### P7 Set up alerts

**OnboardingWeb**

- Already a member?
- Sign in
- {{s.n}}
- {{s.title}}
- {{s.sub}}
- Where do you fly from?
- Pick your home airport, plus any you could easily get to. Free covers one city; Plus covers up to five.
- {{o.label}}
- Where would you go?
- Leave everything on to hear about any great deal.
- {{r.label}}
- {{r.eg}}
- Trip length
- Any (2–21 nights)
- Short breaks (2–5 nights)
- About a week
- Long holidays (2 weeks+)
- How should we tell you?
- Good fares often last only a few days, so faster is better.
- {{c.label}}
- {{c.eg}}
- {{contactLabel}}
- [placeholder] {{contactHint}}
- {{summary}}
- Back
- Continue
- Start watching fares
- Mumbai
- Bengaluru
- Goa
- Kolkata
- Hyderabad
- Chennai
- Kochi
- Gulf & Middle East
- Dubai, Abu Dhabi, Doha, Muscat
- South-East Asia
- Bangkok, Bali, Vietnam, Singapore
- Sri Lanka, Maldives & Nepal
- Colombo, Malé, Kathmandu
- East Asia
- Hong Kong, Tokyo, Seoul
- Europe
- London, Paris, Frankfurt, Istanbul
- Australia
- Sydney
- Instant email
- The hour a deal is confirmed · Plus
- Weekly email
- Every Sunday · Free
- Your cities
- Destinations
- of 6 regions
- Alerts
- 5 of 5 cities. Remove one to swap.
- of 5 cities
- regions on
- You can change all of this later
- Email address
- margin-left: auto;

**Onboarding** (phone)

- [aria-label] Back
- Step {{stepNo}} of 3
- Pick up to 5. Add a city you'd happily take a train to.
- The hour a deal is confirmed
- Weekly digest
- The best of the week, every Sunday
- of 6 regions on

### P8 Sign in

**SignIn**

- Welcome back
- We'll email you a 6-digit code. No password needed.
- Email
- [placeholder] you@example.com
- Send code
- New here?
- Set up free alerts
- ← Change email
- Enter your code
- Sent to {{phone}}. Check spam if it's not there in a minute.
- [aria-label] {{b.label}}
- Sign in
- Didn't get it?
- Resend in 0:24
- Digit

**PhoneSignIn** (phone)

- We'll email you a 6-digit code.
- Sent to {{phone}}.
- Didn't get it? Resend in 0:24

### P9 First visit

**Empty**

- [aria-label] Main
- Deals
- Saved
- My alerts
- You're all set
- We're now watching fares from
- Mumbai
- to 25 destinations. No deal from Mumbai right now, and that's normal: real drops come in bursts, not every day.
- {{testLabel}}
- Browse deals from other cities
- Sent a sample alert to priya@example.com. That's what a real one looks like.
- Get more out of faredrop
- {{t.mark}}
- {{t.title}}
- {{t.sub}}
- {{t.cta}}
- Sent ✓
- Send me a sample alert
- Alerts by email
- Edit
- Add a second city
- Goa or Bengaluru gives you more deals to choose from
- Add city
- Get alerts within the hour
- Free members get a weekly email; Plus is instant
- Try Plus

### P10 My alerts

**Settings**

- [aria-label] Main
- Deals
- Saved
- My alerts
- [aria-label] Your account
- P
- Plus trial · 9 days left
- After that you move to Free: one city and a weekly email, no instant alerts.
- Keep Plus
- I fly from
- {{cityCount}} of 5 on Plus
- {{c.label}}
- [aria-label] {{c.removeLabel}}
- Add a city
- + Add a city
- Hyderabad
- Chennai
- Kochi
- Send deals to
- {{r.label}}
- {{r.eg}}
- [aria-label] {{r.label}}
- How we tell you
- {{c.eg}}
- [aria-label] {{c.label}}
- Only deals that save at least
- ₹4,000
- ₹7,500
- ₹10,000
- ₹20,000
- Trip length
- Any (2–21 nights)
- Short breaks
- About a week
- Long holidays
- Quiet hours
- 11 pm – 7 am
- None
- 10 pm – 8 am
- Account
- Email
- priya@example.com
- Sign out
- Plus and billing
- Privacy
- Contact us
- Delete my account
- {{saveNote}}
- Save changes
- Mumbai
- Goa
- Bengaluru
- Kolkata
- Remove
- Gulf & Middle East
- Dubai, Abu Dhabi, Doha, Muscat
- South-East Asia
- Bangkok, Bali, Vietnam, Singapore
- Sri Lanka, Maldives & Nepal
- Colombo, Malé, Kathmandu
- East Asia
- Hong Kong, Tokyo, Seoul
- Europe
- London, Paris, Frankfurt, Istanbul
- Australia
- Sydney
- Instant email
- The hour a deal is confirmed, to priya@example.com
- Weekly digest
- The best of the week, every Sunday morning
- Saved. New alerts use these settings.
- You have unsaved changes
- All changes saved

**PhoneSettings** (phone)

- Then weekly email only
- {{cityCount}} of 5
- + Add
- {{s.label}}
- {{s.eg}}
- [aria-label] {{s.label}}
- The hour a deal is confirmed
- Sundays
- Dubai, Doha, Muscat
- Bangkok, Bali, Singapore
- London, Paris, Istanbul

### P11 Saved

**Saved**

- [aria-label] Main
- Deals
- Saved
- My alerts
- [aria-label] Your account
- P
- We re-check saved fares and tell you if the price moves or the deal ends.
- Nothing saved. Tap the bookmark on any deal to keep it here.
- Browse deals
- {{d.title}}
- {{d.meta}}
- {{d.price}}
- {{d.note}}
- {{d.cta}}
- [aria-label] {{d.removeLabel}}
- Routes you're watching
- Manage in My alerts
- {{w.route}}
- Tell me under
- {{w.target}}
- {{w.status}}
- Mumbai → Ho Chi Minh City
- 5–11 Apr · 6 nights · Vietjet, non-stop
- ₹25,218
- Same price as when you saved it
- See deal
- Goa → Bangkok
- 3–22 Dec · 19 nights · IndiGo, 1 stop
- ₹35,232
- Leaves in 19 days
- Mumbai → Bahrain
- 14–18 Apr · 4 nights · Kuwait Airways, 1 stop
- ₹20,231
- Saved just now
- Kolkata → Frankfurt
- 24–28 Jan · 4 nights · Etihad, 1 stop
- ₹58,831
- Bengaluru → Ho Chi Minh City
- 10–26 Feb · 16 nights · Vietjet, non-stop
- ₹22,789
- Goa → Colombo
- 16–19 Jan · 3 nights · IndiGo, 1 stop
- ₹31,395
- Goa → Dubai
- 1–15 Nov · 14 nights · saved 17 Oct
- ₹33,883
- Deal ended
- Similar deals
- Remove
- ₹28,000
- Now ₹25,218, under your target
- Mumbai → London
- ₹55,000
- Watching since 2 Nov
- ₹30,000
- Closest so far ₹30,065

**PhoneSaved** (phone)

- We tell you if a saved fare changes or ends.
- Nothing saved yet. Tap the bookmark on a deal to keep it here.
- under
- 5–11 Apr · Vietjet, non-stop
- 3–22 Dec · IndiGo, 1 stop
- 1–15 Nov · saved 17 Oct
- Now ₹25,218

### P12 Unsubscribe

**Unsubscribe**

- Too many deal emails?
- For priya@example.com. Pick what suits you; you don't have to leave altogether.
- [aria-label] Email preference
- {{o.label}}
- {{o.sub}}
- {{confirmLabel}}
- {{doneTitle}}
- {{doneBody}}
- Changed my mind
- See current deals
- Pause for a month
- No emails until 14 Dec, then back to normal
- Paused until 14 Dec
- No deal emails for a month. Everything else stays as it is.
- Weekly digest only
- One email on Sunday with the week’s best
- You’ll get one email each Sunday instead of an email per deal.
- Only big savings
- Deals that save ₹10,000 or more
- Only big savings from now on
- We’ll only email deals that save at least ₹10,000.
- Unsubscribe from all emails
- Your account and saved deals stay
- You’re unsubscribed
- No more deal emails. Your account and saved deals are untouched.
- Unsubscribe
- Save preference

**PhoneUnsubscribe** (phone)


### P13 Delete account

**DeleteAccount**

- Back to My alerts
- Delete your account?
- This can't be undone. We will permanently delete:
- Your email address and sign-in
- Your cities, alert settings and watched routes
- Your saved deals and feedback
- Your Plus trial (9 days left)
- Just want a break? Pausing keeps everything and stops all alerts for a month.
- Pause instead
- Why are you leaving? (optional)
- Choose a reason
- Too many alerts
- Deals weren't from my city
- Prices were different when I tried to book
- I've booked my trip
- Something else
- Type DELETE to confirm
- Delete my account
- Your account is deleted
- We've removed your details and stopped all alerts. A confirmation is on its way to priya@example.com. Safe travels.
- Go to faredrop home
- DELETE

**PhoneDelete** (phone)


### P14 Contact

**Contact**

- Get in touch
- We're a small team and read everything. Most questions are answered below.
- {{f.q}}
- {{f.sign}}
- {{f.a}}
- Send us a message
- About
- A deal or a price
- My alerts
- Plus and billing
- Something else
- Your email
- Message
- [placeholder] If it's about a deal, tell us the route and dates.
- Send message
- Or email [SUPPORT EMAIL]. We usually reply within [REPLY TIME].
- Message sent
- We'll reply to priya@example.com.
- Send another
- The price was different when I tried to book
- Fares change quickly, and sites sometimes show slightly different prices to signed-in visitors. If it was more than a few percent off, use “Price was different” on the alert and we’ll re-check it.
- How do you decide something is a deal?
- We compare each fare with what that trip normally costs on those dates. It has to be below the cheapest normal price, save at least ₹4,000, have at most one stop, and still be there when we check again.
- Do you sell tickets?
- No. You book directly with the airline or a travel site. We never take payment for flights.

**PhoneContact** (phone)


### P15 Privacy

**Privacy**

- Contact
- [aria-label] On this page
- On this page
- What we collect
- How we use it
- Who we share it with
- How long we keep it
- Your choices
- Draft for design review. The final policy needs legal review, including India's Digital Personal Data Protection Act.
- Privacy, in plain words
- We need very little to send you flight deals, so we collect very little. Last updated [DATE].
- Your email address, to send alerts and sign you in.
- Your cities, destinations and alert settings.
- Deals you save, routes you watch, and feedback you give on deals.
- If you buy Plus: a record of the payment. Your UPI or card details go to our payment provider, not to us.
- We don't collect your passport details, travel dates you book, or anything from airline sites.
- Only to run faredrop: picking which deals to send you, sending them, and improving which deals we pick. We don't sell your data or use it for advertising.
- Only the services that deliver faredrop for us: [EMAIL PROVIDER] for email and [PAYMENT PROVIDER] for Plus. When you click through to book, the airline or travel site sees that visit like any other.
- While your account is open. When you delete it, your details are removed within [N] days; payment records are kept as long as tax law requires.
- You can see, correct or delete your data at any time. Questions or complaints go to our grievance officer at [GRIEVANCE CONTACT].
- {{downloadLabel}}
- Edit my details
- Delete my account
- We’ll email you a copy of your data
- Download my data

**PhonePrivacy** (phone)


### P16 Upgrade to Plus

**Upgrade**

- Not now
- faredrop Plus
- Hear about deals while they still exist.
- Good fares tend to last a few days. Free members hear about them on Sunday; Plus members hear within the hour.
- {{p.t}}
- {{p.d}}
- One deal pays for it.
- The last deal from Mumbai saved ₹10,730 on a return to Ho Chi Minh City.
- [aria-label] Billing
- {{p.label}}
- {{p.price}}
- {{p.note}}
- Pay with
- {{m.label}}
- {{fieldLabel}}
- [placeholder] {{fieldHint}}
- Start Plus · {{payLabel}}
- Cancel any time in My alerts. You keep Plus until the end of the period you paid for.
- You're on Plus
- Instant email alerts are on for Mumbai, Goa, Bengaluru and Kolkata.
- Back to deals
- Yearly
- per year · best value
- Monthly
- per month
- Card
- UPI ID
- Card number
- 1234 5678 9012 3456
- [PRICE] / year
- [PRICE] / month
- Instant email alerts
- Within the hour of a deal being confirmed, not on Sunday.
- Up to 5 departure cities
- Add the airports you could reach by train or a short drive.
- Watch your own routes
- Set a target price for any route and we tell you when it dips under.
- Filters that stick
- Trip length, regions, minimum saving and quiet hours.
- Saved-deal tracking
- We tell you if a saved fare changes or ends.

**PhoneUpgrade** (phone)

- [aria-label] Close
- {{p}}
- One deal pays for it: the last one from Mumbai saved ₹10,730.
- Pay with UPI · {{payLabel}}
- Cancel any time in My alerts
- Instant email alerts are on for your 4 cities.
- Best value
- Cancel any time
- Watch routes with your own target price
- Know when a saved fare changes

### P17 Plus and billing

**ManagePlus**

- [aria-label] Main
- Deals
- Saved
- My alerts
- ← My alerts
- Plus and billing
- Plus ends on [RENEWAL DATE].
- You keep instant alerts until then, then move to Free. You won't be charged again.
- Keep Plus after all
- Plus · yearly
- {{badge}}
- {{renewText}}
- [PRICE]
- per year, incl. GST
- Payment method
- {{upi}}
- Autopay mandate active
- Change
- New UPI ID
- [placeholder] name@bank
- Approve in UPI app
- Cancel
- Receipts
- [aria-label] Receipts
- Date
- What
- Amount
- GST invoice
- {{r.date}}
- {{r.what}}
- {{r.amount}}
- Download PDF
- Cancel Plus
- Cancel Plus?
- You keep Plus until [RENEWAL DATE] and won't be charged again. Then you'll get one city and a Sunday email. Your saved deals stay.
- Mind telling us why? (optional)
- Choose a reason
- Too few deals from my city
- Too expensive
- I've booked my trip
- Something else
- Keep Plus
- Cancel at end of period
- Ending
- Active
- Ends [RENEWAL DATE]. No further charges.
- Renews [RENEWAL DATE] via UPI autopay.
- Plus, yearly
- Plus, monthly

**PhoneManagePlus** (phone)

- [aria-label] Back to My alerts
- No more charges. You move to Free after that.
- Autopay active
- {{r.date}} · {{r.amount}}
- GST PDF
- [aria-label] Cancel Plus
- You keep Plus until [RENEWAL DATE]. Then it's one city and a Sunday email. Saved deals stay.
- Why? (optional)

### P18 Ops: pipeline health

**OpsHealth**

- ops
- [aria-label] Internal
- Pipeline
- Deal feedback
- Data as of 14 Nov 2026 (from STATUS.md) · team only
- Pipeline health
- [aria-label] Headline numbers
- {{t.label}}
- {{t.value}}
- {{t.icon}}
- {{t.note}}
- Google lookups answered, by day
- Rule: two full days under 75% → lower the daily budget
- 100%
- 75%
- 50%
- 25%
- 0%
- 75% line
- [aria-label] {{d.aria}}
- {{d.label}}
- {{d.day}}
- {{hoverText}}
- Recent changes
- {{l.when}}
- {{l.what}}
- Discovery by city
- 23 Oct – 1 Nov review window
- [aria-label] Lookups, candidates and deals by city
- City
- Lookups
- Candidates
- Deals
- {{c.name}}
- {{c.lookups}}
- {{c.cand}}
- {{c.deals}}
- Routes on back-off (priced nothing 3 times)
- {{r}}
- Probed again after 14 days, doubling up to 60.
- 9 Nov
- 10 Nov
- 11 Nov
- 12 Nov
- 13 Nov
- % of Google lookups answered
- Mumbai
- Goa (GOI + GOX)
- Kolkata
- Bengaluru
- Chennai
- Kochi
- Hyderabad
- % answered
- , under the 75% line
- Hover or tab to a bar for details.
- Travelpayouts history
- Every cell, every day since 4 Oct
- Google budget
- 60 / day
- Cut from 80 on 14 Nov
- Routes watched
- 8 airports × 25 destinations
- Answered, 9–13 Nov
- 74–89%
- Two full days under 75%
- Deals rated since 12 Oct
- 15 of 16
- 14 good · 1 not for me · 0 wrong
- 14 Nov
- Google budget 80 → 60 a day after two full days under 75% answered.
- CI broke: ubuntu-latest became 26.04 (no Python 3.9); tests pinned to ubuntu-24.04.
- 2 Nov
- Exploration share 0.3 → 0.15; review searches switched off.
- 23 Oct
- Mumbai and Kolkata became alert cities; cities take turns in discovery.
- 19 Oct
- Google budget 40 → 80 a day; Goa’s Mopa airport (GOX) added.
- GOI→HKT
- GOI→IST
- GOI→KTM
- GOI→KUL
- GOI→MLE
- GOI→SGN
- GOI→SHJ
- GOX→CMB
- GOX→KTM
- GOX→MLE
- GOX→SGN

### P19 Ops: deal feedback

**Feedback**

- ops
- [aria-label] Internal
- Pipeline
- Deal feedback
- Google deals emailed since the 12 Oct fix
- Is each deal actually good?
- [aria-label] Summary
- Rated
- {{rated}}
- of {{total}}
- Not wrong (precision)
- {{notWrong}}
- {{bound}}
- Would book (good)
- {{good}}
- Biggest single route
- GOI→CMB
- {{cmbShare}} of emailed deals: ratings lean on it
- [aria-label] Filter
- {{f.label}}
- [aria-label] Emailed deals and verdicts
- Route
- Trip
- Price
- Emailed
- Verdict
- {{r.route}}
- {{r.trip}}
- {{r.price}}
- {{r.sent}}
- {{o.label}}
- Excluded: GOI→CMB 24–30 Oct (₹46,552, emailed 12 Oct before the fix, rated wrong). Ratings come from your review page today; for users they'd come from the email's feedback buttons.
- GOI→DXB
- 1–15 Nov · 14 nights
- 17 Oct
- GOX→SHJ
- 18–25 Feb · 7 nights
- 19 Oct
- 20–25 Feb · 5 nights
- 21 Oct
- 5–12 Jan · 7 nights
- 16–19 Jan · 3 nights
- 23 Oct
- BOM→SGN
- 5–11 Apr · 6 nights
- 24 Oct
- 9–13 Dec · 4 nights
- 28 Oct
- 9–13 Feb · 4 nights
- 30 Oct
- CCU→FRA
- 24–28 Jan · 4 nights
- 31 Oct
- HYD→SHJ
- 17–20 Nov · 3 nights
- 19–24 Feb · 5 nights
- 7 Nov
- 7–14 Jan · 7 nights
- 8 Nov
- BOM→BAH
- 14–18 Apr · 4 nights
- 27 Nov–6 Dec · 9 nights
- 9 Nov
- BLR→SGN
- 10–26 Feb · 16 nights
- 12 Nov
- GOX→BKK
- 3–22 Dec · 19 nights
- 13 Nov
- All
- Unrated
- Good
- Not for me
- Wrong
- 95% lower bound ~
- % (rule of three)

### E1 Deal alert email

**Email**

- · deals@faredrop
- Mumbai → Ho Chi Minh City, ₹25,218 return (30% off)
- New deal from Mumbai
- Ho Chi Minh City for ₹25,218 return
- Usually ₹35,948. You save ₹10,730.
- When
- 5–11 Apr
- Trip
- 6 nights
- Flight
- Vietjet, non-stop
- ₹25,218 this fare
- ₹35,948 usual
- See the deal and book
- Also about this price:
- 31 Mar–6 Apr
- and
- 1–8 Apr
- . Fares like this usually last a few days.
- Was this useful?
- [aria-label] Rate this deal
- {{v.label}}
- {{voteNote}}
- Still live from your cities
- Goa → Bangkok · 3–22 Dec
- ₹35,232
- −34%
- Mumbai → Bahrain · 14–18 Apr
- ₹20,231
- −35%
- You're getting this because Mumbai is one of your cities.
- Change alerts
- Unsubscribe
- One tap. It helps us send you fewer, better deals.
- Thanks! We’ll keep sending trips like this.
- Got it. Fewer trips like this from now on.
- Thanks. We’ll re-check this fare in the next hour.
- Great deal
- Not my kind of trip
- Price was different

### E2 Weekly digest email

**DigestEmail**

- · deals@faredrop
- Your week: 4 deals from Mumbai and Goa, best saves ₹18,447
- Sunday digest · 15 Nov
- This week's best fares from your cities
- Biggest saving first. Prices were right when we last checked; they may have moved since.
- {{d.route}}
- {{d.meta}}
- {{d.status}}
- {{d.price}}
- {{d.save}}
- See all live deals
- Routes you're watching
- Mumbai → London
- No drop under ₹55,000 yet
- Goa → Colombo
- Closest: ₹30,065 (target ₹30,000)
- Plus members heard about Bahrain a week ago
- The Mumbai → Bahrain fare went to Plus members by instant email on 8 Nov. Weekly emails are free; instant alerts are Plus.
- Try Plus
- You get this every Sunday because you chose the weekly digest.
- Change alerts
- Unsubscribe
- Goa → Bangkok
- 3–22 Dec · 19 nights · IndiGo, 1 stop
- ₹35,232
- Save ₹18,447
- Still live
- Mumbai → Bahrain
- 14–18 Apr · 4 nights · Kuwait Airways, 1 stop
- ₹20,231
- Save ₹11,067
- 27 Nov–6 Dec · 9 nights
- ₹29,562
- Below the usual
- Ended Thursday
- Goa → Sharjah
- 19–24 Feb · 5 nights · Air Arabia, non-stop
- ₹31,827

### E3 Saved fare changed email

**PriceChangeEmail**

- · deals@faredrop
- Price drop: Goa → Colombo you saved is now ₹28,644
- A fare you saved got cheaper
- Goa → Colombo · 9–13 Dec
- IndiGo, 1 stop · 4 nights
- When you saved it
- ₹30,065
- Now
- ₹28,644
- Usually
- ₹37,113
- Down another ₹1,421. That's ₹8,469 under the usual price for these dates.
- See it and book
- Also in your saved list
- Goa → Dubai · 1–15 Nov
- Ended ·
- similar deals
- Mumbai → Ho Chi Minh City · 5–11 Apr
- Unchanged at ₹25,218
- We email when a saved fare drops by ₹1,000 or more, rises out of deal territory, or ends.
- Change alerts
- Unsubscribe

### E4/E5 Account emails

**AccountEmails**

- · hello@faredrop
- Your Plus trial ends in 3 days
- Trial ends 23 Nov
- Keep hearing about deals the hour they appear?
- With Plus
- Instant email alerts
- 4 cities
- Watched routes
- On Free
- A Sunday email
- 1 city (you pick)
- No watched routes
- Keep Plus · [PRICE]/year
- Do nothing and you move to Free on 23 Nov. We won't charge you; we never took a payment method for the trial.
- My alerts
- Unsubscribe
- · billing@faredrop
- Action needed: we couldn't renew your Plus
- Payment didn't go through
- Your UPI autopay for Plus was declined
- Plan
- Plus, yearly
- Amount
- [PRICE]
- Tried
- Today, via priya@bank
- Your instant alerts keep running for
- 7 more days
- . We'll try again in 3 days. After that you move to Free; nothing is deleted.
- Update payment method
- Common reasons: an autopay limit, an expired mandate, or not enough balance.
- Need help?

### States sheet

**States**

- 1 · Loading
- While deals load. Same shape as real cards, so nothing jumps.
- 2 · Can't load deals
- The deals file or API didn't answer. Show the last copy we had, clearly marked.
- We couldn't refresh deals
- Showing what we had at 09:40 today. Check prices before booking.
- Try again
- Bahrain
- from Mumbai · 14–18 Apr
- ₹20,231
- No copy at all (first visit while offline): full-page message plus "Try again", no empty grid.
- 3 · Our data is behind
- The fare checks missed a run (it happens: Google refuses some lookups). Say so instead of showing old prices as fresh.
- Prices below were last checked
- 2 days ago
- . We're catching up; check the price before you book.
- Bangkok
- ₹35,232
- Checked 2 days ago
- 4 · Price changed since we told you
- Shown on the deal page and in Saved. Real cases from Goa → Colombo.
- Goa → Colombo · 5–12 Jan
- ₹32,403
- ₹33,274
- Up ₹871 since our alert.
- It's now inside the normal price range, so it's no longer a deal.
- See similar deals
- Goa → Colombo · 9–13 Dec
- ₹30,065
- ₹28,644
- Down another ₹1,421
- since our alert. Even better now.
- 5 · No price range for these dates
- We know the usual price but not the full range. Drop the bar; don't fake it.
- Colombo
- from Goa · 16–19 Jan
- Save ~₹7,600
- ₹31,395
- usually about ₹39,000
- "About" and "~" whenever the usual price is an estimate.
- 6 · Long lists
- After 12 cards, load the rest on request instead of one endless page.
- Showing 12 of 31 deals
- Show more deals
- 7 · Phone: offline
- A slim bar on top of the last copy, so saved deals still open.
- You're offline · last update 09:40
- Retry
- BOM → BAH
- GOX → BKK
- 8 · Deal link no longer exists
- An old shared link or an email from months ago. Send people somewhere useful.
- This deal is long gone
- Fares like it come back. Here's what's cheap from your cities today.
- See today's deals

### Dark mode sheet

**DarkMode**

- Colour tokens, light → dark
- Each light colour gets its own dark step, chosen separately and not inverted. Every text pairing below is at least 4.5:1. The orange accent and the layout stay the same in both themes.
- {{t.name}}
- {{t.light}}
- {{t.dark}}
- {{t.note}}
- Deals
- Saved
- My alerts
- 6 fares well under their usual price
- All my cities
- Mumbai
- Goa
- {{c.to}}
- from {{c.from}}
- {{c.price}}
- {{c.usual}}
- Save {{c.save}}
- {{c.dates}}
- {{c.kind}}
- {{c.fresh}}
- See deal
- Prices were last checked 2 days ago. Check before you book.
- BOM → SGN
- Price checked twice
- Ho Chi Minh City
- from Mumbai · 5–11 Apr · 6 nights
- ₹25,218
- ₹35,948
- You save ₹10,730 (30%)
- Where this price sits
- Normal for these dates: ₹30,500–44,000
- Airline
- Vietjet
- Stops
- Non-stop both ways
- Book for ₹25,218
- ; color:
- Page background
- Ground behind everything
- Card surface
- Cards, header, sheets
- Divider
- Borders and rules
- Text
- 14:1 on dark cards
- Secondary text
- 6.9:1 on dark cards
- Accent (links, Plus)
- 6.7:1 on dark cards
- Saving pill
- Text #F5A877, 7.6:1
- Good / live
- Text #7BD3A2, 7.9:1
- Warning
- Text #F2C66B, 9:1
- Primary button
- Flips to light with dark text
- Chip, selected
- Text #4FB3AC, 5.6:1
- Brand orange
- Same in both themes
- Bahrain
- ₹20,231
- ₹31,298
- ₹11,067
- 14–18 Apr
- Short break
- Checked 2 h ago
- Bangkok
- ₹35,232
- ₹53,679
- ₹18,447
- 3–22 Dec
- Long holiday
- Checked 40 min ago
