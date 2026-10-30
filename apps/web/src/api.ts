import {
  isStitchPlan,
  type StitchPlan,
  type ExportFormat,
} from "@stitchord/contracts";
import type { CompileDocument } from "./sampleDoc";

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown };
    if (typeof data.detail === "string") return data.detail;
    if (data.detail) return JSON.stringify(data.detail);
  } catch {
    /* 非 JSON 响应，退回状态文本 */
  }
  return `${response.status} ${response.statusText}`;
}

export async function previewStitch(file: File): Promise<StitchPlan> {
  const form = new FormData();
  form.append("file", file);
  const response = await fetch("/api/v1/stitch/preview", {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(await readError(response));
  const data: unknown = await response.json();
  if (!isStitchPlan(data)) {
    throw new Error("服务返回的数据不符合 StitchPlan 契约");
  }
  return data;
}

export async function exportStitch(
  plan: StitchPlan,
  format: ExportFormat,
): Promise<Blob> {
  const response = await fetch("/api/v1/stitch/export", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, format }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.blob();
}

export async function digitizeDocument(
  document: CompileDocument,
): Promise<StitchPlan> {
  const response = await fetch("/api/v1/digitize", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(document),
  });
  if (!response.ok) throw new Error(await readError(response));
  const data: unknown = await response.json();
  if (!isStitchPlan(data)) {
    throw new Error("服务返回的针迹计划不符合契约");
  }
  return data;
}

export async function digitizeExport(
  document: CompileDocument,
  format: ExportFormat = "dst",
): Promise<Blob> {
  const response = await fetch(`/api/v1/digitize/export?format=${format}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(document),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.blob();
}

export interface ValidationIssue {
  code: string;
  severity: "error" | "warning";
  message: string;
  blockId?: string | null;
  stitchIndex?: number | null;
}

export interface ValidationReport {
  ok: boolean;
  issues: ValidationIssue[];
}

export async function checkPlan(
  plan: StitchPlan,
  hoopWidthMm: number,
  hoopHeightMm: number,
): Promise<ValidationReport> {
  const response = await fetch("/api/v1/stitch/check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, hoopWidthMm, hoopHeightMm }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as ValidationReport;
}

export interface VectorizeResult {
  document: CompileDocument;
  stats: { layers: number; paths: number; widthMm: number; heightMm: number };
}

export interface WorksheetMeta {
  projectName?: string;
  fabric?: string | null;
  hoop?: string | null;
}

export async function downloadWorksheet(
  plan: StitchPlan,
  meta: WorksheetMeta = {},
): Promise<Blob> {
  const response = await fetch("/api/v1/worksheet", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ plan, ...meta }),
  });
  if (!response.ok) throw new Error(await readError(response));
  return response.blob();
}

export async function vectorizeImage(
  file: File,
  widthMm = 100,
  maxColors = 8,
  removeBackground = true,
  style: "flat" | "photo" = "flat",
): Promise<VectorizeResult> {
  const form = new FormData();
  form.append("file", file);
  form.append("width_mm", String(widthMm));
  form.append("max_colors", String(maxColors));
  form.append("remove_background", removeBackground ? "true" : "false");
  form.append("style", style);
  const response = await fetch("/api/v1/vectorize", {
    method: "POST",
    body: form,
  });
  if (!response.ok) throw new Error(await readError(response));
  return (await response.json()) as VectorizeResult;
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
