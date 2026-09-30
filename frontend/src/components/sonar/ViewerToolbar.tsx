import { Focus, Maximize2, Minus, Plus, Scan } from 'lucide-react';

type Props = { disabled: boolean; scale: number; mode: 'fit' | 'actual'; overlays: boolean; onZoomIn: () => void; onZoomOut: () => void; onFit: () => void; onActual: () => void; onReset: () => void; onToggleOverlays: () => void };

export default function ViewerToolbar({ disabled, scale, mode, overlays, onZoomIn, onZoomOut, onFit, onActual, onReset, onToggleOverlays }: Props) {
  return <div className="viewer-floating-toolbar" role="toolbar" aria-label="Sonar viewer controls">
    <button type="button" aria-label="Zoom out" title="Zoom out" onClick={onZoomOut} disabled={disabled}><Minus size={15} /></button>
    <span className="zoom-readout" title="Rendered image scale">{Math.round(scale * 100)}%</span>
    <button type="button" aria-label="Zoom in" title="Zoom in" onClick={onZoomIn} disabled={disabled}><Plus size={15} /></button>
    <span className="toolbar-divider" />
    <button type="button" className={mode === 'fit' ? 'is-active' : ''} onClick={onFit} disabled={disabled} aria-label="Fit image within viewer" title="Fit image"><Maximize2 size={15} /></button>
    <button type="button" className={mode === 'actual' ? 'is-active' : ''} onClick={onActual} disabled={disabled} aria-label="Show image at actual pixel size" title="Actual size">1:1</button>
    <button type="button" onClick={onReset} disabled={disabled} aria-label="Reset zoom and pan" title="Reset view"><Focus size={15} /></button>
    <span className="toolbar-divider" />
    <button type="button" onClick={onToggleOverlays} disabled={disabled} aria-pressed={overlays} aria-label={overlays ? 'Hide candidate overlays' : 'Show candidate overlays'} title="Toggle detection overlays"><Scan size={14} /> {overlays ? 'BOXES' : 'BOXES OFF'}</button>
  </div>;
}
