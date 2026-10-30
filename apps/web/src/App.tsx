import { useEffect, useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import type { StitchPlan } from "@stitchord/contracts";
import {
  downloadBlob,
  digitizeDocument,
  digitizeExport,
  exportStitch,
  previewStitch,
  vectorizeImage,
} from "./api";
import { StitchCanvas } from "./canvas/StitchCanvas";
import { parsePolyline } from "./path";
import { FABRICS } from "./sampleDoc";
import type { CompileDocument, CompileObject } from "./sampleDoc";
import { useEditorStore } from "./store";

const number = new Intl.NumberFormat("zh-CN");

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

export default function App() {
  const {
    doc,
    plan,
    selectedId,
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
    setPath,
    addRectangle,
    addLine,
    duplicateSelected,
    deleteSelected,
    moveLayer,
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
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("示例工程 · 正在生成针迹…");

  const selected = doc
    ? allObjects(doc.layers).find((obj) => obj.id === selectedId)
    : undefined;
  const selectedPolyline = selected ? parsePolyline(selected.pathD) : null;

  useEffect(() => {
    if (!doc) return;
    let cancelled = false;
    const timer = window.setTimeout(async () => {
      setGenerating(true);
      try {
        const next = await digitizeDocument(doc);
        if (cancelled) return;
        setPlan(next);
        setNotice(
          `已生成 · ${doc.fabric ?? "woven"} · ${next.stats.stitchCount.toLocaleString()} 针`,
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
  }, [doc, setPlan]);

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
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
      const result = await vectorizeImage(file, 100, 8);
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
        const object = state.doc.layers
          .flatMap((layer) => layer.objects)
          .find((obj) => obj.id === state.selectedId);
        if (!object) return;
        const step = event.shiftKey ? 10 : 1;
        const [x, y] = object.translateMm ?? [0, 0];
        const next: [number, number] = [
          x + (event.key === "ArrowRight" ? step : event.key === "ArrowLeft" ? -step : 0),
          y + (event.key === "ArrowDown" ? step : event.key === "ArrowUp" ? -step : 0),
        ];
        state.setTranslate(object.id, next, true);
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
      const blob = doc
        ? await digitizeExport(doc)
        : await exportStitch(plan, "dst");
      downloadBlob(blob, `stitchord-${Date.now()}.dst`);
      setNotice(doc ? "已导出 DST（Ink/Stitch）" : "已导出 DST（经服务端校验）");
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
            className="button primary"
            onClick={() => void onExport()}
            disabled={busy || generating}
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
              accept=".dst,.pes,.exp,.jef,.vp3,.xxx"
              onChange={onPick}
              hidden
            />
            <p className="hint">{notice}</p>
          </section>

          <section>
            <h2>工程</h2>
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
              {generating ? "正在重新生成针迹…" : "修改后自动重新编译"}
            </p>
          </section>

          <section className="layers">
            <h2>图层 / 对象</h2>
            {doc ? (
              doc.layers.map((layer, layerIndex) => (
                <div className="layer-group" key={layer.id}>
                  <div className="layer-head">
                    <strong>{layer.name ?? layer.id}</strong>
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
                    </span>
                  </div>
                  {layer.objects.map((obj) => (
                    <button
                      key={obj.id}
                      type="button"
                      className={`object-row ${selectedId === obj.id ? "is-selected" : ""}`}
                      onClick={() => select(obj.id)}
                    >
                      <span
                        className="swatch"
                        style={{ background: obj.color.hex }}
                        aria-hidden="true"
                      />
                      <span className="object-meta">
                        <strong>{obj.stitch.type}</strong>
                        <span>{obj.id}</span>
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
              <h2>对象属性</h2>
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
                  复制对象
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
                  {selectedPolyline
                    ? "拖拽方块移动节点；曲线/多子路径对象暂不支持。"
                    : "该对象含曲线或多子路径，暂不支持节点编辑。"}
                </p>
              ) : null}
            </section>
          ) : null}

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
            <label className="toggle">
              <input
                type="checkbox"
                checked={showJumps}
                onChange={(event) => setShowJumps(event.target.checked)}
              />
              <span>显示跳针路径</span>
            </label>
            <p className="hint">
              滚轮缩放，拖拽空白平移，拖拽对象移动。快捷键：Ctrl+Z/Y 撤销重做，Delete 删除，
              Ctrl+D 复制，方向键微移（Shift 10mm）。
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
            nodeMode={nodeMode}
            onSelect={select}
            onMove={setTranslate}
            onPath={setPath}
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
