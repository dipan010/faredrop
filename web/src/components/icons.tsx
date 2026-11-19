// The canvas's icons, paths copied from the boards. All decorative
// (aria-hidden); the control around them carries the label.
type P = { size?: number };

export const LogoMark = ({ size = 28 }: P) => (
  <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
    <rect style="fill: var(--ink)" width="28" height="28" rx="7" />
    <path style="stroke: var(--bg)" d="M8 9h12M8 14h8M8 19h4" stroke-width="2.2" stroke-linecap="round" />
    <path d="M20 15v6m0 0-2.5-2.5M20 21l2.5-2.5" stroke="#F08A4B" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" fill="none" />
  </svg>
);
export const Bookmark = ({ size = 20 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <path d="M5 3h10v14l-5-3.5L5 17V3Z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round" />
  </svg>
);
export const Bell = ({ size = 16 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <path d="M10 3a5 5 0 0 0-5 5v3l-1.5 2.5h13L15 11V8a5 5 0 0 0-5-5Zm-2 13a2 2 0 0 0 4 0" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round" />
  </svg>
);
export const List = ({ size = 20 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <path d="M3 5h14M3 10h10M3 15h6" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" />
  </svg>
);
export const ChevronLeft = ({ size = 16 }: P) => (
  <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
    <path d="M10 3 5 8l5 5" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
);
export const Share = ({ size = 20 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <path d="M10 3v10M6 7l4-4 4 4M4 12v4h12v-4" stroke="currentColor" stroke-width="1.7" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
);
export const Close = ({ size = 16, color = 'currentColor', width = 1.8 }: P & { color?: string; width?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
    <path d="M4 4l8 8M12 4l-8 8" style={`stroke: ${color}`} stroke-width={width} stroke-linecap="round" />
  </svg>
);
export const Tick = ({ size = 18, color = 'var(--good-dot)', width = 2 }: P & { color?: string; width?: number }) => (
  <svg width={size} height={size} viewBox="0 0 16 16" aria-hidden="true">
    <path style={`stroke: ${color}`} d="m3.5 8.2 3 3 6-6.4" stroke-width={width} fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
);
export const CheckCircle = ({ size = 22 }: P) => (
  <svg width={size} height={size} viewBox="0 0 22 22" aria-hidden="true">
    <circle style="fill: var(--good-bg)" cx="11" cy="11" r="10" />
    <path style="stroke: var(--good-dot)" d="m6.5 11.2 3 3 6-6.4" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
);
export const Alert = ({ size = 28 }: P) => (
  <svg width={size} height={size} viewBox="0 0 28 28" aria-hidden="true">
    <circle style="fill: var(--save-bg)" cx="14" cy="14" r="12" />
    <path style="stroke: var(--save)" d="M14 8v7M14 19v.5" stroke-width="2.4" stroke-linecap="round" />
  </svg>
);
export const Clock = ({ size = 18 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <circle style="stroke: var(--warn-icon)" cx="10" cy="10" r="8" stroke-width="1.8" fill="none" />
    <path style="stroke: var(--warn-icon)" d="M10 6v4.5l3 2" stroke-width="1.8" fill="none" stroke-linecap="round" />
  </svg>
);
export const Plane = ({ size = 72 }: P) => (
  <svg width={size} height={size} viewBox="0 0 72 72" aria-hidden="true">
    <circle style="fill: var(--accent-bg)" cx="36" cy="36" r="34" />
    <path style="stroke: var(--accent)" d="M22 42l28-14-8 22-6-8-14 0Z" stroke-width="2.4" fill="none" stroke-linejoin="round" />
    <path style="stroke: var(--accent)" d="M36 42l14-14" stroke-width="2.4" stroke-linecap="round" />
  </svg>
);
/* Not on the canvas (G33): sun, moon and half-disc for the theme switch. */
export const Sun = ({ size = 18 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <circle cx="10" cy="10" r="3.5" stroke="currentColor" stroke-width="1.6" fill="none" />
    <path d="M10 2v2M10 16v2M2 10h2M16 10h2M4.3 4.3l1.4 1.4M14.3 14.3l1.4 1.4M4.3 15.7l1.4-1.4M14.3 5.7l1.4-1.4" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" />
  </svg>
);
export const Moon = ({ size = 18 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <path d="M16 12.5A6.5 6.5 0 0 1 7.5 4a6.5 6.5 0 1 0 8.5 8.5Z" stroke="currentColor" stroke-width="1.6" fill="none" stroke-linejoin="round" />
  </svg>
);
export const Auto = ({ size = 18 }: P) => (
  <svg width={size} height={size} viewBox="0 0 20 20" aria-hidden="true">
    <circle cx="10" cy="10" r="7" stroke="currentColor" stroke-width="1.6" fill="none" />
    <path d="M10 3a7 7 0 0 1 0 14Z" fill="currentColor" />
  </svg>
);
/* The "scale continues" arrow at the cut end of a broken price bar (DealOneStop). */
export const ScaleArrow = () => (
  <svg width="22" height="22" viewBox="0 0 22 22" aria-hidden="true">
    <path style="stroke: var(--ink2)" d="M3 11h14m-5-6 6 6-6 6" stroke-width="2" fill="none" stroke-linecap="round" stroke-linejoin="round" />
  </svg>
);
