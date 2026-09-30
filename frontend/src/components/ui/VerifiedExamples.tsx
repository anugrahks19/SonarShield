import { useEffect, useRef, useState } from 'react';

export const verifiedExamples = [
  { id: 'contact-105', label: 'Contact 105 · 2 candidates' },
  { id: 'contact-103', label: 'Contact 103 · 1 candidate' },
  { id: 'contact-104', label: 'Contact 104 · 1 candidate' },
  { id: 'background', label: 'Background · 0 candidates' },
] as const;

export type VerifiedExampleId = (typeof verifiedExamples)[number]['id'];

export default function VerifiedExamples({ busy, onConfirm, onClose }: { busy: boolean; onConfirm: (id: VerifiedExampleId) => void; onClose: () => void }) {
  const [selected, setSelected] = useState<VerifiedExampleId>('contact-105');
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    heading.current?.focus();
    const onEscape = (event: KeyboardEvent) => { if (event.key === 'Escape') onClose(); };
    document.addEventListener('keydown', onEscape);
    return () => document.removeEventListener('keydown', onEscape);
  }, [onClose]);

  return <section className="verified-example-panel" aria-labelledby="verified-example-heading">
    <div><span className="eyebrow">JUDGE WALKTHROUGH · VERIFIED EXAMPLES</span><h2 id="verified-example-heading" ref={heading} tabIndex={-1}>Explore a previously completed sonar analysis</h2></div>
    <p>Contact 105 is a real sonar image with a precomputed F9 analysis; the other bundled examples were completed earlier too. Their saved responses show candidates, evidence, localization, and review controls. <strong>No new inference will run, and it is not a result for your uploaded image.</strong></p>
    <div className="verified-example-actions"><label htmlFor="verified-example-select">Choose a real test image</label><select id="verified-example-select" value={selected} onChange={event => setSelected(event.target.value as VerifiedExampleId)} disabled={busy}>{verifiedExamples.map(example => <option key={example.id} value={example.id}>{example.label}</option>)}</select><button type="button" className="primary" onClick={() => onConfirm(selected)} disabled={busy}>{busy ? 'Checking example…' : 'Load precomputed example'}</button><button type="button" className="secondary" onClick={onClose} disabled={busy}>Keep current view</button></div>
  </section>;
}
