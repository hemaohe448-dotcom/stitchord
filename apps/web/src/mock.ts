import type {
  Bounds,
  ColorBlock,
  Stitch,
  StitchPlan,
  StitchStats,
} from "@stitchord/contracts";

const CENTER = 60;

function tatamiDisc(cx: number, cy: number, radius: number): Stitch[] {  const stitches: Stitch[] = [];
  const rowGap = 0.9;
  const step = 1.4;
  let forward = true;
  for (let y = cy - radius; y <= cy + radius; y += rowGap) {
    const half = Math.sqrt(Math.max(radius * radius - (y - cy) ** 2, 0));
    if (half < 0.5) continue;
    const from = forward ? cx - half : cx + half;
    const to = forward ? cx + half : cx - half;
    const distance = Math.abs(to - from);
    const count = Math.max(2, Math.ceil(distance / step));
    stitches.push({ x: from, y, command: "JUMP" });
    for (let i = 0; i <= count; i += 1) {
      stitches.push({
        x: from + ((to - from) * i) / count,
        y,
        command: "STITCH",
      });
    }
    forward = !forward;
  }
  stitches.push({ x: stitches.at(-1)!.x, y: stitches.at(-1)!.y, command: "END" });
  return stitches;
}

function satinPetal(angle: number): Stitch[] {
  const stitches: Stitch[] = [];
  const length = 30;
  const width = 9;
  const steps = 46;
  const dir = { x: Math.cos(angle), y: Math.sin(angle) };
  const normal = { x: -dir.y, y: dir.x };

  for (let i = 0; i <= steps; i += 1) {
    const t = i / steps;
    const along = 14 + length * t;
    const taper = Math.sin(Math.PI * t) ** 0.85 * width;
    const cx = CENTER + dir.x * along;
    const cy = CENTER + dir.y * along;
    const a = { x: cx + normal.x * taper, y: cy + normal.y * taper };
    const b = { x: cx - normal.x * taper, y: cy - normal.y * taper };
    const pair = i % 2 === 0 ? [a, b] : [b, a];
    for (const point of pair) {
      stitches.push({ x: point.x, y: point.y, command: "STITCH" });
    }
  }
  stitches.push({ x: stitches.at(-1)!.x, y: stitches.at(-1)!.y, command: "END" });
  return stitches;
}

function runningCircle(radius: number, count: number): Stitch[] {
  const stitches: Stitch[] = [];
  for (let i = 0; i <= count; i += 1) {
    const angle = (i / count) * Math.PI * 2;
    stitches.push({
      x: CENTER + Math.cos(angle) * radius,
      y: CENTER + Math.sin(angle) * radius,
      command: i === 0 ? "JUMP" : "STITCH",
    });
  }
  stitches.push({ x: stitches.at(-1)!.x, y: stitches.at(-1)!.y, command: "END" });
  return stitches;
}

function stats(blocks: ColorBlock[]): StitchStats {
  const all = blocks.flatMap((block) => block.stitches);
  const count = (name: Stitch["command"]) =>
    all.filter((stitch) => stitch.command === name).length;
  return {
    stitchCount: count("STITCH"),
    jumpCount: count("JUMP"),
    trimCount: count("TRIM"),
    colorChanges: Math.max(0, blocks.length - 1),
    colorBlocks: blocks.length,
  };
}

function boundsOf(blocks: ColorBlock[]): Bounds {
  const points = blocks.flatMap((block) => block.stitches);
  const xs = points.map((point) => point.x);
  const ys = points.map((point) => point.y);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys),
  };
}

/** Phase 0 演示数据：一版三色“花”样，用于在没有后端时验证渲染器。 */
export function makeMockPlan(): StitchPlan {
  const petals: Stitch[] = [];
  for (let i = 0; i < 6; i += 1) {
    petals.push(...satinPetal((i / 6) * Math.PI * 2 - Math.PI / 2));
  }

  const blocks: ColorBlock[] = [
    {
      id: "cb-1",
      color: { hex: "#2b6cb0", name: "Tatami Blue", brand: "demo" },
      stitches: tatamiDisc(CENTER, CENTER, 44),
    },
    {
      id: "cb-2",
      color: { hex: "#dd6b20", name: "Satin Orange", brand: "demo" },
      stitches: petals,
    },
    {
      id: "cb-3",
      color: { hex: "#1a202c", name: "Running Outline", brand: "demo" },
      stitches: runningCircle(46, 180),
    },
  ];

  return {
    schemaVersion: "1.0",
    unit: "mm",
    bounds: boundsOf(blocks),
    colorBlocks: blocks,
    stats: stats(blocks),
  };
}
