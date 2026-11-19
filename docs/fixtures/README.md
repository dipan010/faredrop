# Fixtures

`snapshot.sample.json` is a product snapshot shaped exactly like `docs/lld.md`
section 3. It holds the seven real Google-confirmed deals the design canvas
shows, so phases 1–2 can build pages before the exporter (phase 3) exists.
Phase 3's first real snapshot supersedes it.

Validate it with:

```bash
python3 tools/check_fixture.py
```

The validator reads keys, NOT NULL columns, the allowlist and the status rules
from `docs/lld.md`. It must report 0 failures; known gaps are listed by id.

## Where each value comes from

No value is estimated. Each comes from one of these sources, tried in order:
1. the canvas (https://claude.ai/artifact/GBnLGrXQ5L1bnpGKmnPGDr, version
   `1795082767-d03c`);
2. `STATUS.md` and `docs/history.md`;
3. a well-known fact (IATA airline codes);
4. `null` where the LLD allows null.

| Deal | Values and their sources |
|---|---|
| BOM-SGN 5–11 Apr 2027 | **Canvas:** price, usual, range 30,500–44,000, Vietjet, non-stop, dates; "Checked 5 h ago". **Feedback board / STATUS:** found and emailed 24 Oct. |
| GOX-BKK 3–22 Dec 2026 | **Canvas:** price, usual, IndiGo via Hyderabad, dates; "Checked 40 min ago". **STATUS 2026-11-14:** range 36,500–3,05,000; emailed 13 Nov. |
| CCU-FRA 24–28 Jan 2027 | **Canvas:** price, usual, Etihad via Abu Dhabi, no range; "Checked yesterday" (set to 24 h before `generated_at`). **STATUS:** emailed 31 Oct. Rated wrong by the owner on 15 Nov because a cheaper fare exists; it's kept because the canvas uses it as the no-range example. |
| BOM-BAH 14–18 Apr 2027 | **Canvas:** price, usual, Kuwait Airways, 1 stop; "Checked 2 h ago". **STATUS 2026-11-09:** via KWI, emailed 8 Nov. Range not shown → `null`. |
| BLR-SGN 10–26 Feb 2027 | **Canvas:** price, usual, Vietjet, non-stop; "Checked 1 h ago". **STATUS:** emailed 12 Nov. Range → `null`. |
| GOI-CMB 16–19 Jan 2027 | **Canvas:** price, usual `~₹39,000` (an estimate, States board section 5; the UI must say "about"), IndiGo, 1 stop; "Checked 3 h ago". **STATUS 2026-10-23:** emailed 23 Oct; usual ~₹39k. `via` is `null`: STATUS line 33 says the January GOI→CMB deals went via HYD, but line 38 has Jan 5–12 via MAA, so nothing pins 16–19 Jan to one airport. |
| GOI-DXB 1–15 Nov 2026 | **Canvas:** price, dates, 14 nights, "Deal ended". **`docs/history.md`:** Google's usual ₹38,609; emailed 17 Oct. Airline and stops aren't recorded anywhere → `null` (gap G35). `status = ended` because the departure has passed (LLD §2.3). `checked_at` is set to `detected_at`, the only check known. |

Other fields:
- **The fixture clock:** in fixture mode, the data adapter and the tests take
  "now" from `snapshot.generated_at` (2026-11-15T10:19:40Z), not the wall clock.
  Otherwise every render after 18 Nov shows "Checked 4+ days ago", the
  data-is-behind banner never goes away, "Leaves in N days" is wrong, and
  Playwright results change with the date.
- **`detected_at`:** the day the deal was emailed. The time of day isn't
  recorded, so it's `00:00:00Z`.
- **`checked_at`:** back-computed from the canvas's "Checked {age}" labels,
  relative to `generated_at = 2026-11-15T10:19:40Z`, the LLD's example.
  These are fixture timestamps, not real check times.
- **`saving` and `saving_pct`:** computed as `usual − price` and
  `(1 − price/usual) × 100`, rounded to 1 decimal. Every rounded percentage
  matches the canvas (30, 34, 26, 35, 20, 20).
- **`group_id`:** each deal is its own group. The canvas shows sibling dates for
  BOM-SGN (31 Mar–6 Apr, 1–8 Apr) and GOI-CMB (4–11, 7–12, 9–12, 16–23 and
  20–24 Jan) but not their prices, and a sibling would need a price. They're
  left out (gap G34).
- **`card_html`:** `null`. The exporter renders it in phase 3.
- **`pipeline`:** `last_gf_at` and `run_id` come from the LLD example.
  `gf_answered_today` (41) is from the LLD example and `gf_budget` (60) is the
  real budget since 14 Nov. `last_collect_at` isn't known, so it's `null`.
- **`route_prices`:** empty. No watched-route price appears on the canvas as a
  monthly minimum.

## Not included

- HYD-SHJ 17–20 Nov: it's on the landing and phone feed boards, but it isn't
  in the plan's fixture list, and it has already departed.
- GOX-SHJ and the other GOI-CMB dates: they appear only on the ops feedback
  board.

Add them only from real data.
