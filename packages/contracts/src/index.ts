/**
 * Stitchord 跨端契约（v1.0）
 *
 * 单位：毫米（mm），坐标原点由 Bounds 描述，Y 轴向下为正。
 * 该契约是编辑器、打版服务、导出器之间的唯一事实来源；
 * 修改必须同时更新 docs/contracts/ 与 Python 端 models.py。
 */

export const STITCH_COMMANDS = [
  "STITCH",
  "JUMP",
  "TRIM",
  "COLOR_CHANGE",
  "STOP",
  "END",
  "NEEDLE_AT",
  "UNKNOWN",
] as const;

export type StitchCommand = (typeof STITCH_COMMANDS)[number];

export interface Stitch {
  x: number;
  y: number;
  command: StitchCommand;
}

export interface Bounds {
  minX: number;
  minY: number;
  maxX: number;
  maxY: number;
}

export interface ThreadColor {
  name?: string | null;
  /** #RRGGBB */
  hex: string;
  brand?: string | null;
  code?: string | null;
}

export interface ColorBlock {
  id: string;
  color: ThreadColor;
  stitches: Stitch[];
}

export interface StitchStats {
  stitchCount: number;
  jumpCount: number;
  trimCount: number;
  colorChanges: number;
  colorBlocks: number;
}

export interface StitchPlan {
  schemaVersion: "1.0";
  unit: "mm";
  bounds: Bounds;
  colorBlocks: ColorBlock[];
  stats: StitchStats;
}

export const SUPPORTED_IMPORT_FORMATS = [
  "dst",
  "pes",
  "exp",
  "jef",
  "vp3",
  "xxx",
] as const;

export const SUPPORTED_EXPORT_FORMATS = [
  "dst",
  "exp",
  "jef",
  "pes",
  "vp3",
  "xxx",
] as const;

export type ExportFormat = (typeof SUPPORTED_EXPORT_FORMATS)[number];

export function emptyPlan(): StitchPlan {
  return {
    schemaVersion: "1.0",
    unit: "mm",
    bounds: { minX: 0, minY: 0, maxX: 0, maxY: 0 },
    colorBlocks: [],
    stats: {
      stitchCount: 0,
      jumpCount: 0,
      trimCount: 0,
      colorChanges: 0,
      colorBlocks: 0,
    },
  };
}

/** 轻量运行时校验：只保证渲染所需的最小结构，不做完整 JSON Schema 校验。 */
export function isStitchPlan(value: unknown): value is StitchPlan {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (v.schemaVersion !== "1.0" || v.unit !== "mm") return false;
  if (!Array.isArray(v.colorBlocks)) return false;
  if (typeof v.bounds !== "object" || v.bounds === null) return false;
  return v.colorBlocks.every((block) => {
    if (typeof block !== "object" || block === null) return false;
    const b = block as Record<string, unknown>;
    return (
      typeof b.id === "string" &&
      typeof b.color === "object" &&
      b.color !== null &&
      Array.isArray(b.stitches)
    );
  });
}
