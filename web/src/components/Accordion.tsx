// C27. One open at a time; aria-expanded on the button, +/− sign.
import { useId, useState } from 'preact/hooks';

export default function Accordion({ items, initial = 0 }: { items: { q: string; a: string }[]; initial?: number }) {
  const [open, setOpen] = useState(initial);
  const id = useId();
  return (
    <div class="fd-acc">
      {items.map((it, i) => (
        <div class="fd-acc__item">
          <h3 style="font-size: inherit">
            <button type="button" class="fd-acc__q" aria-expanded={open === i ? 'true' : 'false'} aria-controls={`${id}-${i}`} onClick={() => setOpen(open === i ? -1 : i)}>
              {it.q}<span class="fd-acc__sign" aria-hidden="true">{open === i ? '−' : '+'}</span>
            </button>
          </h3>
          <p class="fd-acc__a" id={`${id}-${i}`} hidden={open !== i}>{it.a}</p>
        </div>
      ))}
    </div>
  );
}
