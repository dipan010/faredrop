// C9. Six digit boxes; typing moves on, Backspace moves back, pasting fills
// all six. onComplete fires with the code once all are filled.
import { useRef, useState } from 'preact/hooks';

export default function CodeInput({ length = 6, initial = '', onComplete }: { length?: number; initial?: string; onComplete?: (code: string) => void }) {
  const [digits, setDigits] = useState<string[]>(() => Array.from({ length }, (_, i) => initial[i] ?? ''));
  const refs = useRef<(HTMLInputElement | null)[]>([]);
  const update = (next: string[]) => {
    setDigits(next);
    if (next.every((d) => d)) onComplete?.(next.join(''));
  };
  const fill = (i: number, text: string) => {
    const clean = text.replace(/\D/g, '').slice(0, length - i);
    if (!clean) return;
    const next = [...digits];
    for (let k = 0; k < clean.length; k++) next[i + k] = clean[k]!;
    update(next);
    refs.current[Math.min(length - 1, i + clean.length)]?.focus();
  };
  return (
    <div class="fd-code" role="group" aria-label="6-digit code">
      {digits.map((d, i) => (
        <input
          ref={(el) => { refs.current[i] = el; }}
          type="text"
          inputMode="numeric"
          autocomplete={i === 0 ? 'one-time-code' : 'off'}
          maxLength={length}
          aria-label={`Digit ${i + 1}`}
          value={d}
          onInput={(e) => {
            const el = e.target as HTMLInputElement;
            if (el.value.length > 1) return fill(i, el.value);
            const v = el.value.replace(/\D/g, '');
            const next = [...digits];
            next[i] = v;
            el.value = v;
            update(next);
            if (v && i < length - 1) refs.current[i + 1]?.focus();
          }}
          onPaste={(e) => { e.preventDefault(); fill(i, e.clipboardData?.getData('text') ?? ''); }}
          onKeyDown={(e) => {
            if (e.key === 'Backspace' && !digits[i] && i > 0) refs.current[i - 1]?.focus();
            if (e.key === 'ArrowLeft' && i > 0) refs.current[i - 1]?.focus();
            if (e.key === 'ArrowRight' && i < length - 1) refs.current[i + 1]?.focus();
          }}
        />
      ))}
    </div>
  );
}
