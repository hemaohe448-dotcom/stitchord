import { describe, expect, it } from "vitest";
import { fitViewport, toScreen, zoomAt } from "./transform";

describe("fitViewport", () => {
  it("fits and centers a wide design", () => {
    const viewport = fitViewport(
      { minX: 0, minY: 0, maxX: 100, maxY: 50 },
      500,
      500,
      50,
    );
    expect(viewport.scale).toBeCloseTo(4);
    expect(toScreen(0, 0, viewport)).toEqual({ x: 50, y: 150 });
    expect(toScreen(100, 50, viewport)).toEqual({ x: 450, y: 350 });
  });

  it("keeps the anchor point fixed while zooming", () => {
    const viewport = fitViewport(
      { minX: -10, minY: -10, maxX: 10, maxY: 10 },
      400,
      400,
      20,
    );
    const anchor = { x: 137, y: 219 };
    const before = toScreen(
      (anchor.x - viewport.tx) / viewport.scale,
      (anchor.y - viewport.ty) / viewport.scale,
      viewport,
    );
    const zoomed = zoomAt(viewport, anchor.x, anchor.y, 1.7);
    const world = {
      x: (anchor.x - zoomed.tx) / zoomed.scale,
      y: (anchor.y - zoomed.ty) / zoomed.scale,
    };
    const after = toScreen(world.x, world.y, zoomed);
    expect(after.x).toBeCloseTo(before.x, 6);
    expect(after.y).toBeCloseTo(before.y, 6);
  });
});
