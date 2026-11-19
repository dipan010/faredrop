// C5. A link when href is set, a button otherwise. Disabled links get
// aria-disabled and no href.
import type { ComponentChildren } from 'preact';

export type ButtonKind = 'primary' | 'accent' | 'outline' | 'secondary' | 'text' | 'quiet' | 'danger' | 'danger-outline' | 'brand';
export interface ButtonProps {
  kind?: ButtonKind;
  size?: 52 | 48 | 44 | 40 | 36;
  href?: string;
  disabled?: boolean;
  block?: boolean;
  type?: 'button' | 'submit';
  onClick?: (e: MouseEvent) => void;
  class?: string;
  'aria-label'?: string;
  'aria-pressed'?: boolean;
  children: ComponentChildren;
}

export default function Button({ kind = 'primary', size = 48, href, disabled, block, type = 'button', onClick, children, ...rest }: ButtonProps) {
  const cls = ['fd-btn', `fd-btn--${kind}`, size !== 48 && `fd-btn--${size}`, block && 'fd-btn--block', rest.class].filter(Boolean).join(' ');
  if (href && !disabled) return <a class={cls} href={href} aria-label={rest['aria-label']}>{children}</a>;
  if (href) return <a class={cls} aria-disabled="true" role="link" aria-label={rest['aria-label']}>{children}</a>;
  return (
    <button
      type={type}
      class={cls}
      onClick={disabled ? undefined : onClick}
      aria-disabled={disabled ? 'true' : undefined}
      aria-label={rest['aria-label']}
      aria-pressed={rest['aria-pressed']}
    >
      {children}
    </button>
  );
}
