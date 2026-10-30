import { useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import type { ExportFormat, StitchPlan } from "@stitchord/contracts";
import {
  checkPlan,
  downloadBlob,
  downloadWorksheet,
  digitizeDocument,
  digitizeExport,
  deleteProject,
  exportStitch,
  importSvg,
  listProjects,
  loadProject,
  previewStitch,
  saveProject,
  vectorizeImage,
} from "./api";
import type { ProjectSummary, ValidationIssue } from "./api";
import { StitchCanvas } from "./canvas/StitchCanvas";
import { parseCurve } from "./curve";
import { FABRICS } from "./sampleDoc";
import type { CompileDocument, CompileObject } from "./sampleDoc";
import { useEditorStore } from "./store";

const number = new Intl.NumberFormat("zh-CN");

const HOOPS = [
  { id: "100x100", label: "100 × 100 mm" },
  { id: "130x180", label: "130 × 180 mm" },
  { id: "160x260", label: "160 × 260 mm" },
  { id: "200x200", label: "200 × 200 mm" },
  { id: "60x120", label: "60 × 120 mm（帽框）" },
];

const FORMATS: ExportFormat[] = ["dst", "pes", "jef", "exp", "vp3", "xxx"];

function sizeLabel(plan: StitchPlan): string {
  const width = plan.bounds.maxX - plan.bounds.minX;
  const height = plan.bounds.maxY - plan.bounds.minY;
  return `${width.toFixed(1)} × ${height.toFixed(1)} mm`;
}

function allObjects(
  layers: { objects: CompileObject[] }[],
): CompileObject[] {
  return layers.flatMap((layer) => layer.objects);
}

function withoutUnderlay(doc: CompileDocument): CompileDocument {
  return {
    ...doc,
    layers: doc.layers.map((layer) => ({
      ...layer,
      objects: layer.objects.map((obj) => ({
        ...obj,
        stitch: {
          ...obj.stitch,
          underlay: false,
          satin_heavy_underlay: false,
        },
      })),
    })),
  };
}

export default function App() {
  const {
    doc,
    plan,
    selectedId,
    selectedIds,
    hidden,
    showJumps,
    fitToken,
    past,
    future,
    setPlan,
    setDoc,
    newSample,
    select,
    updateObject,
    updateStitch,
    setTranslate,
    setTranslations,
    setPath,
    addRectangle,
    addLine,
    addFreehand,
    duplicateSelected,
    deleteSelected,
    moveLayer,
    toggleLayer,
    toggleLayerLock,
    deleteLayer,
    duplicateLayer,
    mergeLayerDown,
    renameLayer,
    setProjectName,
    setFabric,
    undo,
    redo,
    setShowJumps,
    requestFit,
  } = useEditorStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const projectInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [generating, setGenerating] = useState(false);
  const [nodeMode, setNodeMode] = useState(false);
  const [drawMode, setDrawMode] = useState(false);
  const [maxColors, setMaxColors] = useState(8);
  const [removeBackground, setRemoveBackground] = useState(true);
  const [vectorStyle, setVectorStyle] = useState<"flat" | "photo">("flat");
  const [vectorDetail, setVectorDetail] = useState<"high" | "medium" | "low">(
    "medium",
  );
  const [previewTopOnly, setPreviewTopOnly] = useState(false);
  const [hoop, setHoop] = useState("100x100");
  const [format, setFormat] = useState<ExportFormat>("dst");
  const [issues, setIssues] = useState<ValidationIssue[]>([]);
  const [valid, setValid] = useState(true);
  const [checking, setChecking] = useState(false);
  const [playing, setPlaying] = useState(false);
  const [playIndex, setPlayIndex] = useState(0);
  const [playSpeed, setPlaySpeed] = useState(240);
  const [projects, setProjects] = useState<ProjectSummary[]>([]);
  const [showProjects, setShowProjects] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("示例工程 · 正在生成针迹…");

  const selected = doc
    ? allObjects(doc.layers).find((obj) => obj.id === selectedId)
    : undefined;
  const selectedCurve = selected ? parseCurve(selected.pathD) : null;
  const stitches = useMemo(
    () =>
      plan.colorBlocks.flatMap((block) =>
        block.stitches
          .filter((stitch) => stitch.command === "STITCH")
          .map((stitch) => ({ x: stitch.x, y: stitch.y, color: block.color.hex })),
      ),
    [plan],
  );

  useEffect(() => {
    setPlaying(false);
    setPlayIndex(0);
  }, [plan]);

  useEffect(() => {
    if (!playing || stitches.length === 0) return;
    const step = Math.max(1, Math.round(playSpeed / 60));
    const timer = window.setInterval(() => {
      setPlayIndex((current) =>
        Math.min(current + step, stitches.length - 1),
      );
    }, 16);
    return () => window.clearInterval(timer);
  }, [playing, playSpeed, stitches.length]);

  useEffect(() => {
    if (playing && stitches.length > 0 && playIndex >= stitches.length - 1) {
      setPlaying(false);
    }
  }, [playing, playIndex, stitches.length]);

  const activeStitch = stitches[playIndex] ?? null;

  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    const source = previewTopOnly ? withoutUnderlay(doc) : doc;
    setGenerating(true);
    const timer = window.setTimeout(async () => {
      try {
        const next = await digitizeDocument(source);
        if (cancelled) return;
        setPlan(next);
        setNotice(
          `${previewTopOnly ? "预览（仅面线）" : "已生成"} · ${doc.fabric ?? "woven"} · ${next.stats.stitchCount.toLocaleString()} 针`,
        );
      } catch (cause) {
        if (!cancelled) {
          setError(cause instanceof Error ? cause.message : String(cause));
        }
      } finally {
        if (!cancelled) setGenerating(false);
      }
    }, 450);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [doc, previewTopOnly, setPlan]);

  useEffect(() => {
    let cancelled = false;
    const [width, height] = hoop.split("x").map(Number);
    setChecking(true);
    checkPlan(plan, width, height)
      .then((report) => {
        if (cancelled) return;
        setIssues(report.issues);
        setValid(report.ok);
      })
      .catch(() => {
        if (!cancelled) {
          setValid(false);
          setIssues([
            {
              code: "CHECK_FAILED",
              severity: "error",
              message: "校验服务不可用，已禁用导出",
            },
          ]);
        }
      })
      .finally(() => {
        if (!cancelled) setChecking(false);
      });
    return () => {
      cancelled = true;
    };
  }, [plan, hoop]);

  async function onSaveToServer() {
    if (!doc) return;
    setBusy(true);
    setError(null);
    try {
      const name =
        doc.name?.trim() || `工程 ${new Date().toLocaleString("zh-CN")}`;
      const saved = await saveProject(name, doc);
      setNotice(`已保存到服务器 · ${saved.name}`);
      setProjects(await listProjects());
      setShowProjects(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  async function onRefreshProjects() {
    try {
      setProjects(await listProjects());
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function onOpenServerProject(id: string) {
    setBusy(true);
    setError(null);
    try {
      const project = await loadProject(id);
      setDoc(project.document);
      setNotice(`已从服务器打开 · ${project.name}`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  async function onDeleteServerProject(id: string) {
    try {
      await deleteProject(id);
      setProjects((items) => items.filter((item) => item.id !== id));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      if (file.name.toLowerCase().endsWith(".svg")) {
        const result = await importSvg(file, 100);
        setDoc(result.document);
        setNotice(
          `SVG 导入 · ${result.stats.layers} 色 / ${result.stats.paths} 个路径 · 正在生成针迹…`,
        );
        return;
      }
      const next = await previewStitch(file);
      setDoc(null);
      setPlan(next);
      setNotice(`${file.name} · ${next.stats.stitchCount.toLocaleString()} 针`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleFile(file);
    event.target.value = "";
  }

  async function handleImage(file: File) {
    setBusy(true);
    setError(null);
    try {
      const detail =
        vectorDetail === "high"
          ? { speckle: 2, difference: 8 }
          : vectorDetail === "low"
            ? { speckle: 12, difference: 28 }
            : { speckle: 4, difference: 16 };
      const result = await vectorizeImage(
        file,
        100,
        maxColors,
        removeBackground,
        vectorStyle,
        detail.speckle,
        detail.difference,
      );
      setDoc(result.document);
      setNotice(
        `矢量化 · ${result.stats.layers} 色 / ${result.stats.paths} 个路径 · 正在生成针迹…`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  function onPickImage(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (file) void handleImage(file);
    event.target.value = "";
  }

  function onSaveProject() {
    if (!doc) return;
    const blob = new Blob([JSON.stringify(doc, null, 2)], {
      type: "application/json",
    });
    downloadBlob(blob, `stitchord-${Date.now()}.json`);
    setNotice("已保存工程 JSON");
  }

  async function onOpenProject(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file) return;
    try {
      const parsed = JSON.parse(await file.text()) as CompileDocument;
      if (!parsed || !Array.isArray(parsed.layers) || !parsed.layers.length) {
        throw new Error("不是有效的 Stitchord 工程文件");
      }
      setDoc(parsed);
      setNotice(`${file.name} · 已打开工程`);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    }
  }

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      const target = event.target as HTMLElement | null;
      if (target && ["INPUT", "SELECT", "TEXTAREA"].includes(target.tagName)) {
        return;
      }
      const state = useEditorStore.getState();
      const mod = event.ctrlKey || event.metaKey;
      if (mod && event.key.toLowerCase() === "z") {
        event.preventDefault();
        if (event.shiftKey) state.redo();
        else state.undo();
        return;
      }
      if (mod && event.key.toLowerCase() === "y") {
        event.preventDefault();
        state.redo();
        return;
      }
      if (mod && event.key.toLowerCase() === "d") {
        event.preventDefault();
        state.duplicateSelected();
        return;
      }
      if (event.key === "Delete" || event.key === "Backspace") {
        event.preventDefault();
        state.deleteSelected();
        return;
      }
      if (event.key === "Escape") {
        state.select(null);
        setNodeMode(false);
        return;
      }
      if (event.key.startsWith("Arrow") && state.selectedId && state.doc) {
        event.preventDefault();
        const step = event.shiftKey ? 10 : 1;
        const ids = state.selectedIds.length
          ? state.selectedIds
          : [state.selectedId];
        const entries = ids
          .map((id) => {
            const object = state.doc?.layers
              .flatMap((layer) => layer.objects)
              .find((obj) => obj.id === id);
            if (!object) return null;
            const [x, y] = object.translateMm ?? [0, 0];
            return {
              id,
              value: [
                x +
                  (event.key === "ArrowRight"
                    ? step
                    : event.key === "ArrowLeft"
                      ? -step
                      : 0),
                y +
                  (event.key === "ArrowDown"
                    ? step
                    : event.key === "ArrowUp"
                      ? -step
                      : 0),
              ] as [number, number],
            };
          })
          .filter((entry): entry is { id: string; value: [number, number] } =>
            Boolean(entry),
          );
        state.setTranslations(entries, true);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      const [hoopWidth, hoopHeight] = hoop.split("x").map(Number);
      const blob = doc
        ? await digitizeExport(doc, format, hoopWidth, hoopHeight)
        : await exportStitch(plan, format);
      downloadBlob(blob, `stitchord-${Date.now()}.${format}`);
      setNotice(
        `已导出 ${format.toUpperCase()}（${doc ? "Ink/Stitch" : "计划导出"}）`,
      );
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  async function onWorksheet() {
    setBusy(true);
    setError(null);
    try {
      const fullPlan =
        previewTopOnly && doc ? await digitizeDocument(doc) : plan;
      const blob = await downloadWorksheet(fullPlan, {
        projectName: doc?.name || "Stitchord Design",
        fabric: doc?.fabric ?? null,
        hoop,
      });
      downloadBlob(blob, `stitchord-worksheet-${Date.now()}.pdf`);
      setNotice("已下载工艺单 PDF");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  function setColor(hex: string) {
    if (!selected) return;
    updateObject(selected.id, { color: { ...selected.color, hex } });
  }

  function setNumber(
    field: "x" | "y",
    raw: string,
  ) {
    if (!selected) return;
    const value = Number(raw);
    if (!Number.isFinite(value)) return;
    const current = selected.translateMm ?? [0, 0];
    setTranslate(
      selected.id,
      field === "x" ? [value, current[1]] : [current[0], value],
      true,
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>Stitchord</strong>
            <span className="brand-sub">绣花制版 · Phase 2 编辑</span>
          </div>
        </div>
        <div className="topbar-actions">
          <button
            type="button"
            className="button ghost"
            onClick={undo}
            disabled={!past.length || busy}
          >
            撤销
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={redo}
            disabled={!future.length || busy}
          >
            重做
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={requestFit}
            disabled={busy}
          >
            适应画布
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={() => inputRef.current?.click()}
            disabled={busy}
          >
            导入文件
          </button>
          <button
            type="button"
            className="button ghost"
            onClick={() => void onWorksheet()}
            disabled={busy || generating}
          >
            工艺单
          </button>
          <button
            type="button"
            className="button primary"
            onClick={() => void onExport()}
            disabled={busy || generating || !valid}
          >
            导出 DST
          </button>
        </div>
      </header>

      <div className="workspace">
        <aside className="sidebar">
          <section>
            <h2>文件</h2>
            <button
              type="button"
              className="dropzone"
              onClick={() => inputRef.current?.click()}
              disabled={busy}
            >
              <strong>{busy ? "处理中…" : "点击或拖入绣花文件"}</strong>
              <span>DST / PES / EXP / JEF / VP3 / XXX · ≤ 25 MB</span>
            </button>
            <input
              ref={inputRef}
              type="file"
              accept=".dst,.pes,.exp,.jef,.vp3,.xxx,.svg"
              onChange={onPick}
              hidden
            />
            <p className="hint">{notice}</p>
            <div className="button-row">
              <button
                type="button"
                className="button"
                onClick={() => void onSaveToServer()}
                disabled={!doc || busy}
              >
                保存到服务器
              </button>
              <button
                type="button"
                className="button"
                onClick={() => {
                  setShowProjects((value) => !value);
                  if (!showProjects) void onRefreshProjects();
                }}
              >
                项目库
              </button>
            </div>
            {showProjects ? (
              <div className="project-list">
                {projects.length === 0 ? (
                  <p className="hint">暂无服务器工程</p>
                ) : (
                  projects.map((project) => (
                    <div className="project-row" key={project.id}>
                      <button
                        type="button"
                        className="project-open"
                        onClick={() => void onOpenServerProject(project.id)}
                        title="打开服务器工程"
                      >
                        {project.name}
                      </button>
                      <button
                        type="button"
                        className="icon-button"
                        onClick={() => void onDeleteServerProject(project.id)}
                        title="删除服务器工程"
                      >
                        ×
                      </button>
                    </div>
                  ))
                )}
              </div>
            ) : null}
          </section>

          <section>
            <h2>工程</h2>
            <div className="field">
              <label htmlFor="project-name">工程名</label>
              <input
                key={doc?.name ?? ""}
                id="project-name"
                type="text"
                defaultValue={doc?.name ?? ""}
                placeholder="未命名工程"
                maxLength={120}
                onBlur={(event) => setProjectName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter") event.currentTarget.blur();
                }}
              />
            </div>
            <div className="field">
              <label htmlFor="fabric">面料预设</label>
              <select
                id="fabric"
                value={doc?.fabric ?? "woven"}
                onChange={(event) => setFabric(event.target.value)}
                disabled={!doc}
              >
                {FABRICS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="hoop">绣框</label>
              <select
                id="hoop"
                value={hoop}
                onChange={(event) => setHoop(event.target.value)}
              >
                {HOOPS.map((item) => (
                  <option key={item.id} value={item.id}>
                    {item.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="format">导出格式</label>
              <select
                id="format"
                value={format}
                onChange={(event) =>
                  setFormat(event.target.value as ExportFormat)
                }
              >
                {FORMATS.map((item) => (
                  <option key={item} value={item}>
                    {item.toUpperCase()}
                  </option>
                ))}
              </select>
            </div>
            <div className="field-row">
              <div className="field">
                <label htmlFor="colors">矢量化颜色数</label>
                <input
                  id="colors"
                  type="number"
                  min="2"
                  max="16"
                  value={maxColors}
                  onChange={(event) =>
                    setMaxColors(
                      Math.min(16, Math.max(2, Number(event.target.value) || 8)),
                    )
                  }
                />
              </div>
              <label className="toggle checkbox-field">
                <input
                  type="checkbox"
                  checked={removeBackground}
                  onChange={(event) => setRemoveBackground(event.target.checked)}
                />
                <span>去白底</span>
              </label>
            </div>
            <div className="field">
              <label htmlFor="vector-detail">矢量化细节</label>
              <select
                id="vector-detail"
                value={vectorDetail}
                onChange={(event) =>
                  setVectorDetail(event.target.value as "high" | "medium" | "low")
                }
              >
                <option value="high">高（保留小细节）</option>
                <option value="medium">中</option>
                <option value="low">低（更适合刺绣）</option>
              </select>
            </div>
            <div className="field">
              <label htmlFor="vector-style">矢量化风格</label>
              <select
                id="vector-style"
                value={vectorStyle}
                onChange={(event) =>
                  setVectorStyle(event.target.value as "flat" | "photo")
                }
              >
                <option value="flat">扁平插画 / Logo</option>
                <option value="photo">照片 / 渐变（实验）</option>
              </select>
            </div>
            <div className="button-row">
              <button
                type="button"
                className="button"
                onClick={newSample}
                disabled={busy}
              >
                新建示例
              </button>
              <button
                type="button"
                className="button"
                onClick={addRectangle}
                disabled={!doc || busy}
              >
                加矩形
              </button>
              <button
                type="button"
                className="button"
                onClick={addLine}
                disabled={!doc || busy}
              >
                加走线
              </button>
              <button
                type="button"
                className="button"
                onClick={() => imageInputRef.current?.click()}
                disabled={busy}
              >
                图片矢量化
              </button>
              <button
                type="button"
                className={drawMode ? "button primary" : "button"}
                onClick={() => {
                  setDrawMode((value) => !value);
                  setNodeMode(false);
                }}
              >
                {drawMode ? "结束绘制" : "自由绘制"}
              </button>
            </div>
            <input
              ref={imageInputRef}
              type="file"
              accept=".png,.jpg,.jpeg,.webp"
              onChange={onPickImage}
              hidden
            />
            <div className="button-row">
              <button
                type="button"
                className="button"
                onClick={onSaveProject}
                disabled={!doc}
              >
                保存工程
              </button>
              <button
                type="button"
                className="button"
                onClick={() => projectInputRef.current?.click()}
                disabled={busy}
              >
                打开工程
              </button>
            </div>
            <input
              ref={projectInputRef}
              type="file"
              accept=".json"
              onChange={(event) => void onOpenProject(event)}
              hidden
            />
            <p className="hint">
              {drawMode
                ? "在画布上按住拖动绘制走线，松开生成对象（之后可节点编辑）。"
                : generating
                  ? "正在重新生成针迹…"
                  : "修改后自动重新编译"}
            </p>
          </section>

          <section className="layers">
            <h2>图层 / 对象</h2>
            {doc ? (
              doc.layers.map((layer, layerIndex) => (
                <div
                  className={`layer-group ${layer.visible === false ? "is-hidden" : ""} ${layer.locked ? "is-locked" : ""}`}
                  key={layer.id}
                >
                  <div className="layer-head">
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => toggleLayer(layer.id)}
                      title={layer.visible === false ? "显示图层" : "隐藏图层"}
                    >
                      {layer.visible === false ? "○" : "●"}
                    </button>
                    <button
                      type="button"
                      className="icon-button"
                      onClick={() => toggleLayerLock(layer.id)}
                      title={layer.locked ? "解锁图层" : "锁定图层"}
                    >
                      {layer.locked ? "🔒" : "🔓"}
                    </button>
                    <input
                      key={`${layer.id}-${layer.name ?? ""}`}
                      className="layer-name"
                      defaultValue={layer.name ?? layer.id}
                      onBlur={(event) => renameLayer(layer.id, event.target.value)}
                      onKeyDown={(event) => {
                        if (event.key === "Enter") event.currentTarget.blur();
                      }}
                      title="点击重命名"
                    />
                    <span className="layer-actions">
                      <button
                        type="button"
                        onClick={() => moveLayer(layer.id, -1)}
                        disabled={layerIndex === 0}
                        title="上移图层"
                      >
                        ↑
                      </button>
                      <button
                        type="button"
                        onClick={() => moveLayer(layer.id, 1)}
                        disabled={layerIndex === doc.layers.length - 1}
                        title="下移图层"
                      >
                        ↓
                      </button>
                      <button
                        type="button"
                        onClick={() => duplicateLayer(layer.id)}
                        title="复制图层"
                      >
                        ⧉
                      </button>
                      <button
                        type="button"
                        onClick={() => mergeLayerDown(layer.id)}
                        disabled={layerIndex === 0}
                        title="向下合并图层"
                      >
                        ⤓
                      </button>
                      <button
                        type="button"
                        onClick={() => deleteLayer(layer.id)}
                        disabled={doc.layers.length <= 1}
                        title="删除图层"
                      >
                        ×
                      </button>
                    </span>
                  </div>
                  {layer.objects.map((obj) => (
                    <button
                      key={obj.id}
                      type="button"
                      className={`object-row ${selectedIds.includes(obj.id) ? "is-selected" : ""} ${obj.hidden ? "is-hidden" : ""} ${obj.locked ? "is-locked" : ""}`}
                      onClick={(event) => select(obj.id, event.shiftKey)}
                    >
                      <span
                        className="swatch"
                        style={{ background: obj.color.hex }}
                        aria-hidden="true"
                      />
                      <span className="object-meta">
                        <strong>{obj.stitch.type}</strong>
                        <span>
                          {obj.id}
                          {obj.hidden ? " · 隐藏" : ""}
                          {obj.locked ? " · 锁定" : ""}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              ))
            ) : (
              <p className="hint">导入的文件不可编辑；点击“新建示例”开始。</p>
            )}
          </section>

          {selected ? (
            <section>
              <h2>
                对象属性
                {selectedIds.length > 1 ? ` · 已选 ${selectedIds.length}` : ""}
              </h2>
              <div className="field-row">
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(selected.hidden)}
                    onChange={(event) =>
                      updateObject(selected.id, { hidden: event.target.checked })
                    }
                  />
                  <span>隐藏（不生成针迹）</span>
                </label>
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={Boolean(selected.locked)}
                    onChange={(event) =>
                      updateObject(selected.id, { locked: event.target.checked })
                    }
                  />
                  <span>锁定画布编辑</span>
                </label>
              </div>
              <div className="field">
                <label htmlFor="color">颜色</label>
                <input
                  id="color"
                  type="color"
                  value={selected.color.hex}
                  onChange={(event) => setColor(event.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor="stitch">针法</label>
                <select
                  id="stitch"
                  value={selected.stitch.type}
                  onChange={(event) =>
                    updateStitch(selected.id, {
                      type: event.target.value as "fill" | "running" | "satin",
                    })
                  }
                >
                  <option value="fill">填充 Fill</option>
                  <option value="running">走线 Running</option>
                  <option value="satin">缎面 Satin（需双轨线）</option>
                </select>
              </div>
              {selected.stitch.type === "fill" ? (
                <>
                  <div className="field">
                    <label htmlFor="spacing">行距 mm</label>
                    <input
                      id="spacing"
                      type="number"
                      step="0.05"
                      min="0.1"
                      max="2"
                      value={selected.stitch.rowSpacingMm ?? ""}
                      placeholder="面料默认"
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          rowSpacingMm: event.target.value
                            ? Number(event.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="angle">角度 °</label>
                    <input
                      id="angle"
                      type="number"
                      step="5"
                      min="-180"
                      max="180"
                      value={selected.stitch.angleDeg ?? 0}
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          angleDeg: Number(event.target.value),
                        })
                      }
                    />
                  </div>
                </>
              ) : null}
              {selected.stitch.type === "running" ? (
                <>
                  <div className="field">
                    <label htmlFor="stitch-length">针距 mm</label>
                    <input
                      id="stitch-length"
                      type="number"
                      step="0.5"
                      min="0.5"
                      max="12"
                      value={selected.stitch.maxStitchLengthMm ?? ""}
                      placeholder="面料默认"
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          maxStitchLengthMm: event.target.value
                            ? Number(event.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="running-width">线宽 mm</label>
                    <input
                      id="running-width"
                      type="number"
                      step="0.1"
                      min="0.1"
                      max="2"
                      value={selected.stitch.runningWidthMm ?? 0.4}
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          runningWidthMm: Number(event.target.value),
                        })
                      }
                    />
                  </div>
                </>
              ) : null}
              {selected.stitch.type === "satin" ? (
                <>
                  <div className="field">
                    <label htmlFor="satin-density">缎面密度 mm</label>
                    <input
                      id="satin-density"
                      type="number"
                      step="0.05"
                      min="0.2"
                      max="1.5"
                      value={selected.stitch.satinDensityMm ?? ""}
                      placeholder="面料默认"
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          satinDensityMm: event.target.value
                            ? Number(event.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>
                  <div className="field">
                    <label htmlFor="pull-comp">拉布补偿 mm</label>
                    <input
                      id="pull-comp"
                      type="number"
                      step="0.05"
                      min="0"
                      max="2"
                      value={selected.stitch.pull_compensation_mm ?? ""}
                      placeholder="面料默认"
                      onChange={(event) =>
                        updateStitch(selected.id, {
                          pull_compensation_mm: event.target.value
                            ? Number(event.target.value)
                            : undefined,
                        })
                      }
                    />
                  </div>
                </>
              ) : null}
              {selected.stitch.type !== "running" ? (
                <label className="toggle">
                  <input
                    type="checkbox"
                    checked={selected.stitch.underlay !== false}
                    onChange={(event) =>
                      updateStitch(selected.id, {
                        underlay: event.target.checked,
                      })
                    }
                  />
                  <span>打底</span>
                </label>
              ) : null}
              <div className="field-row">
                <div className="field">
                  <label htmlFor="tx">X mm</label>
                  <input
                    id="tx"
                    type="number"
                    step="1"
                    value={selected.translateMm?.[0] ?? 0}
                    onChange={(event) => setNumber("x", event.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="ty">Y mm</label>
                  <input
                    id="ty"
                    type="number"
                    step="1"
                    value={selected.translateMm?.[1] ?? 0}
                    onChange={(event) => setNumber("y", event.target.value)}
                  />
                </div>
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className="button"
                  onClick={duplicateSelected}
                >
                  复制选中
                </button>
                <button
                  type="button"
                  className="button danger"
                  onClick={deleteSelected}
                >
                  删除对象
                </button>
              </div>
              <div className="button-row">
                <button
                  type="button"
                  className={nodeMode ? "button primary" : "button"}
                  onClick={() => setNodeMode((value) => !value)}
                >
                  {nodeMode ? "退出节点编辑" : "节点编辑"}
                </button>
              </div>
              {nodeMode ? (
                <p className="hint">
                  {selectedCurve
                    ? "拖拽方块移动节点，圆形手柄调整曲线。"
                    : "该对象包含弧线或多子路径，暂不支持节点编辑。"}
                </p>
              ) : null}
              {selectedIds.length > 1 ? (
                <p className="hint">
                  多选：属性只改主对象；Delete / Ctrl+D 作用于全部选中。
                </p>
              ) : null}
            </section>
          ) : null}

          <section>
            <h2>工艺校验</h2>
            <div className={`validation ${valid ? "is-ok" : "is-error"}`}>
              {checking
                ? "校验中…"
                : valid
                  ? `通过${issues.length ? `（${issues.length} 条提示）` : ""}`
                  : "有错误，导出已禁用"}
            </div>
            {issues.length ? (
              <ul className="issue-list">
                {issues.slice(0, 8).map((issue, index) => (
                  <li
                    key={`${issue.code}-${index}`}
                    className={issue.severity === "error" ? "error" : "warning"}
                  >
                    {issue.message}
                  </li>
                ))}
              </ul>
            ) : null}
          </section>

          <section>
            <h2>统计</h2>
            <div className="stats">
              <div>
                <span>针数</span>
                <strong>{number.format(plan.stats.stitchCount)}</strong>
              </div>
              <div>
                <span>跳针</span>
                <strong>{number.format(plan.stats.jumpCount)}</strong>
              </div>
              <div>
                <span>换色</span>
                <strong>{number.format(plan.stats.colorChanges)}</strong>
              </div>
              <div>
                <span>幅面</span>
                <strong>{sizeLabel(plan)}</strong>
              </div>
            </div>
          </section>

          <section>
            <h2>显示</h2>
            <div className="playback">
              <button
                type="button"
                className="button"
                onClick={() => {
                  if (stitches.length === 0) return;
                  if (!playing && playIndex >= stitches.length - 1) {
                    setPlayIndex(0);
                  }
                  setPlaying((value) => !value);
                }}
                disabled={!stitches.length}
              >
                {playing ? "暂停" : "播放"}
              </button>
              <input
                type="range"
                min="0"
                max={Math.max(stitches.length - 1, 0)}
                value={Math.min(playIndex, Math.max(stitches.length - 1, 0))}
                onChange={(event) => {
                  setPlaying(false);
                  setPlayIndex(Number(event.target.value));
                }}
              />
              <select
                value={playSpeed}
                onChange={(event) => setPlaySpeed(Number(event.target.value))}
                aria-label="播放速度"
              >
                <option value={60}>慢</option>
                <option value={240}>中</option>
                <option value={600}>快</option>
              </select>
              <span className="playback-count">
                {stitches.length ? playIndex + 1 : 0}/{stitches.length}
              </span>
            </div>
            <label className="toggle">
              <input
                type="checkbox"
                checked={showJumps}
                onChange={(event) => setShowJumps(event.target.checked)}
              />
              <span>显示跳针路径</span>
            </label>
            <label className="toggle">
              <input
                type="checkbox"
                checked={!previewTopOnly}
                onChange={(event) => setPreviewTopOnly(!event.target.checked)}
              />
              <span>显示打底（仅影响预览）</span>
            </label>
            <p className="hint">
              滚轮缩放，拖拽空白平移，拖拽对象移动；Shift+点击多选，拖动任一选中对象整体移动。
              快捷键：Ctrl+Z/Y 撤销重做，Delete 删除，Ctrl+D 复制，方向键微移（Shift 10mm）。
            </p>
          </section>
        </aside>

        <main
          className="stage"
          onDrop={onDrop}
          onDragOver={(event) => event.preventDefault()}
        >
          <StitchCanvas
            plan={plan}
            hidden={hidden}
            showJumps={showJumps}
            fitToken={fitToken}
            doc={doc}
            selectedId={selectedId}
            selectedIds={selectedIds}
            nodeMode={nodeMode}
            drawMode={drawMode}
            activeStitch={activeStitch}
            onSelect={select}
            onMoveMany={setTranslations}
            onPath={setPath}
            onDraw={addFreehand}
          />
          {error ? (
            <div className="banner error" role="alert">
              <strong>操作失败</strong>
              <span>{error}</span>
              <button type="button" onClick={() => setError(null)}>
                关闭
              </button>
            </div>
          ) : null}
        </main>
      </div>

      <footer className="statusbar">
        <span>{doc ? `${doc.layers.length} 层` : "导入模式"}</span>
        <span>{doc ? `${allObjects(doc.layers).length} 个对象` : "不可编辑"}</span>
        <span>{plan.stats.stitchCount.toLocaleString()} 针</span>
        <span>{sizeLabel(plan)}</span>
        <span className="statusbar-note">
          Phase 2 · 拖拽对象 / 参数重算 / 撤销重做
        </span>
      </footer>
    </div>
  );
}
