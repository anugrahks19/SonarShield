import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';

export type Toast = { id: number; kind: 'success' | 'error' | 'info'; message: string };

export function ToastRegion({ toasts, dismiss }: { toasts: Toast[]; dismiss: (id: number) => void }) {
  return <div className="toast-region" aria-live="polite" aria-atomic="false">{toasts.map(toast => <div key={toast.id} className={`app-toast toast-${toast.kind}`} role={toast.kind === 'error' ? 'alert' : 'status'}>{toast.kind === 'success' ? <CheckCircle2 size={16} /> : toast.kind === 'error' ? <AlertCircle size={16} /> : <Info size={16} />}<span>{toast.message}</span><button type="button" aria-label="Dismiss notification" onClick={() => dismiss(toast.id)}><X size={14} /></button></div>)}</div>;
}

type BoundaryState = { failed: boolean; error: Error | null };
export class AppErrorBoundary extends Component<{ children: ReactNode }, BoundaryState> {
  state: BoundaryState = { failed: false, error: null };
  static getDerivedStateFromError(error: Error): BoundaryState { return { failed: true, error }; }
  componentDidCatch(error: Error, info: ErrorInfo) { if (import.meta.env.DEV) console.error('View rendering failed', error, info.componentStack); }
  render() {
    if (!this.state.failed) return this.props.children;
    return <main className="fatal-view"><span className="eyebrow">SONAR-SHIELD</span><h1>Something went wrong rendering this view.</h1><p>Your local review data remains in this browser.</p><button type="button" className="primary" onClick={() => window.location.reload()}>Reload application</button>{import.meta.env.DEV && this.state.error && <details><summary>Technical details</summary><pre>{this.state.error.message}</pre></details>}</main>;
  }
}
