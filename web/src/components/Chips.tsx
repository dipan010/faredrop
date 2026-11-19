// C6 ToggleChip and ChipGroup (island). Modes:
//   single  one pressed at a time (feed city filter)
//   multi   any number, up to max; at max the rest are aria-disabled and a
//           note says why (setup: Free 1 city, Plus 5)
//   filter  single, with counts (ops feedback)
//   vote    single, accent style (email verdict preview, ops)
import { useState } from 'preact/hooks';

export interface ChipProps {
  label: string;
  pressed: boolean;
  onToggle?: () => void;
  count?: number;
  size?: 40 | 44;
  vote?: boolean;
  disabled?: boolean;
}
export function ToggleChip({ label, pressed, onToggle, count, size = 40, vote, disabled }: ChipProps) {
  return (
    <button
      type="button"
      class={'fd-chip' + (size === 44 ? ' fd-chip--44' : '') + (vote ? ' fd-chip--vote' : '')}
      aria-pressed={pressed ? 'true' : 'false'}
      aria-disabled={disabled ? 'true' : undefined}
      onClick={disabled ? undefined : onToggle}
    >
      {label}
      {count != null && <span class="fd-chip__n">{count}</span>}
    </button>
  );
}

export interface ChipGroupProps {
  label: string;
  options: { value: string; label: string; count?: number }[];
  mode?: 'single' | 'multi' | 'filter' | 'vote';
  initial?: string[];
  max?: number;
  maxNote?: string;
  size?: 40 | 44;
  onChange?: (v: string[]) => void;
}
export default function ChipGroup({ label, options, mode = 'single', initial = [], max, maxNote, size = 40, onChange }: ChipGroupProps) {
  const [sel, setSel] = useState<string[]>(initial);
  const multi = mode === 'multi';
  const atMax = multi && max != null && sel.length >= max;
  const set = (v: string[]) => { setSel(v); onChange?.(v); };
  return (
    <div role="group" aria-label={label} class="fd-chips">
      {options.map((o) => {
        const on = sel.includes(o.value);
        return (
          <ToggleChip
            label={o.label}
            count={o.count}
            size={size}
            vote={mode === 'vote'}
            pressed={on}
            disabled={atMax && !on}
            onToggle={() => set(multi ? (on ? sel.filter((x) => x !== o.value) : [...sel, o.value]) : on && mode === 'vote' ? [] : [o.value])}
          />
        );
      })}
      {atMax && maxNote && <span class="fd-chip-note" role="status">{maxNote}</span>}
    </div>
  );
}

/** Removable city chip (My alerts "I fly from"). */
export function RemovableChip({ label, onRemove }: { label: string; onRemove?: () => void }) {
  return (
    <span class="fd-chip fd-chip--removable">
      {label}
      <button type="button" class="fd-chip__x" aria-label={`Remove ${label}`} onClick={onRemove}>
        <svg width="12" height="12" viewBox="0 0 16 16" aria-hidden="true"><path style="stroke: var(--surface)" d="M4 4l8 8M12 4l-8 8" stroke-width="2" stroke-linecap="round" /></svg>
      </button>
    </span>
  );
}
