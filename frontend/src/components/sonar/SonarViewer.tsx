import { useCallback, useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import type { PointerEvent, WheelEvent } from 'react';
import type { AnalyzeResponse } from '../../types';
import BoundingBoxOverlay from './BoundingBoxOverlay';
import CursorCoordinates from './CursorCoordinates';
import ViewerToolbar from './ViewerToolbar';
import { boundedPan, displayTransform, fitScale, screenToImage } from './viewerGeometry';
import type { Point, Size } from './viewerGeometry';

type Props = { src: string | null; filename: string | null; dimensions: Size | null; result: AnalyzeResponse | null; selectedId: string | null; onSelect: (id: string) => void; onUpload: () => void };

export default function SonarViewer({ src, filename, dimensions, result, selectedId, onSelect, onUpload }: Props) {
  const viewportRef = useRef<HTMLDivElement>(null);
  const dragRef = useRef<{ pointerId: number; x: number; y: number; pan: Point } | null>(null);
  const [viewport, setViewport] = useState<Size>({ width: 0, height: 0 });
  const [mode, setMode] = useState<'fit' | 'actual'>('fit');
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState<Point>({ x: 0, y: 0 });
  const [overlays, setOverlays] = useState(true);
  const [cursor, setCursor] = useState<Point | null>(null);
  const [dragging, setDragging] = useState(false);
  const image = useMemo<Size | null>(() => {
    const width = result?.input.width ?? dimensions?.width;
    const height = result?.input.height ?? dimensions?.height;
    return width && height ? { width, height } : null;
  }, [dimensions, result]);

  useLayoutEffect(() => {
    const node = viewportRef.current;
    if (!node) return;
    const update = () => setViewport({ width: node.clientWidth, height: node.clientHeight });
    update();
    const observer = new ResizeObserver(update);
    observer.observe(node);
    return () => observer.disconnect();
  }, []);

  const fitted = image && viewport.width && viewport.height ? fitScale(viewport, image) : 1;
  const scale = (mode === 'fit' ? fitted : 1) * zoom;
  const transform = image ? displayTransform(viewport, image, scale, pan) : null;
  const display = transform?.display;
  const safePan = transform?.safePan ?? pan;
  // Backend boxes stay in original image pixels. The image layer and percentage-positioned
  // boxes share one scale and translation: screen = centered offset + pan + pixel * scale.
  const offset = transform?.offset ?? { x: 0, y: 0 };
  const offsetX = offset.x;
  const offsetY = offset.y;

  const setView = useCallback((nextMode: 'fit' | 'actual') => { setMode(nextMode); setZoom(1); setPan({ x: 0, y: 0 }); }, []);
  const changeZoom = useCallback((factor: number, anchor?: Point) => {
    if (!image || !viewport.width) return;
    const nextZoom = Math.min(8, Math.max(.25, zoom * factor));
    const nextScale = (mode === 'fit' ? fitted : 1) * nextZoom;
    const focus = anchor ?? { x: viewport.width / 2, y: viewport.height / 2 };
    const { x: imageX, y: imageY } = screenToImage(focus, { x: offsetX, y: offsetY }, scale);
    const nextPan = {
      x: focus.x - imageX * nextScale - (viewport.width - image.width * nextScale) / 2,
      y: focus.y - imageY * nextScale - (viewport.height - image.height * nextScale) / 2,
    };
    setZoom(nextZoom);
    setPan(boundedPan(nextPan, viewport, image, nextScale));
  }, [image, viewport, zoom, mode, fitted, offsetX, offsetY, scale]);
  const onWheel = (event: WheelEvent<HTMLDivElement>) => {
    if (!image) return;
    event.preventDefault();
    const rect = event.currentTarget.getBoundingClientRect();
    changeZoom(event.deltaY < 0 ? 1.15 : 1 / 1.15, { x: event.clientX - rect.left, y: event.clientY - rect.top });
  };
  const onPointerDown = (event: PointerEvent<HTMLDivElement>) => {
    if (!image || event.button !== 0 || (event.target as HTMLElement).closest('button')) return;
    dragRef.current = { pointerId: event.pointerId, x: event.clientX, y: event.clientY, pan: safePan };
    event.currentTarget.setPointerCapture(event.pointerId);
    setDragging(true);
  };
  const onPointerMove = (event: PointerEvent<HTMLDivElement>) => {
    const rect = event.currentTarget.getBoundingClientRect();
    if (dragRef.current && image) {
      const next = { x: dragRef.current.pan.x + event.clientX - dragRef.current.x, y: dragRef.current.pan.y + event.clientY - dragRef.current.y };
      setPan(boundedPan(next, viewport, image, scale));
    }
    if (!image) return;
    const { x, y } = screenToImage({ x: event.clientX - rect.left, y: event.clientY - rect.top }, offset, scale);
    setCursor(x >= 0 && x <= image.width && y >= 0 && y <= image.height ? { x, y } : null);
  };
  const endDrag = (event: PointerEvent<HTMLDivElement>) => {
    if (dragRef.current?.pointerId === event.pointerId) {
      dragRef.current = null;
      if (event.currentTarget.hasPointerCapture(event.pointerId)) event.currentTarget.releasePointerCapture(event.pointerId);
      setDragging(false);
    }
  };
  useEffect(() => {
    if (!selectedId || !image || !viewport.width || !result) return;
    const selected = result.candidates.find(candidate => candidate.candidate_id === selectedId);
    if (!selected || selected.detection.bbox.length !== 4) return;
    const [x1, y1, x2, y2] = selected.detection.bbox;
    // Selection can originate from the queue, viewer, or map. Recenter only
    // when that external selection or viewport changes, never during zoom.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setPan(boundedPan({ x: image.width * scale / 2 - (x1 + x2) * scale / 2, y: image.height * scale / 2 - (y1 + y2) * scale / 2 }, viewport, image, scale));
  // Selection centers the object at the current scale. Zoom and pan remain user controlled.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, result, image?.width, image?.height, viewport.width, viewport.height]);

  return <section className="viewer panel" aria-label="Sonar image viewer">
    <div className="panel-heading viewer-heading"><div><span className="eyebrow">IMAGE WORKSPACE</span><h2>Sonar image viewer</h2></div><span className="viewer-hint">SCROLL TO ZOOM · DRAG TO PAN</span></div>
    <div ref={viewportRef} className={`viewer-canvas phase2-canvas ${dragging ? 'is-dragging' : ''}`} onWheel={onWheel} onPointerDown={onPointerDown} onPointerMove={onPointerMove} onPointerUp={endDrag} onPointerCancel={endDrag} onPointerLeave={() => setCursor(null)}>
      {src && image && display ? <div className="image-stage phase2-stage" style={{ width: display.width, height: display.height, left: offset.x, top: offset.y }}>
        <img src={src} alt="Original uploaded side-scan sonar image" draggable={false} />
        {overlays && result && <BoundingBoxOverlay candidates={result.candidates} width={image.width} height={image.height} selectedId={selectedId} onSelect={onSelect} />}
      </div> : <div className="viewer-empty"><div className="sonar-glyph">⌖</div><strong>NO SONAR IMAGE LOADED</strong><span>Upload a side-scan sonar image to begin analysis.</span><button type="button" className="secondary" onClick={onUpload}>UPLOAD SONAR</button></div>}
      <ViewerToolbar disabled={!src || !image} scale={scale} mode={mode} overlays={overlays} onZoomIn={() => changeZoom(1.25)} onZoomOut={() => changeZoom(.8)} onFit={() => setView('fit')} onActual={() => setView('actual')} onReset={() => setView('fit')} onToggleOverlays={() => setOverlays(value => !value)} />
      {src && <CursorCoordinates point={cursor} />}
    </div>
    <div className="viewer-footer"><span title={result?.input.filename ?? filename ?? undefined}>{result?.input.filename ?? filename ?? 'NO INPUT'}</span>{image && <span>{image.width} × {image.height} PX</span>}{result?.input.input_id && <span>{result.input.input_id}</span>}{result?.analysis_id && <span>{result.analysis_id}</span>}<span>{result?.processing.status ?? 'AWAITING ANALYSIS'}</span></div>
  </section>;
}
