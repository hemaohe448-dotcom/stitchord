import { useRef, useState } from "react";
import type { ChangeEvent, DragEvent } from "react";
import type { StitchPlan } from "@stitchord/contracts";
import { downloadBlob, exportStitch, previewStitch } from "./api";
import { StitchCanvas } from "./canvas/StitchCanvas";
import { useEditorStore } from "./store";

const number = new Intl.NumberFormat("zh-CN");

function sizeLabel(plan: StitchPlan): string {
  const width = plan.bounds.maxX - plan.bounds.minX;
  const height = plan.bounds.maxY - plan.bounds.minY;
  return `${width.toFixed(1)} × ${height.toFixed(1)} mm`;
}

export default function App() {
  const {
    plan,
    hidden,
    showJumps,
    fitToken,
    setPlan,
    toggleBlock,
    setShowJumps,
    requestFit,
  } = useEditorStore();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState("示例花样 · 尚未导入文件");

  async function handleFile(file: File) {
    setBusy(true);
    setError(null);
    try {
      const next = await previewStitch(file);
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

  function onDrop(event: DragEvent<HTMLElement>) {
    event.preventDefault();
    const file = event.dataTransfer.files?.[0];
    if (file) void handleFile(file);
  }

  async function onExport() {
    setBusy(true);
    setError(null);
    try {
      const blob = await exportStitch(plan, "dst");
      downloadBlob(blob, `stitchord-${Date.now()}.dst`);
      setNotice("已导出 DST（经服务端校验）");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : String(cause));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden="true" />
          <div>
            <strong>Stitchord</strong>
            <span className="brand-sub">绣花制版 · Phase 0</span>
          </div>
        </div>
        <div className="topbar-actions">
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
            disabled={busy}
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

          <section className="layers">
            <h2>颜色块 / 图层</h2>
            {plan.colorBlocks.map((block, index) => (
              <button
                key={block.id}
                type="button"
                className={`layer ${hidden[block.id] ? "is-hidden" : ""}`}
                onClick={() => toggleBlock(block.id)}
                aria-pressed={!hidden[block.id]}
              >
                <span
                  className="swatch"
                  style={{ background: block.color.hex }}
                  aria-hidden="true"
                />
                <span className="layer-meta">
                  <strong>
                    {index + 1}. {block.color.name ?? block.color.hex}
                  </strong>
                  <span>
                    {block.stitches.length.toLocaleString()} 针 · {block.color.hex}
                  </span>
                </span>
                <span className="eye" aria-hidden="true">
                  {hidden[block.id] ? "○" : "●"}
                </span>
              </button>
            ))}
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
              滚轮缩放，拖拽平移。预览与导出共用同一份 StitchPlan。
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
        <span>{plan.colorBlocks.length} 个色块</span>
        <span>{plan.stats.stitchCount.toLocaleString()} 针</span>
        <span>{sizeLabel(plan)}</span>
        <span className="statusbar-note">
          Phase 0 · DST 读取 / 导出往返已通过契约测试
        </span>
      </footer>
    </div>
  );
}
