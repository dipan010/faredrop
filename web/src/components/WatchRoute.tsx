// C22. States: form (input + button), watching (status + Stop), phone (one
// button with the suggested target), locked (Free: explains Plus).
import { useId, useState } from 'preact/hooks';
import { inr } from '../data/format';
import { destCity, originCity } from '../data/places';
import { Tick } from './icons';

export default function WatchRoute({ origin, destination, target, variant = 'form', locked = false, initialWatching = false }: {
  origin: string; destination: string; target: number; variant?: 'form' | 'phone'; locked?: boolean; initialWatching?: boolean;
}) {
  const [watching, setWatching] = useState(initialWatching);
  const [value, setValue] = useState(inr(target));
  const id = useId();
  const route = `${originCity(origin)} → ${destCity(destination)}`;
  const amount = variant === 'phone' ? inr(target) : value;

  const status = (
    <div role="status" class="fd-watching">
      {variant === 'form' && <Tick />}
      <span>Watching. We'll message you under {amount}.</span>
      {variant === 'form' && <button type="button" onClick={() => setWatching(false)}>Stop</button>}
    </div>
  );

  if (variant === 'phone') {
    return (
      <section class="fd-panel" style="padding: 16px; gap: 10px">
        <h2 style="font-size: 15px; font-weight: 600">Watch this route</h2>
        {locked ? <Locked /> : watching ? status : (
          <button type="button" class="fd-btn fd-btn--44" style="width: 100%; border: 1px solid var(--accent); background: var(--surface); color: var(--accent)" onClick={() => setWatching(true)}>
            Tell me if it drops under {inr(target)}
          </button>
        )}
      </section>
    );
  }
  return (
    <section class="fd-panel fd-panel--side" style="gap: 12px">
      <h2>Watch {route}</h2>
      <p class="fd-muted" style="font-size: 14px">Get an email the next time this route drops, even if it's not a top deal.</p>
      {locked ? <Locked /> : (
        <>
          <label class="fd-field" for={id}>Tell me when it's under</label>
          <input id={id} class="fd-input fd-input--44" style="border-radius: 8px; margin-top: -6px" type="text" inputMode="numeric" value={value} onInput={(e) => setValue((e.target as HTMLInputElement).value)} />
          {watching ? status : <button type="button" class="fd-btn fd-btn--accent fd-btn--44 fd-btn--block" onClick={() => setWatching(true)}>Watch this route</button>}
        </>
      )}
    </section>
  );
}

function Locked() {
  return (
    <div class="fd-locked">
      <span>Route watches are part of Plus.</span>
      <a class="fd-btn fd-btn--accent fd-btn--40" style="align-self: flex-start" href="/plus">See Plus</a>
    </div>
  );
}
