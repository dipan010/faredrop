// Checks web/src/styles/tokens.css against the token table in
// docs/ui-spec.md §3.1 (generated from the canvas), and checks contrast.
// axe only checks text contrast, so the 3:1 non-text rule for --faint
// borders (WCAG 1.4.11, gap G31) is checked here.
import { readFileSync } from 'node:fs';

const root = new URL('../../', import.meta.url);
const spec = readFileSync(new URL('docs/ui-spec.md', root), 'utf8');
const css = readFileSync(new URL('web/src/styles/tokens.css', root), 'utf8');

// Deliberate differences from the canvas, each with its gap.
const OVERRIDES = { light: { '--faint': '#82858C' } }; // G31

const want = {};
for (const m of spec.matchAll(/^\| `(--[\w-]+)` \| `(#\w{6})` \| `(#\w{6})` \|/gm)) {
  want[m[1]] = { light: m[2], dark: m[3] };
}

function block(re) {
  const m = css.match(re);
  if (!m) throw new Error('block not found: ' + re);
  return Object.fromEntries([...m[1].matchAll(/(--[\w-]+):\s*(#\w{6})/g)].map((x) => [x[1], x[2]]));
}
const got = {
  light: block(/:root,\s*\[data-theme="light"\]\s*\{([^}]*)\}/),
  darkMedia: block(/:root:not\(\[data-theme="light"\]\)\s*\{([^}]*)\}/),
  dark: block(/:root\[data-theme="dark"\],\s*\[data-theme="dark"\]\s*\{([^}]*)\}/),
};

let fail = 0;
const bad = (msg) => { fail++; console.error('FAIL ' + msg); };
for (const [k, v] of Object.entries(want)) {
  const l = OVERRIDES.light[k] ?? v.light;
  if (got.light[k]?.toUpperCase() !== l.toUpperCase()) bad(`${k} light ${got.light[k]} != ${l}`);
  for (const b of ['dark', 'darkMedia']) {
    if (got[b][k]?.toUpperCase() !== v.dark.toUpperCase()) bad(`${k} ${b} ${got[b][k]} != ${v.dark}`);
  }
}
if (Object.keys(want).length !== 36) bad(`expected 36 spec tokens, found ${Object.keys(want).length}`);

function lum(hex) {
  const c = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
    .map((x) => (x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4));
  return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
}
const ratio = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };

// [foreground, background, minimum]
const PAIRS = [
  ['--ink', '--bg', 4.5], ['--ink', '--surface', 4.5], ['--ink2', '--surface', 4.5],
  ['--muted', '--surface', 4.5], ['--muted', '--bg', 4.5], ['--muted2', '--surface', 4.5],
  ['--accent', '--surface', 4.5], ['--accent', '--bg', 4.5], ['--surface', '--accent', 4.5],
  ['--surface', '--ink', 4.5], ['--accent', '--accent-bg', 4.5], ['--accent-hover', '--surface', 4.5],
  ['--save', '--save-bg', 4.5], ['--eyebrow', '--bg', 4.5], ['--good', '--good-bg', 4.5],
  ['--good', '--surface', 4.5], ['--warn', '--warn-bg', 4.5], ['--bad', '--bad-bg', 4.5],
  ['--band-muted', '--ink', 4.5],
  // non-text: checkbox/radio borders and the large "→" glyph, on every surface they sit on
  ['--faint', '--surface', 3], ['--faint', '--bg', 3], ['--faint', '--surface2', 3], ['--faint', '--chip', 3],
];
for (const theme of ['light', 'dark']) {
  for (const [f, b, min] of PAIRS) {
    const r = ratio(got[theme][f], got[theme][b]);
    const line = `${theme.padEnd(5)} ${f} on ${b}: ${r.toFixed(2)} (min ${min})`;
    if (r < min) bad(line); else if (process.argv.includes('-v')) console.log('ok   ' + line);
  }
}

if (fail) { console.error(`${fail} failure(s)`); process.exit(1); }
console.log(`tokens ok: ${Object.keys(want).length} tokens x 3 blocks match the spec; ${PAIRS.length * 2} contrast pairs pass`);
