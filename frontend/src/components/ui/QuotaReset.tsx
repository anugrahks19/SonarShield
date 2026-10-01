import { useEffect, useState } from 'react';

export default function QuotaReset({ details }: { details?: Record<string, unknown> }) {
  const [now, setNow] = useState(() => Date.now());
  const reset = typeof details?.resetAt === 'string' ? Date.parse(details.resetAt) : NaN;
  useEffect(() => {
    if (!Number.isFinite(reset)) return;
    const timer = window.setInterval(() => setNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [reset]);
  if (!Number.isFinite(reset)) return <span>Reset time was not supplied by Hugging Face.</span>;
  const remaining = Math.max(0, Math.ceil((reset - now) / 1000));
  if (!remaining) return <span>Hugging Face’s reported wait has elapsed. You can try live analysis again; availability is not guaranteed.</span>;
  const hours = Math.floor(remaining / 3600);
  const minutes = Math.floor(remaining % 3600 / 60);
  const seconds = remaining % 60;
  return <span>Hugging Face reported reset in {hours}:{String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')} · {new Date(reset).toLocaleString()}</span>;
}
