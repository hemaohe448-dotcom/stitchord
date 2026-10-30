import type { Bounds } from "@stitchord/contracts";

export interface Viewport {
  /** 屏幕像素 / 毫米 */
  scale: number;
  tx: number;
  ty: number;
}

export function fitViewport(
  bounds: Bounds,
  width: number,
  height: number,
  padding = 48,
): Viewport {
  const bw = Math.max(bounds.maxX - bounds.minX, 1e-6);
  const bh = Math.max(bounds.maxY - bounds.minY, 1e-6);
  const scale = Math.min(
    Math.max(width - padding * 2, 1) / bw,
    Math.max(height - padding * 2, 1) / bh,
  );
  return {
    scale,
    tx: (width - bw * scale) / 2 - bounds.minX * scale,
    ty: (height - bh * scale) / 2 - bounds.minY * scale,
  };
}

export function toScreen(x: number, y: number, viewport: Viewport) {
  return {
    x: x * viewport.scale + viewport.tx,
    y: y * viewport.scale + viewport.ty,
  };
}

export function toWorld(x: number, y: number, viewport: Viewport) {
  return {
    x: (x - viewport.tx) / viewport.scale,
    y: (y - viewport.ty) / viewport.scale,
  };
}

/** 以屏幕点 (sx, sy) 为锚点缩放，锚点下的世界坐标保持不动。 */
export function zoomAt(
  viewport: Viewport,
  sx: number,
  sy: number,
  factor: number,
): Viewport {
  const nextScale = Math.min(Math.max(viewport.scale * factor, 0.05), 80);
  const world = toWorld(sx, sy, viewport);
  return {
    scale: nextScale,
    tx: sx - world.x * nextScale,
    ty: sy - world.y * nextScale,
  };
}
