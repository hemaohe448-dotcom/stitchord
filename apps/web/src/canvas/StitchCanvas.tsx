import { useEffect, useRef, useState } from "react";
import type { StitchPlan } from "@stitchord/contracts";
import { movePolylinePoint, parsePolyline, serializePolyline } from "../path";
import type { CompileDocument, CompileObject } from "../sampleDoc";
import { fitViewport, toScreen, toWorld, zoomAt, type Viewport } from "./transform";

interface StitchCanvasProps {
  plan: StitchPlan;
  hidden: Record<string, boolean>;
  showJumps: boolean;
  fitToken: number;
  doc: CompileDocument | null;
  selectedId: string | null;
  nodeMode: boolean;
  drawMode: boolean;
  onSelect: (id: string | null) => void;
  onMove: (id: string, value: [number, number], commit: boolean) => void;
  onPath: (id: string, pathD: string, commit: boolean) => void;
  onDraw: (points: Array<[number, number]>) => void;
}

type DragState =
  | { mode: "pan"; x: number; y: number; tx: number; ty: number }
  | {
      mode: "object";
      id: string;
      startX: number;
      startY: number;
      startTranslate: [number, number];
      last: [number, number];
      moved: boolean;
    }
  | {
      mode: "node";
      id: string;
      index: number;
      translate: [number, number];
      startPath: string;
      lastPath: string;
    }
  | { mode: "draw" };

function findObject(doc: CompileDocument, id: string | null): CompileObject | null {
  if (!id) return null;
  for (const layer of doc.layers) {
    const found = layer.objects.find((obj) => obj.id === id);
    if (found) return found;
  }
  return null;
}

function hitTest(
  doc: CompileDocument,
  world: { x: number; y: number },
  ctx: CanvasRenderingContext2D,
): CompileObject | null {
  for (let li = doc.layers.length - 1; li >= 0; li -= 1) {
    const layer = doc.layers[li];
    if (layer.visible === false) continue;
    const objects = layer.objects;
    for (let oi = objects.length - 1; oi >= 0; oi -= 1) {
      const obj = objects[oi];
      const [dx, dy] = obj.translateMm ?? [0, 0];
      const local = { x: world.x - dx, y: world.y - dy };
      const path = new Path2D(obj.pathD);
      ctx.save();
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      let hit = false;
      if (obj.stitch.type === "fill") {
        hit = ctx.isPointInPath(path, local.x, local.y);
      } else {
        ctx.lineWidth = 2;
        hit = ctx.isPointInStroke(path, local.x, local.y);
      }
      ctx.restore();
      if (hit) return obj;
    }
  }
  return null;
}

function visibleGridStep(scale: number): number {
  const candidates = [1, 2, 5, 10, 20, 50, 100];
  return candidates.find((step) => step * scale >= 28) ?? 100;
}

export function StitchCanvas({
  plan,
  hidden,
  showJumps,
  fitToken,
  doc,
  selectedId,
  nodeMode,
  drawMode,
  onSelect,
  onMove,
  onPath,
  onDraw,
}: StitchCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<DragState | null>(null);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const lastFit = useRef<{ token: number; width: number; height: number } | null>(
    null,
  );
  const [drawPoints, setDrawPoints] = useState<Array<[number, number]>>([]);
  const [viewport, setViewport] = useState<Viewport>({
    scale: 1,
    tx: 0,
    ty: 0,
  });

  useEffect(() => {
    const element = containerRef.current;
    if (!element) return;
    const observer = new ResizeObserver((entries) => {
      const rect = entries[0]?.contentRect;
      if (rect) setSize({ width: rect.width, height: rect.height });
    });
    observer.observe(element);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (size.width <= 0 || size.height <= 0) return;
    const width = plan.bounds.maxX - plan.bounds.minX;
    const height = plan.bounds.maxY - plan.bounds.minY;
    const previous = lastFit.current;
    const drasticallyChanged =
      !previous ||
      previous.token !== fitToken ||
      Math.abs(width - previous.width) > Math.max(previous.width * 0.2, 4) ||
      Math.abs(height - previous.height) > Math.max(previous.height * 0.2, 4);
    if (!drasticallyChanged) return;
    lastFit.current = { token: fitToken, width, height };
    setViewport(fitViewport(plan.bounds, size.width, size.height));
  }, [plan.bounds, fitToken, size.width, size.height]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas || size.width <= 0 || size.height <= 0) return;
    const dpr = window.devicePixelRatio || 1;
    canvas.width = Math.round(size.width * dpr);
    canvas.height = Math.round(size.height * dpr);
    canvas.style.width = `${size.width}px`;
    canvas.style.height = `${size.height}px`;

    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, size.width, size.height);

    const gridStep = visibleGridStep(viewport.scale);
    const topLeft = toWorld(0, 0, viewport);
    const bottomRight = toWorld(size.width, size.height, viewport);
    ctx.lineWidth = 1;
    ctx.strokeStyle = "rgba(255,255,255,0.045)";
    ctx.beginPath();
    const startX = Math.floor(topLeft.x / gridStep) * gridStep;
    const startY = Math.floor(topLeft.y / gridStep) * gridStep;
    for (let x = startX; x <= bottomRight.x; x += gridStep) {
      const p = toScreen(x, 0, viewport);
      ctx.moveTo(p.x, 0);
      ctx.lineTo(p.x, size.height);
    }
    for (let y = startY; y <= bottomRight.y; y += gridStep) {
      const p = toScreen(0, y, viewport);
      ctx.moveTo(0, p.y);
      ctx.lineTo(size.width, p.y);
    }
    ctx.stroke();

    const boundsA = toScreen(plan.bounds.minX, plan.bounds.minY, viewport);
    const boundsB = toScreen(plan.bounds.maxX, plan.bounds.maxY, viewport);
    ctx.setLineDash([6, 6]);
    ctx.strokeStyle = "rgba(255,255,255,0.18)";
    ctx.strokeRect(
      boundsA.x,
      boundsA.y,
      boundsB.x - boundsA.x,
      boundsB.y - boundsA.y,
    );
    ctx.setLineDash([]);

    const width = Math.min(Math.max(viewport.scale * 0.16, 0.7), 4);
    for (const block of plan.colorBlocks) {
      if (hidden[block.id]) continue;
      ctx.strokeStyle = block.color.hex;
      ctx.lineWidth = width;
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.beginPath();

      let hasPoint = false;
      let afterTrim = false;
      for (const stitch of block.stitches) {
        const point = toScreen(stitch.x, stitch.y, viewport);
        if (stitch.command === "STITCH") {
          if (hasPoint && !afterTrim) ctx.lineTo(point.x, point.y);
          else ctx.moveTo(point.x, point.y);
          afterTrim = false;
        } else if (stitch.command === "TRIM") {
          ctx.moveTo(point.x, point.y);
          afterTrim = true;
        } else if (stitch.command === "END" || stitch.command === "STOP") {
          afterTrim = true;
          hasPoint = false;
          continue;
        } else {
          ctx.moveTo(point.x, point.y);
          afterTrim = false;
        }
        hasPoint = true;
      }
      ctx.stroke();
    }

    if (showJumps) {
      ctx.strokeStyle = "rgba(255, 214, 102, 0.5)";
      ctx.lineWidth = Math.max(0.8, width * 0.6);
      ctx.setLineDash([4, 4]);
      ctx.beginPath();
      for (const block of plan.colorBlocks) {
        if (hidden[block.id]) continue;
        let previous: { x: number; y: number } | null = null;
        for (const stitch of block.stitches) {
          if (previous && stitch.command === "JUMP") {
            const from = toScreen(previous.x, previous.y, viewport);
            const to = toScreen(stitch.x, stitch.y, viewport);
            ctx.moveTo(from.x, from.y);
            ctx.lineTo(to.x, to.y);
          }
          previous = { x: stitch.x, y: stitch.y };
        }
      }
      ctx.stroke();
      ctx.setLineDash([]);
    }

    const first = plan.colorBlocks[0]?.stitches.find(
      (stitch) => stitch.command === "STITCH",
    );
    if (first) {
      const point = toScreen(first.x, first.y, viewport);
      ctx.fillStyle = "#68d391";
      ctx.beginPath();
      ctx.arc(point.x, point.y, 4, 0, Math.PI * 2);
      ctx.fill();
    }

    const selected = doc ? findObject(doc, selectedId) : null;
    if (selected) {
      const [dx, dy] = selected.translateMm ?? [0, 0];
      ctx.save();
      ctx.translate(
        viewport.tx + dx * viewport.scale,
        viewport.ty + dy * viewport.scale,
      );
      ctx.scale(viewport.scale, viewport.scale);
      ctx.strokeStyle = "#f6ad55";
      ctx.lineWidth = 1.5 / viewport.scale;
      ctx.setLineDash([4 / viewport.scale, 3 / viewport.scale]);
      ctx.stroke(new Path2D(selected.pathD));
      ctx.restore();

      if (nodeMode) {
        const polyline = parsePolyline(selected.pathD);
        if (polyline) {
          const [dx, dy] = selected.translateMm ?? [0, 0];
          ctx.fillStyle = "#f6ad55";
          ctx.strokeStyle = "#1a1206";
          ctx.lineWidth = 1;
          for (const [x, y] of polyline.points) {
            const screenX =
              (x + dx) * viewport.scale + viewport.tx;
            const screenY =
              (y + dy) * viewport.scale + viewport.ty;
            ctx.beginPath();
            ctx.rect(screenX - 4, screenY - 4, 8, 8);
            ctx.fill();
            ctx.stroke();
          }
        }
      }
    }

    if (drawPoints.length > 1) {
      ctx.strokeStyle = "#f6ad55";
      ctx.lineWidth = 2;
      ctx.setLineDash([5, 3]);
      ctx.beginPath();
      drawPoints.forEach(([x, y], index) => {
        const point = toScreen(x, y, viewport);
        if (index === 0) ctx.moveTo(point.x, point.y);
        else ctx.lineTo(point.x, point.y);
      });
      ctx.stroke();
      ctx.setLineDash([]);
    }
  }, [plan, hidden, showJumps, viewport, size, doc, selectedId, nodeMode, drawPoints]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const onWheel = (event: WheelEvent) => {
      event.preventDefault();
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      setViewport((current) =>
        zoomAt(current, x, y, Math.exp(-event.deltaY * 0.0015)),
      );
    };
    canvas.addEventListener("wheel", onWheel, { passive: false });
    return () => canvas.removeEventListener("wheel", onWheel);
  }, []);

  return (
    <div className="canvas-shell" ref={containerRef}>
      <canvas
        ref={canvasRef}
        className={drawMode ? "stitch-canvas is-drawing" : "stitch-canvas"}
        onPointerDown={(event) => {
          const canvas = canvasRef.current;
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          const world = toWorld(
            event.clientX - rect.left,
            event.clientY - rect.top,
            viewport,
          );
          if (drawMode) {
            setDrawPoints([[world.x, world.y]]);
            dragRef.current = { mode: "draw" };
            event.currentTarget.setPointerCapture(event.pointerId);
            return;
          }
          const ctx = canvas.getContext("2d");
          const selectedObject = doc ? findObject(doc, selectedId) : null;
          if (nodeMode && selectedObject && ctx) {
            const polyline = parsePolyline(selectedObject.pathD);
            if (polyline) {
              const [dx, dy] = selectedObject.translateMm ?? [0, 0];
              const screenX = event.clientX - rect.left;
              const screenY = event.clientY - rect.top;
              for (let index = 0; index < polyline.points.length; index += 1) {
                const [x, y] = polyline.points[index];
                const px = (x + dx) * viewport.scale + viewport.tx;
                const py = (y + dy) * viewport.scale + viewport.ty;
                if (Math.hypot(px - screenX, py - screenY) <= 9) {
                  dragRef.current = {
                    mode: "node",
                    id: selectedObject.id,
                    index,
                    translate: [dx, dy],
                    startPath: selectedObject.pathD,
                    lastPath: selectedObject.pathD,
                  };
                  event.currentTarget.setPointerCapture(event.pointerId);
                  return;
                }
              }
            }
          }
          const hit = doc && ctx ? hitTest(doc, world, ctx) : null;
          if (hit) {
            onSelect(hit.id);
            const start = hit.translateMm ?? [0, 0];
            dragRef.current = {
              mode: "object",
              id: hit.id,
              startX: world.x,
              startY: world.y,
              startTranslate: [start[0], start[1]],
              last: [start[0], start[1]],
              moved: false,
            };
          } else {
            onSelect(null);
            dragRef.current = {
              mode: "pan",
              x: event.clientX,
              y: event.clientY,
              tx: viewport.tx,
              ty: viewport.ty,
            };
          }
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const drag = dragRef.current;
          if (!drag) return;
          if (drag.mode === "draw") {
            const canvas = canvasRef.current;
            if (!canvas) return;
            const rect = canvas.getBoundingClientRect();
            const world = toWorld(
              event.clientX - rect.left,
              event.clientY - rect.top,
              viewport,
            );
            setDrawPoints((previous) => {
              const last = previous[previous.length - 1];
              if (last && Math.hypot(world.x - last[0], world.y - last[1]) < 0.8) {
                return previous;
              }
              return [...previous, [world.x, world.y]];
            });
            return;
          }
          if (drag.mode === "pan") {
            setViewport((current) => ({
              ...current,
              tx: drag.tx + (event.clientX - drag.x),
              ty: drag.ty + (event.clientY - drag.y),
            }));
            return;
          }
          const canvas = canvasRef.current;
          if (!canvas) return;
          const rect = canvas.getBoundingClientRect();
          const world = toWorld(
            event.clientX - rect.left,
            event.clientY - rect.top,
            viewport,
          );
          if (drag.mode === "node") {
            const polyline = parsePolyline(drag.startPath);
            if (!polyline) return;
            const next = serializePolyline(
              movePolylinePoint(
                polyline,
                drag.index,
                world.x - drag.translate[0],
                world.y - drag.translate[1],
              ),
            );
            drag.lastPath = next;
            onPath(drag.id, next, false);
            return;
          }
          const next: [number, number] = [
            drag.startTranslate[0] + (world.x - drag.startX),
            drag.startTranslate[1] + (world.y - drag.startY),
          ];
          drag.last = next;
          drag.moved = true;
          onMove(drag.id, next, false);
        }}
        onPointerUp={() => {
          const drag = dragRef.current;
          if (drag?.mode === "draw") {
            if (drawPoints.length >= 2) onDraw(drawPoints);
            setDrawPoints([]);
          } else if (drag?.mode === "node") {
            onPath(drag.id, drag.lastPath, true);
          } else if (drag?.mode === "object" && drag.moved) {
            onMove(drag.id, drag.last, true);
          }
          dragRef.current = null;
        }}
        onPointerCancel={() => {
          setDrawPoints([]);
          dragRef.current = null;
        }}
      />
    </div>
  );
}
