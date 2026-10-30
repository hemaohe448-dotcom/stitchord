export interface CompileStitch {
  type: "fill" | "running" | "satin";
  rowSpacingMm?: number;
  angleDeg?: number;
  underlay?: boolean;
  satin_heavy_underlay?: boolean;
  pull_compensation_mm?: number;
  maxStitchLengthMm?: number;
  runningWidthMm?: number;
  satinDensityMm?: number;
}

export interface CompileObject {
  id: string;
  pathD: string;
  color: { hex: string; name?: string };
  stitch: CompileStitch;
  translateMm?: [number, number];
  hidden?: boolean;
  locked?: boolean;
}

export interface CompileLayer {
  id: string;
  name?: string;
  visible?: boolean;
  locked?: boolean;
  objects: CompileObject[];
}

export interface CompileDocument {
  widthMm: number;
  heightMm: number;
  fabric?: string;
  layers: CompileLayer[];
}

export const FABRICS = [
  { id: "woven", label: "平纹棉 Woven" },
  { id: "knit", label: "针织 Knit" },
  { id: "pique", label: "珠地 Piqué" },
  { id: "terry", label: "毛圈 Terry" },
  { id: "fleece", label: "抓绒 Fleece" },
  { id: "denim", label: "牛仔 Denim" },
  { id: "twill", label: "斜纹/帽料 Twill" },
  { id: "leather", label: "皮革 Leather" },
] as const;

/** A small two-colour document used by the “generate” demo. */
export function buildSampleDocument(
  fabric: string,
  stitch: "fill" | "running",
): CompileDocument {
  if (stitch === "running") {
    return {
      widthMm: 100,
      heightMm: 100,
      fabric,
      layers: [
        {
          id: "layer-outline",
          name: "outline",
          objects: [
            {
              id: "obj-outline",
              pathD: "M 10,50 L 50,50 L 50,80",
              color: { hex: "#2e7d32", name: "green" },
              stitch: { type: "running" },
            },
          ],
        },
      ],
    };
  }
  return {
    widthMm: 100,
    heightMm: 100,
    fabric,
    layers: [
      {
        id: "layer-red",
        name: "red",
        objects: [
          {
            id: "obj-red",
            pathD: "M 10,10 L 50,10 L 50,40 L 10,40 Z",
            color: { hex: "#c0392b", name: "red" },
            stitch: { type: "fill" },
          },
        ],
      },
      {
        id: "layer-blue",
        name: "blue",
        objects: [
          {
            id: "obj-blue",
            pathD: "M 60,10 L 90,10 L 90,40 L 60,40 Z",
            color: { hex: "#2980b9", name: "blue" },
            stitch: { type: "fill" },
          },
        ],
      },
    ],
  };
}
