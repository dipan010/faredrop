// C13. Variants:
//   feed    desktop feed card (save, tags, group, freshness, Not interested, See deal)
//   compact phone feed row (whole row is the link)
//   mini    landing "recent deals" tile
//   teaser  landing hero card
//   row     ended page "still live" row
// Interactive bits (save, hide) take handlers; rendered from .astro without
// a client: directive they are inert, so pages wrap it in an island.
import type { SnapshotDeal } from '../data/types';
import { dateRange, flightLine, inr, nightsLabel, pct, stopsShort, tripKind, TRIP_LABEL } from '../data/format';
import { destCity, originCity } from '../data/places';
import { Bookmark } from './icons';
import { DateChips, Freshness, PriceBlock, SavingPill, type SiblingDate } from './Price';

export type DealCardVariant = 'feed' | 'compact' | 'mini' | 'teaser' | 'row';
export interface DealCardProps {
  deal: SnapshotDeal;
  variant?: DealCardVariant;
  now: Date;
  href?: string;
  group?: SiblingDate[];
  saved?: boolean;
  onToggleSave?: () => void;
  onHide?: () => void;
  headingLevel?: 2 | 3;
}

export default function DealCard({ deal: d, variant = 'feed', now, href, group = [], saved, onToggleSave, onHide, headingLevel = 3 }: DealCardProps) {
  const to = destCity(d.destination);
  const from = originCity(d.origin);
  const link = href ?? `/deals/${d.deal_id}`;
  const est = !!d.usual_is_estimate;
  const H = (`h${headingLevel}` as 'h2' | 'h3');

  if (variant === 'compact') {
    return (
      <a class="fd-card fd-deal--compact" href={link}>
        <span class="fd-deal__main">
          <span class="fd-deal__route">{d.origin} → {d.destination}</span>
          <span class="fd-deal__meta">{to} · {dateRange(d.depart_date, d.return_date)} · {flightLine(d)}</span>
        </span>
        <span class="fd-deal__side">
          <span class="fd-deal__price">{inr(d.price)}</span>
          <span class="fd-deal__pct">−{pct(d.saving_pct)}% vs usual</span>
        </span>
      </a>
    );
  }

  if (variant === 'mini') {
    return (
      <div class="fd-card fd-deal--mini">
        <div class="fd-deal__from">{from} → </div>
        <H class="fd-deal__city">{to}</H>
        <PriceBlock price={d.price} usual={d.usual} estimate={est} variant="mini" />
        <SavingPill saving={d.saving} pct={d.saving_pct} format="off" />
      </div>
    );
  }

  if (variant === 'teaser') {
    // The bar shows the price as a share of the usual (canvas: 70%).
    const w = d.usual ? Math.round((d.price / d.usual) * 100) : 100;
    return (
      <div class="fd-card fd-deal--teaser">
        <div class="fd-deal__new"><span class="fd-fresh__dot" aria-hidden="true" />New deal · just now</div>
        <div>
          <div class="fd-deal__city">{to}</div>
          <div class="fd-deal__from">from {from} · {stopsShort(d.stops)} · {dateRange(d.depart_date, d.return_date)}</div>
        </div>
        <PriceBlock price={d.price} usual={d.usual} estimate={est} variant="hero" />
        <div class="fd-teaser-bar" aria-hidden="true"><span style={`width: ${w}%`} /></div>
        <div class="fd-deal__foot2">
          <SavingPill saving={d.saving} pct={d.saving_pct} format="you-save" size="lg" />
          <a class="fd-deal__book" href={link}>Book →</a>
        </div>
      </div>
    );
  }

  if (variant === 'row') {
    return (
      <a class="fd-card fd-deal--row" href={link}>
        <span class="fd-deal__titles">
          <span class="fd-deal__city">{to}</span>
          <span class="fd-deal__from">from {from} · {dateRange(d.depart_date, d.return_date)}</span>
        </span>
        <strong>{inr(d.price)}</strong>
      </a>
    );
  }

  return (
    <article class="fd-card fd-deal">
      <div class="fd-deal__top">
        <div class="fd-deal__titles">
          <H class="fd-deal__city">{to}</H>
          <div class="fd-deal__from">from {from} · {d.origin} → {d.destination}</div>
        </div>
        <button
          type="button"
          class="fd-save-btn"
          aria-pressed={saved ? 'true' : 'false'}
          aria-label={`Save ${from} to ${to}`}
          onClick={onToggleSave}
        >
          <Bookmark />
        </button>
      </div>
      <PriceBlock price={d.price} usual={d.usual} estimate={est}>
        <SavingPill saving={d.saving} pct={d.saving_pct} push estimate={est} />
      </PriceBlock>
      <div class="fd-tags">
        <span class="fd-tag">{dateRange(d.depart_date, d.return_date)}</span>
        <span class="fd-tag">{nightsLabel(d.nights)}</span>
        {flightLine(d) && <span class="fd-tag">{flightLine(d)}</span>}
        <span class="fd-tag fd-tag--accent">{TRIP_LABEL[tripKind(d.nights)]}</span>
      </div>
      <DateChips dates={group} />
      <div class="fd-deal__foot">
        <Freshness checkedAt={d.checked_at} now={now} stale={d.status === 'stale'} />
        <button type="button" class="fd-btn fd-btn--quiet" onClick={onHide}>Not interested</button>
        <a class="fd-btn fd-btn--primary fd-btn--40" href={link} aria-label={`See deal: ${from} to ${to}`}>See deal</a>
      </div>
    </article>
  );
}
