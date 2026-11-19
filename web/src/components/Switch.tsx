// C10. role="switch"; on --accent, off --switch-off; disabled when the
// plan doesn't include it (the reason goes in sub).
import { useState } from 'preact/hooks';

export function Switch({ label, checked, onChange, disabled }: { label: string; checked: boolean; onChange?: (v: boolean) => void; disabled?: boolean }) {
  return (
    <button
      type="button"
      role="switch"
      class="fd-switch"
      aria-checked={checked ? 'true' : 'false'}
      aria-label={label}
      disabled={disabled}
      onClick={() => onChange?.(!checked)}
    >
      <span class="fd-switch__knob" />
    </button>
  );
}

/** A settings row: label + sub on the left, the switch on the right. */
export default function SwitchRow({ label, sub, initial = false, disabled }: { label: string; sub?: string; initial?: boolean; disabled?: boolean }) {
  const [on, setOn] = useState(initial);
  return (
    <div class="fd-switch-row">
      <span class="fd-switch-row__text"><span class="fd-switch-row__label">{label}</span>{sub && <span class="fd-switch-row__sub">{sub}</span>}</span>
      <Switch label={label} checked={on} onChange={setOn} disabled={disabled} />
    </div>
  );
}
