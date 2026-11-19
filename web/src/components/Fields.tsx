// C7 Select and C8 TextField: label above (or inline), 52 / 48 / 44 / 40 px.
import { useId } from 'preact/hooks';

type Size = 52 | 48 | 44 | 40;

export interface SelectProps {
  label: string;
  options: (string | { value: string; label: string })[];
  value?: string;
  size?: Size;
  inline?: boolean;
  hideLabel?: boolean;
  name?: string;
  onChange?: (v: string) => void;
}
export function Select({ label, options, value, size = 48, inline, hideLabel, name, onChange }: SelectProps) {
  return (
    <label class={'fd-field' + (inline ? ' fd-field--inline' : '')}>
      <span class={hideLabel ? 'visually-hidden' : undefined}>{label}</span>
      <select
        class={'fd-select' + (size !== 48 ? ` fd-select--${size}` : '')}
        name={name}
        value={value}
        onChange={(e) => onChange?.((e.target as HTMLSelectElement).value)}
      >
        {options.map((o) => (typeof o === 'string' ? <option>{o}</option> : <option value={o.value}>{o.label}</option>))}
      </select>
    </label>
  );
}

export interface TextFieldProps {
  label: string;
  type?: 'email' | 'text' | 'textarea' | 'number';
  placeholder?: string;
  value?: string;
  size?: Size;
  name?: string;
  error?: string;
  hint?: string;
  autocomplete?: string;
  inputMode?: 'numeric' | 'email' | 'text' | 'decimal';
  onInput?: (v: string) => void;
}
export function TextField({ label, type = 'text', placeholder, value, size = 48, name, error, hint, autocomplete, inputMode, onInput }: TextFieldProps) {
  const id = useId();
  const describedBy = [error && id + '-e', hint && id + '-h'].filter(Boolean).join(' ') || undefined;
  const common = {
    name, placeholder, value, autocomplete,
    'aria-invalid': error ? ('true' as const) : undefined,
    'aria-describedby': describedBy,
    onInput: (e: Event) => onInput?.((e.target as HTMLInputElement).value),
  };
  return (
    <label class="fd-field">
      {label}
      {type === 'textarea' ? (
        <textarea class="fd-textarea" {...common} />
      ) : (
        <input class={'fd-input' + (size !== 48 ? ` fd-input--${size}` : '')} type={type as 'email'} inputMode={inputMode} {...common} />
      )}
      {hint && <span class="fd-field__hint" id={id + '-h'}>{hint}</span>}
      {error && <span class="fd-field__error" id={id + '-e'}>{error}</span>}
    </label>
  );
}
