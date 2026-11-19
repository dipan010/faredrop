// C14 PriceBlock, C15 SavingPill, C16 Freshness, C17 DateChips.
import type { ComponentChildren } from 'preact';
import { checkedLabel, dateRange, inr, isFresh, savingText, usualText, type SavingFormat } from '../data/format';

export function SavingPill({ saving, pct, format = 'save', size, push, estimate }: {
  saving: number; pct: number; format?: SavingFormat; size?: 'lg'; push?: boolean; estimate?: boolean;
}) {
  // Estimates round the saving to the nearest ₹100 and add "~" (States board 5).
  const text = estimate && format === 'save' ? `Save ~${inr(Math.round(saving / 100) * 100)}` : savingText(saving, pct, format);
  return <span class={'fd-pill' + (size ? ' fd-pill--lg' : '') + (push ? ' fd-pill--push' : '')}>{text}</span>;
}

export type PriceVariant = 'card' | 'large' | 'hero' | 'phone' | 'mini' | 'inline';
export function PriceBlock({ price, usual, estimate, variant = 'card', saving, pct, children }: {
  price: number; usual: number | null; estimate?: boolean; variant?: PriceVariant;
  saving?: number; pct?: number; children?: ComponentChildren;
}) {
  if (variant === 'large') {
    return (
      <div class="fd-price fd-price--large">
        <div class="fd-price__now">{inr(price)}</div>
        {usual != null && saving != null && pct != null && (
          <div class="fd-price__below">
            <strong>{inr(saving)} ({Math.round(pct)}%) below</strong>{' '}
            <span class="fd-muted">the {estimate ? 'estimated ' : ''}usual {usualText(usual, !!estimate)}</span>
          </div>
        )}
      </div>
    );
  }
  const strike = variant === 'hero' || variant === 'phone' || variant === 'mini';
  return (
    <div class={`fd-price fd-price--${variant}`}>
      <span class="fd-price__now">{inr(price)}</span>
      {usual != null && (strike
        ? <s class="fd-price__usual">{usualText(usual, !!estimate)}</s>
        : <span class="fd-price__usual">{estimate ? <>usually about {inr(usual)}</> : <>usually <s>{inr(usual)}</s></>}</span>)}
      {children}
    </div>
  );
}

export function Freshness({ checkedAt, now, stale }: { checkedAt: string; now: Date; stale?: boolean }) {
  const fresh = isFresh(checkedAt, now);
  return (
    <span class={'fd-fresh' + (fresh ? '' : ' fd-fresh--old') + (stale ? ' fd-fresh--stale' : '')}>
      <span class="fd-fresh__dot" aria-hidden="true" />
      {checkedLabel(checkedAt, now)}
    </span>
  );
}

export interface SiblingDate { depart_date: string; return_date: string; href?: string }
export function DateChips({ dates, title, variant = 'card' }: { dates: SiblingDate[]; title?: string; variant?: 'card' | 'page' }) {
  if (!dates.length) return null;
  const t = title ?? (variant === 'card'
    ? `Also this cheap on ${dates.length} other date${dates.length > 1 ? 's' : ''}`
    : 'Also this cheap on');
  const chips = (
    <div class={'fd-tags' + (variant === 'page' ? ' fd-datechips--lg' : '')}>
      {dates.map((d) => {
        const label = dateRange(d.depart_date, d.return_date);
        return d.href ? <a class="fd-datechip" href={d.href}>{label}</a> : <span class="fd-datechip">{label}</span>;
      })}
    </div>
  );
  if (variant === 'page') {
    return <section class="fd-stack-8"><h2 style="font-size: 15px; font-weight: 600">{t}</h2>{chips}</section>;
  }
  return <div class="fd-group"><div class="fd-group__title">{t}</div>{chips}</div>;
}
