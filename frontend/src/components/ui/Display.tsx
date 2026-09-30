import type { ReactNode } from 'react';
import type { DecisionStatus } from '../../types';

export const format = (value: unknown) => value === null || value === undefined ? 'Not available' : typeof value === 'boolean' ? value ? 'YES' : 'NO' : String(value);
export const readable = (text: string) => text.replaceAll('_', ' ');
export function Badge({ status }: { status: string }) { return <span className={`badge status-${status.toLowerCase()}`}>{readable(status)}</span>; }
export function DecisionBadge({ status }: { status: DecisionStatus }) { return <span className={`badge decision-badge status-${status.toLowerCase()}`} aria-label={`AI decision ${readable(status)}`}>{readable(status)}</span>; }
export function Metric({ label, value, precision }: { label: string; value: unknown; precision?: number }) { const shown = precision !== undefined && typeof value === 'number' && Number.isFinite(value) ? value.toFixed(precision) : format(value); return <div className="metric"><span>{label}</span><strong title={precision !== undefined && typeof value === 'number' ? String(value) : undefined}>{shown}</strong></div>; }
export function Section({ title, children }: { title: string; children: ReactNode }) { return <section className="section"><h3>{title}</h3>{children}</section>; }
