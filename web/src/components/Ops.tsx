// C29 StatTile and DataTable (ops pages, receipts). BarChart is an island
// (BarChart.tsx) because its bars announce on focus.
import type { ComponentChildren } from 'preact';

export function StatTile({ label, value, note, tone = 'ok' }: { label: string; value: ComponentChildren; note: string; tone?: 'ok' | 'warn' }) {
  return (
    <div class="fd-tile">
      <span class="fd-tile__label">{label}</span>
      <span class="fd-tile__value">{value}</span>
      <span class="fd-tile__note">
        <span class={'fd-tile__icon' + (tone === 'warn' ? ' fd-tile__icon--warn' : '')} aria-hidden="true">{tone === 'warn' ? '!' : '✓'}</span>
        <span class="visually-hidden">{tone === 'warn' ? 'Warning: ' : 'OK: '}</span>{note}
      </span>
    </div>
  );
}

export interface Column { key: string; label: string; num?: boolean; bar?: boolean }
export function DataTable({ label, columns, rows, template, phoneTemplate }: {
  label: string; columns: Column[]; rows: Record<string, ComponentChildren | number>[]; template: string;
  /** columns at ≤ 640 px; defaults to equal shares */
  phoneTemplate?: string;
}) {
  const cols = `--cols: ${template}; --cols-phone: ${phoneTemplate ?? `repeat(${columns.length}, minmax(0, 1fr))`}`;
  const max = Math.max(1, ...rows.flatMap((r) => columns.filter((c) => c.bar).map((c) => Number(r[c.key]) || 0)));
  return (
    <div role="table" aria-label={label} class="fd-table" style={cols}>
      <div role="row" class="fd-table__row fd-table__row--head">
        {columns.map((c) => <span role="columnheader" class={c.num ? 'fd-table__num' : undefined}>{c.label}</span>)}
      </div>
      {rows.map((r) => (
        <div role="row" class="fd-table__row">
          {columns.map((c) =>
            c.bar ? (
              <span role="cell" class="fd-table__bar"><span style={`width: calc((100% - 40px) * ${(Number(r[c.key]) / max).toFixed(3)})`} /><span>{r[c.key]}</span></span>
            ) : (
              <span role="cell" class={c.num ? 'fd-table__num' : undefined} style={c.key === columns[0]!.key ? 'font-weight: 500' : undefined}>{r[c.key]}</span>
            ),
          )}
        </div>
      ))}
    </div>
  );
}
