import test from 'node:test';
import assert from 'node:assert/strict';
import { boundedPan, displayTransform, fitScale, imageToScreen, screenToImage } from '../src/components/sonar/viewerGeometry.ts';

const image = { width: 640, height: 640 };
const box = [328.72943115234375, 9.503705978393555, 343.97467041015625, 21.56841468811035];

for (const [name, viewport] of [
  ['1280 × 720', { width: 730, height: 430 }],
  ['1440 × 900', { width: 850, height: 550 }],
  ['1920 × 1080', { width: 1250, height: 690 }],
]) {
  test(`fit and backend box alignment at ${name}`, () => {
    const scale = fitScale(viewport, image);
    const { display, offset } = displayTransform(viewport, image, scale, { x: 0, y: 0 });
    assert.ok(display.width <= viewport.width - 24 + 1e-9);
    assert.ok(display.height <= viewport.height - 24 + 1e-9);
    const topLeft = imageToScreen({ x: box[0], y: box[1] }, offset, scale);
    const bottomRight = imageToScreen({ x: box[2], y: box[3] }, offset, scale);
    assert.ok(topLeft.x < bottomRight.x && topLeft.y < bottomRight.y);
    const recovered = screenToImage(topLeft, offset, scale);
    assert.ok(Math.abs(recovered.x - box[0]) < 1e-10);
    assert.ok(Math.abs(recovered.y - box[1]) < 1e-10);
  });
}

test('zoom and pan move the image and box by the same transform', () => {
  const viewport = { width: 500, height: 400 };
  const scale = 1.5;
  const pan = boundedPan({ x: -90, y: 75 }, viewport, image, scale);
  const { offset } = displayTransform(viewport, image, scale, pan);
  for (const [x, y] of [[box[0], box[1]], [box[2], box[3]], [336.352, 15.536]]) {
    const screen = imageToScreen({ x, y }, offset, scale);
    const recovered = screenToImage(screen, offset, scale);
    assert.ok(Math.abs(recovered.x - x) < 1e-10);
    assert.ok(Math.abs(recovered.y - y) < 1e-10);
  }
  assert.deepEqual(box, [328.72943115234375, 9.503705978393555, 343.97467041015625, 21.56841468811035]);
});

test('pan is zero in fit mode and bounded at actual size', () => {
  const viewport = { width: 500, height: 400 };
  assert.deepEqual(boundedPan({ x: 100, y: -100 }, viewport, image, fitScale(viewport, image)), { x: 0, y: 0 });
  assert.deepEqual(boundedPan({ x: 999, y: -999 }, viewport, image, 1), { x: 70, y: -120 });
});
