// C11. checkbox cards (regions; aria-pressed) or radio cards (channels,
// unsubscribe, billing plan; role=radio in a radiogroup with arrow keys).
import { useRef, useState } from 'preact/hooks';
import { Tick } from './icons';

export interface Option { value: string; label: string; sub?: string }

export default function OptionCards({ label, options, control = 'checkbox', initial = [], columns = 'auto', onChange }: {
  label: string; options: Option[]; control?: 'checkbox' | 'radio'; initial?: string[];
  columns?: 'auto' | 'one'; onChange?: (v: string[]) => void;
}) {
  const [sel, setSel] = useState<string[]>(initial);
  const refs = useRef<(HTMLButtonElement | null)[]>([]);
  const set = (v: string[]) => { setSel(v); onChange?.(v); };
  const style = columns === 'one' ? 'grid-template-columns: 1fr; gap: 8px' : undefined;

  if (control === 'radio') {
    const idx = Math.max(0, options.findIndex((o) => sel.includes(o.value)));
    const move = (i: number) => {
      const j = (i + options.length) % options.length;
      set([options[j]!.value]);
      refs.current[j]?.focus();
    };
    return (
      <div role="radiogroup" aria-label={label} class="fd-options" style={style}>
        {options.map((o, i) => {
          const on = sel.includes(o.value);
          return (
            <button
              ref={(el) => { refs.current[i] = el; }}
              type="button"
              role="radio"
              class="fd-option"
              aria-checked={on ? 'true' : 'false'}
              tabIndex={i === idx ? 0 : -1}
              onClick={() => set([o.value])}
              onKeyDown={(e) => {
                if (e.key === 'ArrowDown' || e.key === 'ArrowRight') { e.preventDefault(); move(i + 1); }
                if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') { e.preventDefault(); move(i - 1); }
              }}
            >
              <span class="fd-option__text"><span class="fd-option__label">{o.label}</span>{o.sub && <span class="fd-option__sub">{o.sub}</span>}</span>
              <span class="fd-option__dot" aria-hidden="true" />
            </button>
          );
        })}
      </div>
    );
  }
  return (
    <div role="group" aria-label={label} class="fd-options" style={style}>
      {options.map((o) => {
        const on = sel.includes(o.value);
        return (
          <button type="button" class="fd-option" aria-pressed={on ? 'true' : 'false'} onClick={() => set(on ? sel.filter((x) => x !== o.value) : [...sel, o.value])}>
            <span class="fd-option__text"><span class="fd-option__label">{o.label}</span>{o.sub && <span class="fd-option__sub">{o.sub}</span>}</span>
            <span class="fd-option__box" aria-hidden="true">{on && <Tick size={14} color="var(--surface)" width={2.2} />}</span>
          </button>
        );
      })}
    </div>
  );
}
