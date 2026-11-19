// C19 CheckList and C20 Timeline (deal page).
import { CheckCircle } from './icons';

export function CheckList({ items }: { items: { title: string; detail: string }[] }) {
  return (
    <ul class="fd-checks">
      {items.map((c) => (
        <li><CheckCircle /><div class="fd-checks__text"><span class="fd-checks__title">{c.title}</span><span class="fd-checks__detail">{c.detail}</span></div></li>
      ))}
    </ul>
  );
}

export function Timeline({ steps }: { steps: { when: string; title: string; detail: string }[] }) {
  return (
    <ol class="fd-timeline">
      {steps.map((s) => (
        <li>
          <div class="fd-timeline__bar" aria-hidden="true" />
          <span class="fd-timeline__when">{s.when}</span>
          <span class="fd-timeline__title">{s.title}</span>
          <span class="fd-timeline__detail">{s.detail}</span>
        </li>
      ))}
    </ol>
  );
}
