// C24. role="status". With an action (Undo), or a short confirmation
// ("Link copied") that clears itself.
import { useEffect } from 'preact/hooks';

export default function Toast({ message, action, onDone, timeout, small }: {
  message: string; action?: { label: string; onClick: () => void }; onDone?: () => void; timeout?: number; small?: boolean;
}) {
  useEffect(() => {
    if (!timeout || !onDone) return;
    const t = setTimeout(onDone, timeout);
    return () => clearTimeout(t);
  }, [timeout, onDone]);
  return (
    <div role="status" class={'fd-toast' + (small ? ' fd-toast--sm' : '')}>
      <span>{message}</span>
      {action && <button type="button" onClick={action.onClick}>{action.label}</button>}
    </div>
  );
}
