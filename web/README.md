# web/ — the faredrop product site

Astro (static) + Preact islands + TypeScript + plain CSS. Built from
`docs/ui-spec.md`; data types follow `docs/lld.md`. The Node toolchain lives
only in this folder.

## Commands (run inside `web/`)

```bash
npm ci                       # exact versions from package-lock.json
npm run dev                  # http://localhost:4321/dev/components/
npm run tokens               # tokens.css matches spec §3.1; contrast pairs (incl. 3:1 non-text) pass
npm run check                # astro check: TypeScript across .astro/.ts/.tsx
npx playwright install chromium   # once
npm test                     # builds, serves dist/, runs Playwright + axe
```

Astro telemetry is off in every script (`ASTRO_TELEMETRY_DISABLED=1`).
`npm test` serves `dist/` with `scripts/serve.mjs`, not `astro preview`,
because Astro 7's preview detaches into the background without a terminal.

## Layout

- `src/styles/tokens.css`: colour tokens (light on `:root`, dark under the
  system preference unless light is forced, and on any `[data-theme=dark]`),
  type, spacing, radii. `base.css`: element styles, fonts, focus ring.
  `components.css`: every component's classes (`fd-` prefix).
- `src/components/`: C1–C31 from spec §4. Page chrome (Logo, SiteHeader,
  PhoneTabBar, Footer, Stepper, EmailShell) is `.astro`. Everything a
  client-side page might render (cards, prices, banners…) is Preact `.tsx`:
  it ships no JS unless a page adds a `client:` directive (gap G49).
- `src/data/`: LLD types, formatting rules (spec §2), the fixture adapter
  (reads `docs/fixtures/snapshot.sample.json`, validated at build time, clock
  pinned to `generated_at`) and the real adapter stub (phase 4).
- `src/pages/dev/components.astro`: the gallery; every component in a light
  and a dark panel.
- `tests/gallery.spec.ts`: axe at 390 and 1440 px in both page themes, the
  email preview, the theme switch, and the booking sheet's focus trap.

## Free limits we rely on

Cloudflare Pages, Free plan (developers.cloudflare.com/pages/platform/limits,
read 2026-11-19): 500 builds a month, 1 build at a time, 20-minute build
timeout, 20,000 files per site, 25 MiB per file, 100 custom domains per
project, 100 projects per account. The page states no bandwidth or
static-request limit. Pages Functions count against the Workers free quota;
this site uses none yet. GitHub Actions: the `web` job in
`.github/workflows/check.yml` runs on the free public-repo minutes.

Fonts: Inter and Space Grotesk via `@fontsource` (SIL OFL 1.1), bundled into
the build, so no third party sees visits (G32).
