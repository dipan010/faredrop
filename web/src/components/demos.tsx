// Gallery-only islands: wire components to local state so the gallery
// shows their interactive states. Phase 2's pages do the same with data.
import { useState } from 'preact/hooks';
import type { SnapshotDeal } from '../data/types';
import { destCity, originCity } from '../data/places';
import DealCard from './DealCard';
import Toast from './Toast';
import { Bookmark, Share } from './icons';
import type { SiblingDate } from './Price';

export function FeedCardDemo({ deal, nowIso, group, saved: s0 = false }: { deal: SnapshotDeal; nowIso: string; group?: SiblingDate[]; saved?: boolean }) {
  const [saved, setSaved] = useState(s0);
  const [hidden, setHidden] = useState(false);
  const name = `${originCity(deal.origin)} → ${destCity(deal.destination)}`;
  return (
    <div class="fd-stack-8">
      {hidden ? (
        <Toast message={`Hidden ${name}. We'll show you fewer trips like it.`} action={{ label: 'Undo', onClick: () => setHidden(false) }} />
      ) : (
        <DealCard deal={deal} now={new Date(nowIso)} group={group} saved={saved} onToggleSave={() => setSaved(!saved)} onHide={() => setHidden(true)} />
      )}
    </div>
  );
}

/** Deal page side panel: Save / Share pair; Share swaps to "Link copied". */
export function SaveSharePair({ initialSaved = false }: { initialSaved?: boolean }) {
  const [saved, setSaved] = useState(initialSaved);
  const [copied, setCopied] = useState(false);
  return (
    <div class="fd-pair">
      <button type="button" class="fd-toggle-save" aria-pressed={saved ? 'true' : 'false'} onClick={() => setSaved(!saved)}>{saved ? 'Saved' : 'Save'}</button>
      <button type="button" class="fd-toggle-save" onClick={() => setCopied(true)}>{copied ? 'Link copied' : 'Share'}</button>
      <span role="status" class="visually-hidden">{copied ? 'Link copied' : ''}</span>
    </div>
  );
}

/** Phone deal page header share + "Link copied" toast. */
export function PhoneShare() {
  const [copied, setCopied] = useState(false);
  return (
    <div class="fd-stack-8">
      <button type="button" class="fd-icon-btn fd-icon-btn--bordered" aria-label="Share" onClick={() => setCopied(true)}><Share /></button>
      {copied && <Toast small message="Link copied. Paste it into any chat." timeout={4000} onDone={() => setCopied(false)} />}
    </div>
  );
}

/** Phone save button in the sticky bar. */
export function SaveIcon({ initialSaved = false }: { initialSaved?: boolean }) {
  const [saved, setSaved] = useState(initialSaved);
  return (
    <button type="button" class="fd-save-btn" aria-pressed={saved ? 'true' : 'false'} aria-label="Save this deal" onClick={() => setSaved(!saved)}>
      <Bookmark />
    </button>
  );
}

/** Email verdict chips: preview of the three one-click links (E1). */
export function VoteDemo() {
  const notes: Record<string, string> = {
    '': 'One tap. It helps us send you fewer, better deals.',
    good: 'Thanks! We’ll keep sending trips like this.',
    meh: 'Got it. Fewer trips like this from now on.',
    diff: 'Thanks. We’ll re-check this fare in the next hour.',
  };
  const [v, setV] = useState('');
  return (
    <div class="fd-stack-8">
      <div role="group" aria-label="Rate this deal" class="fd-chips">
        {[['good', 'Great deal'], ['meh', 'Not my kind of trip'], ['diff', 'Price was different']].map(([id, label]) => (
          <button type="button" class="fd-chip" aria-pressed={v === id ? 'true' : 'false'} onClick={() => setV(id!)}>{label}</button>
        ))}
      </div>
      <span role="status" class="fd-small">{notes[v]}</span>
    </div>
  );
}
