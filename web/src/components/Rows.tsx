// C28 SavedRow / WatchRow / PriceChange notice (Saved page, States board 4).
import type { SnapshotDeal } from '../data/types';
import { dateRange, flightLine, inr, nightsLabel } from '../data/format';
import { destCity, originCity } from '../data/places';

export function SavedRow({ deal: d, note, href, onRemove }: { deal: SnapshotDeal; note: string; href?: string; onRemove?: () => void }) {
  const title = `${originCity(d.origin)} → ${destCity(d.destination)}`;
  const ended = d.status === 'ended';
  const meta = [dateRange(d.depart_date, d.return_date), nightsLabel(d.nights), flightLine(d)].filter(Boolean).join(' · ');
  return (
    <div class={'fd-saved' + (ended ? ' fd-saved--ended' : '')}>
      <a class="fd-saved__main" href={href ?? `/deals/${d.deal_id}`}>
        <span class="fd-saved__title">{title}</span>
        <span class="fd-saved__meta">{meta}</span>
        <span class="fd-saved__note">{note}</span>
      </a>
      <div class="fd-saved__side">
        <span class="fd-saved__price">{ended && <span class="visually-hidden">Was </span>}{inr(d.price)}</span>
        <button type="button" class="fd-saved__remove" aria-label={`Remove ${title}`} onClick={onRemove}>Remove</button>
      </div>
    </div>
  );
}

export function WatchRow({ route, status, target }: { route: string; status: string; target: number }) {
  return (
    <div class="fd-watchrow">
      <span class="fd-watchrow__text"><span class="fd-watchrow__route">{route}</span><span class="fd-watchrow__status">{status}</span></span>
      <span class="fd-watchrow__target">under <strong>{inr(target)}</strong></span>
    </div>
  );
}

/** "Up ₹871 since our alert." / "Down another ₹1,421 since our alert." */
export function PriceChange({ was, now, similarHref }: { was: number; now: number; similarHref?: string }) {
  const up = now > was;
  return (
    <div class={'fd-change' + (up ? '' : ' fd-change--down')}>
      {up ? (
        <><strong>Up {inr(now - was)} since our alert.</strong> It's now inside the normal price range, so it's no longer a deal. {similarHref && <a href={similarHref}>See similar deals</a>}</>
      ) : (
        <><strong>Down another {inr(was - now)}</strong> since our alert. Even better now.</>
      )}
    </div>
  );
}
