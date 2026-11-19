// C30 (gap G33): cycles system → light → dark. Stored in localStorage
// under faredrop.theme, wrapped in try/catch (private windows can throw).
import { useEffect, useState } from 'preact/hooks';
import { Auto, Moon, Sun } from './icons';

type Mode = 'system' | 'light' | 'dark';
const KEY = 'faredrop.theme';
const NEXT: Record<Mode, Mode> = { system: 'light', light: 'dark', dark: 'system' };
const LABEL: Record<Mode, string> = {
  system: 'Theme: same as device. Switch to light',
  light: 'Theme: light. Switch to dark',
  dark: 'Theme: dark. Switch to same as device',
};

function read(): Mode {
  try {
    const v = localStorage.getItem(KEY);
    return v === 'light' || v === 'dark' ? v : 'system';
  } catch {
    return 'system';
  }
}
export function applyTheme(m: Mode) {
  const el = document.documentElement;
  if (m === 'system') el.removeAttribute('data-theme');
  else el.setAttribute('data-theme', m);
  try {
    if (m === 'system') localStorage.removeItem(KEY);
    else localStorage.setItem(KEY, m);
  } catch {
    /* storage blocked: the choice lasts for this page only */
  }
}

export default function ThemeSwitch() {
  const [mode, setMode] = useState<Mode>('system');
  useEffect(() => setMode(read()), []);
  const Icon = mode === 'light' ? Sun : mode === 'dark' ? Moon : Auto;
  return (
    <button
      type="button"
      class="fd-theme-btn"
      aria-label={LABEL[mode]}
      title={LABEL[mode]}
      onClick={() => {
        const m = NEXT[mode];
        applyTheme(m);
        setMode(m);
      }}
    >
      <Icon />
    </button>
  );
}
