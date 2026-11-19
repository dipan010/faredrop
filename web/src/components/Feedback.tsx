// C23 Banner, C25 EmptyState, C26 Skeleton.
import type { ComponentChildren } from 'preact';
import { Alert, Clock, Plane } from './icons';
import Button from './Button';

export type BannerTone = 'error' | 'warn' | 'offline' | 'info' | 'note' | 'bad' | 'band';
export interface BannerProps {
  tone: BannerTone;
  title?: ComponentChildren;
  body?: ComponentChildren;
  action?: { label: string; href?: string; onClick?: () => void };
}

export function Banner({ tone, title, body, action }: BannerProps) {
  if (tone === 'offline') {
    return (
      <div role="status" class="fd-offline">
        <span>{body}</span>
        {action && <button type="button" onClick={action.onClick}>{action.label}</button>}
      </div>
    );
  }
  if (tone === 'band') {
    return (
      <section class="fd-band">
        <div class="fd-band__text"><span class="fd-band__title">{title}</span><span class="fd-band__body">{body}</span></div>
        {action && <Button kind="brand" size={44} href={action.href} onClick={action.onClick}>{action.label}</Button>}
      </section>
    );
  }
  if (tone === 'error') {
    return (
      <div role="alert" class="fd-banner fd-banner--error">
        <Alert />
        <span class="fd-banner__text"><span class="fd-banner__title">{title}</span><span class="fd-banner__body">{body}</span></span>
        {action && <Button kind="outline" size={40} href={action.href} onClick={action.onClick}>{action.label}</Button>}
      </div>
    );
  }
  return (
    <div role={tone === 'bad' ? 'alert' : 'status'} class={`fd-banner fd-banner--${tone}`}>
      {tone === 'warn' && <Clock />}
      <span class="fd-banner__text">
        {title && <span class="fd-banner__title">{title}</span>}
        {body && <span class="fd-banner__body">{body}</span>}
      </span>
      {action && (action.href ? <a href={action.href}>{action.label}</a> : <button type="button" class="fd-btn fd-btn--text" onClick={action.onClick}>{action.label}</button>)}
    </div>
  );
}

export function EmptyState({ title, body, action, solid, art }: {
  title: string; body: ComponentChildren; action?: { label: string; href?: string; onClick?: () => void; kind?: 'primary' | 'outline' };
  solid?: boolean; art?: boolean;
}) {
  return (
    <div class={'fd-empty' + (solid ? ' fd-empty--solid' : '')}>
      {art && <Plane />}
      <span class="fd-empty__title">{title}</span>
      <span class="fd-empty__body">{body}</span>
      {action && <Button kind={action.kind ?? 'primary'} size={44} href={action.href} onClick={action.onClick}>{action.label}</Button>}
    </div>
  );
}

/** Same shape as a deal card so nothing jumps when data arrives. */
export function Skeleton({ shape = 'card', count = 1 }: { shape?: 'card' | 'block'; count?: number }) {
  const one = shape === 'card' ? (
    <div class="fd-card fd-skel" aria-hidden="true">
      <span style="width: 60%; height: 20px" />
      <span class="c" style="width: 40%; height: 12px" />
      <span style="width: 50%; height: 30px" />
      <div class="fd-skel__row"><span class="c" style="width: 70px; height: 22px" /><span class="c" style="width: 90px; height: 22px" /></div>
      <span class="c" style="height: 40px; border-radius: 8px" />
    </div>
  ) : (
    <div class="fd-card fd-skel" aria-hidden="true">
      <span style="width: 40%; height: 18px" />
      <span class="c" style="height: 14px" />
      <span class="c" style="width: 80%; height: 14px" />
    </div>
  );
  return <div aria-busy="true" aria-label="Loading deals" role="status" class="fd-skel-group">{Array.from({ length: count }, () => one)}</div>;
}
