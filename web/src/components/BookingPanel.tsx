// C21. Desktop: "Book this fare" expands an inline "Where to book" panel.
// Phone: a bottom sheet, role="dialog" aria-modal, with a focus trap,
// Escape to close and focus returned to the opener.
// The airline-site row is off by default: gap G9 proposes dropping it
// (we have no airline deep link); `airlineLink` shows the canvas version.
import { useLayoutEffect, useRef, useState } from 'preact/hooks';
import type { SnapshotDeal } from '../data/types';
import { inr } from '../data/format';
import { Close } from './icons';

const GOOGLE = 'https://www.google.com/travel/flights';

function Links({ deal, airlineLink, sheet, compareHref }: { deal: SnapshotDeal; airlineLink?: boolean; sheet?: boolean; compareHref: string }) {
  return (
    <>
      {airlineLink && deal.airline_name && (
        <a class="fd-book__link" href={compareHref} target="_blank" rel="noopener"><span>{deal.airline_name} (airline site)</span>{sheet ? <strong>{inr(deal.price)}</strong> : <span style="font-weight: 600">{inr(deal.price)}</span>}</a>
      )}
      <a class="fd-book__link" href={compareHref} target="_blank" rel="noopener">
        <span>Compare on Google Flights</span><span class="fd-muted" style={sheet ? 'font-size: 13px' : undefined}>{sheet ? 'new tab' : 'opens a new tab'}</span>
      </a>
      <span class="fd-small">{sheet ? 'Gone when you get there?' : 'Price gone when you get there?'} <a href={`/deals/${deal.deal_id}#gone`}>Tell us</a>{sheet ? '' : " and we'll mark it."}</span>
    </>
  );
}

export default function BookingPanel({ deal, variant = 'inline', airlineLink = false, compareHref = GOOGLE, initialOpen = false, contained = false }: {
  deal: SnapshotDeal; variant?: 'inline' | 'sheet'; airlineLink?: boolean; compareHref?: string; initialOpen?: boolean;
  /** gallery only: keep the sheet inside its frame instead of the viewport */
  contained?: boolean;
}) {
  const [open, setOpen] = useState(initialOpen);
  const opener = useRef<HTMLButtonElement>(null);
  const sheet = useRef<HTMLDivElement>(null);

  useLayoutEffect(() => {
    if (!open || variant !== 'sheet') return;
    const el = sheet.current!;
    const focusables = () => Array.from(el.querySelectorAll<HTMLElement>('a[href], button'));
    focusables()[0]?.focus();
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') { setOpen(false); return; }
      if (e.key !== 'Tab') return;
      const f = focusables();
      const first = f[0], last = f[f.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last?.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first?.focus(); }
    };
    document.addEventListener('keydown', onKey);
    return () => { document.removeEventListener('keydown', onKey); opener.current?.focus(); };
  }, [open, variant]);

  if (variant === 'sheet') {
    return (
      <>
        <button ref={opener} type="button" class="fd-btn fd-btn--primary fd-btn--52" style="flex: 1; border-radius: 12px" aria-haspopup="dialog" onClick={() => setOpen(true)}>
          Book for {inr(deal.price)}
        </button>
        {open && (
          <div class={'fd-sheet-backdrop' + (contained ? ' fd-sheet-backdrop--contained' : '')} onClick={(e) => { if (e.target === e.currentTarget) setOpen(false); }}>
            <div ref={sheet} role="dialog" aria-modal="true" aria-label="Where to book" class="fd-sheet">
              <div class="fd-sheet__head">
                <span class="fd-sheet__title">Where to book</span>
                <button type="button" class="fd-icon-btn" aria-label="Close" onClick={() => setOpen(false)}><Close /></button>
              </div>
              <Links deal={deal} airlineLink={airlineLink} sheet compareHref={compareHref} />
            </div>
          </div>
        )}
      </>
    );
  }
  return (
    <>
      <button type="button" class="fd-btn fd-btn--primary" aria-expanded={open ? 'true' : 'false'} onClick={() => setOpen(!open)}>Book this fare</button>
      {open && (
        <div class="fd-book">
          <span class="fd-book__title">Where to book</span>
          <Links deal={deal} airlineLink={airlineLink} compareHref={compareHref} />
        </div>
      )}
    </>
  );
}
