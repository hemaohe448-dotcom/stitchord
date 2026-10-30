import { useEffect, useRef, useState } from "react";
import type { StitchPlan } from "@stitchord/contracts";
import { fitViewport, toScreen, toWorld, zoomAt, type Viewport } from "./transform";

interface StitchCanvasProps {
  plan: StitchPlan;
  hidden: Record<string, boolean>;
  showJumps: boolean;
  fitToken: number;
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
}: StitchCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const dragRef = useRef<{ x: number; y: number; tx: number; ty: number } | null>(
    null,
  );
  const [size, setSize] = useState({ width: 0, height: 0 });
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
    setViewport(fitViewport(plan.bounds, size.width, size.height));
  }, [plan, fitToken, size.width, size.height]);

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
  }, [plan, hidden, showJumps, viewport, size]);

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
        className="stitch-canvas"
        onPointerDown={(event) => {
          dragRef.current = {
            x: event.clientX,
            y: event.clientY,
            tx: viewport.tx,
            ty: viewport.ty,
          };
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          const drag = dragRef.current;
          if (!drag) return;
          setViewport((current) => ({
            ...current,
            tx: drag.tx + (event.clientX - drag.x),
            ty: drag.ty + (event.clientY - drag.y),
          }));
        }}
        onPointerUp={() => {
          dragRef.current = null;
        }}
        onPointerCancel={() => {
          dragRef.current = null;
        }}
      />
    </div>
  );
}
