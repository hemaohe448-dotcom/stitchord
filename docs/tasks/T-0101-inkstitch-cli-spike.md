# T-0101：Ink/Stitch 无头编译 spike

状态: doing
负责人: Builder（Codex/DSH 子代理）
依赖: 无（P1 入口）
对应验收: P1-AC1 … P1-AC8

## 目标

在无 Inkscape GUI 的容器里，用固定 commit 的 Ink/Stitch 把一份 SVG 编译为 DST，并输出 StitchPlan JSON。
证明方案 A（ADR-0002）可行，产出参数映射与黄金语料。

## 非目标

- 不做 Web 编辑器；
- 不覆盖全部绣法/格式；
- 不优化性能；
- 不修改 Ink/Stitch 的绣法算法。

## 输入（只读这些）

- `docs/research/inkstitch-notes.md`
- `docs/contracts/stitch-plan.md`
- `docs/versions.lock.md`
- 研究克隆：`.research/repos/inkstitch/`（只读）
- 现有 `services/digitizer/app/convert.py`（复用计划序列化）

## 步骤

1. 写 `services/digitizer/Dockerfile.inkstitch`：`python:3.11-slim` + 固定 commit 的 Ink/Stitch；
   记录镜像 digest。
2. 确认 CLI：输入方式、`--extension=output`、`--format=dst`、stdout、退出码；把结论写进
   `docs/research/inkstitch-cli.md`（含命令与输出）。
3. 若无法直接调用，改在容器内 import `lib.stitch_plan`；仍失败则记录阻塞并停止，不得伪造。
4. 新增 `stitch_plan_json` 扩展（GPL 补丁）：复用 Ink/Stitch 的 stitch plan 生成，输出契约 JSON。
5. 建 `tests/golden/svg/` 12 份 SVG：running / satin / tatami / underlay / 双色 / 跳针 / 锁针。
6. 写对比脚本：我们的输出 vs Inkscape 原生参考（针数、色块、换色、包围盒、逐针）。
7. 生成 `docs/contracts/inkstitch-params.md`（≥15 个属性，附源码行号）。

## 验收标准

- [ ] AC1 镜像离线可跑，无需 Inkscape GUI；
- [ ] AC2 12 份 SVG × {DST, PES} 成功；针数误差 ≤1%，色块/换色一致，包围盒 ≤0.1 mm；
- [ ] AC3 StitchPlan JSON 通过 `docs/contracts/stitch-plan.schema.json`；与直接导出 DST 的逐针误差 ≤0.05 mm；
- [ ] AC4 连续 3 次编译 SHA-256 一致；
- [ ] AC5 2 万针 P95 ≤ 10 s；
- [ ] AC6 参数映射 ≥15 项，均有 `path:line`；
- [ ] AC7 非法输入返回结构化错误，不崩溃、不产生半成品。

## 证据

- `docs/research/inkstitch-cli.md`（命令 + 输出）
- `artifacts/p1/`（生成的 DST、JSON、对比报告；不入库）
- CI 日志 / 本地命令输出

## 进展（2026-10-30）

已完成步骤 1–4 的“库调用”分支：

- Python 3.11.18 + Ink/Stitch `d225262` + inkex `a887f9d` + wxPython 4.3.2 可导入；
- 直接调用 `node_to_elements → embroider → stitch_groups_to_stitch_plan → write_embroidery_file`，
  不经过 Inkscape 与 `inkstitch.py`；
- 10 px 矩形：1 色块 / 48 针 / DST 662 B；
- 两条彩色路径：2 色块 / 419 针 / DST 1781 B；
- 连续两次运行 DST SHA-256 一致（确定性成立）；
- 新增 `services/inkstitch_worker/worker.py`：扁平 SVG → plan JSON + DST，双色 fixture 通过
  pydantic 契约校验，两次运行 SHA 一致；
- 发现 wxPython 是 import 链硬依赖（tartan + sew_stack），最小惰性化补丁不可行；
- 发现必须关闭 Ink/Stitch 磁盘缓存；plan 为 px，DST 为 0.1 mm 且居中。

证据：`docs/research/inkstitch-headless.md`、`tools/spike/`、`artifacts/p1/`。

**结论**：放弃 CLI 入口，P1 改为“worker 内直接调用库”。剩余：satin/running/underlay、
参数映射、PES、12 份黄金语料、性能与 Linux 镜像。

## 风险与未知

- wxPython/GTK 依赖可能让 import 失败；
- Inkscape 文档模型可能需要额外命名空间；
- `--format` 参数解析依赖 inkex 的 argv 约定；
- 参考输出需要 Inkscape 环境（本机未安装）。
