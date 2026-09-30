export default function CursorCoordinates({ point }: { point: { x: number; y: number } | null }) {
  return <div className="cursor-coordinates" aria-live="off">{point ? `IMAGE PIXEL  X ${Math.round(point.x)}  Y ${Math.round(point.y)}` : 'IMAGE PIXEL  —'}</div>;
}
