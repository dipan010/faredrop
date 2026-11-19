// C18. Where the price sits against Google's typical range.
//   range   full bar: track, normal band, usual tick, deal dot
//   broken  range_high far above the rest: the scale is cut, the band runs
//           off the end with an arrow (GOX-BKK board)
//   none    no range: two plain comparison bars (CCU-FRA board)
// variant is picked from the data unless forced. Scale rule (gap G46):
// it reproduces both canvas boards' scales (20,000–48,000 and the
// 30,000–60,000 cut).
import { inr } from '../data/format';
import { ScaleArrow } from './icons';

export type RangeVariant = 'range' | 'broken' | 'none';
export interface PriceRangeBarProps {
  price: number;
  usual: number | null;
  rangeLow: number | null;
  rangeHigh: number | null;
  variant?: RangeVariant;
  compact?: boolean; // phone
}

const ceilTo = (v: number, s: number) => Math.ceil(v / s) * s;
const floorTo = (v: number, s: number) => Math.floor(v / s) * s;

/** A range is "broken" when its top is over twice the usual price. */
export function rangeVariant(usual: number | null, low: number | null, high: number | null): RangeVariant {
  if (low == null || high == null || usual == null) return 'none';
  return high > usual * 2 ? 'broken' : 'range';
}

export function scaleFor(price: number, usual: number, high: number, broken: boolean) {
  const max = broken ? ceilTo(usual * 1.1, 5000) : ceilTo(high * 1.08, 2000);
  const min = floorTo(price - 0.18 * (max - price), 5000);
  return { min, max };
}

export default function PriceRangeBar(p: PriceRangeBarProps) {
  const v = p.variant ?? rangeVariant(p.usual, p.rangeLow, p.rangeHigh);
  if (v === 'none') {
    const usual = p.usual ?? p.price;
    const w = Math.round((p.price / usual) * 100);
    return (
      <div class="fd-compare" role="img" aria-label={`This deal ${inr(p.price)} against the usual ${inr(usual)}`}>
        <div class="fd-compare__row"><span class="fd-compare__name">Usual price</span><span class="fd-compare__bar" style="width: 100%" /><span class="fd-compare__val">{inr(usual)}</span></div>
        <div class="fd-compare__row"><span class="fd-compare__name">This deal</span><span class="fd-compare__bar fd-compare__bar--deal" style={`width: ${w}%`} /><span class="fd-compare__val fd-compare__val--deal">{inr(p.price)}</span></div>
      </div>
    );
  }
  const low = p.rangeLow!, high = p.rangeHigh!, usual = p.usual!;
  const broken = v === 'broken';
  const { min, max } = scaleFor(p.price, usual, high, broken);
  // In the broken bar, positions are over (100% − 24px), the arrow's room.
  const pos = (x: number) => {
    const f = Math.min(1, Math.max(0, (x - min) / (max - min)));
    return broken ? `calc((100% - 24px) * ${f.toFixed(4)})` : `${(f * 100).toFixed(1)}%`;
  };
  const label = `This deal ${inr(p.price)}. Usual ${inr(usual)}. Normal range ${inr(low)} to ${inr(high)}.`;
  const cls = 'fd-range' + (broken ? ' fd-range--broken' : '') + (p.compact ? ' fd-range--compact' : '');

  if (p.compact) {
    const mid = broken ? pos((low + max) / 2) : pos((low + high) / 2);
    return (
      <div class={cls} role="img" aria-label={label}>
        <div class="fd-range__track" />
        <div class="fd-range__band" style={`left: ${pos(low)}; ${broken ? 'right: 24px' : `width: calc(${pos(high)} - ${pos(low)})`}`} />
        <div class="fd-range__dot" style={`left: ${pos(p.price)}`} />
        <div class="fd-range__deal" style={`left: ${pos(p.price)}`}>this deal</div>
        <div class="fd-range__normal" style={`left: ${mid}`}>normal: {inr(low)}–{broken ? inr(high) : inr(high).slice(1)}</div>
      </div>
    );
  }
  return (
    <div class={cls} role="img" aria-label={label}>
      <div class="fd-range__track" />
      <div class="fd-range__band" style={`left: ${pos(low)}; ${broken ? 'right: 24px' : `width: calc(${pos(high)} - ${pos(low)})`}`} />
      {broken && <span class="fd-range__break"><ScaleArrow /></span>}
      <div class={'fd-range__lbl' + (broken ? ' fd-range__lbl--start' : '')} style={`left: ${pos(low)}`}>{inr(low)}<br /><span>cheapest normal</span></div>
      {broken
        ? <div class="fd-range__lbl fd-range__lbl--end">up to {inr(high)}<br /><span>long multi-airline trips</span></div>
        : <div class="fd-range__lbl" style={`left: ${pos(high)}`}>{inr(high)}<br /><span>priciest normal</span></div>}
      <div class="fd-range__usual" style={`left: ${pos(usual)}`} />
      <div class="fd-range__usual-lbl" style={`left: ${pos(usual)}`}>usual {inr(usual)}</div>
      <div class="fd-range__dot" style={`left: ${pos(p.price)}`} />
      <div class="fd-range__deal" style={`left: ${pos(p.price)}`}>
        {broken ? <>{inr(p.price)} this deal</> : <>{inr(p.price)}<br /><span>this deal</span></>}
      </div>
    </div>
  );
}
