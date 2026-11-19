// C29 BarChart: focusable bars; hovering or focusing one writes its detail
// into a live region (OpsHealth board).
import { useState } from 'preact/hooks';

export interface Bar { label: string; day: string; value: number; detail: string }
export default function BarChart({ bars, rule = 75, ruleLabel = '75% line' }: { bars: Bar[]; rule?: number; ruleLabel?: string }) {
  const [text, setText] = useState('');
  const cols = `grid-template-columns: repeat(${bars.length}, minmax(0, 1fr))`;
  return (
    <>
      <div class="fd-chart">
        <div class="fd-chart__y" aria-hidden="true"><span>100%</span><span>75%</span><span>50%</span><span>25%</span><span>0%</span></div>
        <div class="fd-chart__plot">
          <div class="fd-chart__rule" style={`top: ${100 - rule}%`} />
          <span class="fd-chart__rule-lbl" style={`top: calc(${100 - rule}% - 18px)`} aria-hidden="true">{ruleLabel}</span>
          <div class="fd-chart__bars" style={cols}>
            {bars.map((b) => (
              <button type="button" class="fd-chart__bar" aria-label={`${b.label}: ${b.detail}`} onMouseEnter={() => setText(b.detail)} onFocus={() => setText(b.detail)} onMouseLeave={() => setText('')}>
                <span class="fd-chart__val" aria-hidden="true">{b.label}</span>
                <span class="fd-chart__fill" style={`height: ${b.value}%`} />
              </button>
            ))}
          </div>
        </div>
        <div class="fd-chart__x" style={cols} aria-hidden="true">{bars.map((b) => <span>{b.day}</span>)}</div>
      </div>
      <div role="status" class="fd-chart__live">{text}</div>
    </>
  );
}
