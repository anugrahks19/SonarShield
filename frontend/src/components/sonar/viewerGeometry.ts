export type Size = { width: number; height: number };
export type Point = { x: number; y: number };

const limit = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

export function fitScale(viewport: Size, image: Size): number {
  return Math.min((viewport.width - 24) / image.width, (viewport.height - 24) / image.height);
}

export function boundedPan(pan: Point, viewport: Size, image: Size, scale: number): Point {
  const halfX = Math.max(0, (image.width * scale - viewport.width) / 2);
  const halfY = Math.max(0, (image.height * scale - viewport.height) / 2);
  return { x: halfX === 0 ? 0 : limit(pan.x, -halfX, halfX), y: halfY === 0 ? 0 : limit(pan.y, -halfY, halfY) };
}

export function displayTransform(viewport: Size, image: Size, scale: number, pan: Point) {
  const display = { width: image.width * scale, height: image.height * scale };
  const safePan = boundedPan(pan, viewport, image, scale);
  const offset = { x: (viewport.width - display.width) / 2 + safePan.x, y: (viewport.height - display.height) / 2 + safePan.y };
  return { display, safePan, offset };
}

export function imageToScreen(pixel: Point, offset: Point, scale: number): Point {
  return { x: offset.x + pixel.x * scale, y: offset.y + pixel.y * scale };
}

export function screenToImage(screen: Point, offset: Point, scale: number): Point {
  return { x: (screen.x - offset.x) / scale, y: (screen.y - offset.y) / scale };
}
