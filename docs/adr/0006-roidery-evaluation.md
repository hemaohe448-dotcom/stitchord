# ADR-0006：Roidery 的定位——先采用参数模型，编辑器内核设构建门槛

- 状态：接受；Phase 2 构建门槛**已通过**（2026-10-30）
- 日期：2026-10-30
- 相关：ADR-0002、`docs/reference/parameters.md`、`docs/reviews/roidery-build-result.md`

## 背景

用户指认的目标项目是 [`lork-fork/Roidery`](https://github.com/lork-fork/Roidery)：
一个 MIT/Apache-2.0 的 Rust 绣花制版应用，基于 VectorCraft，具备：

- Illustrator 式矢量编辑、图层/Sequencer、节点与缎面块编辑；
- tatami/渐变/轮廓/圆形/motif/guided 填充、缎面、running、E-stitch、字母；
- 面料预设（密度/拉布补偿/打底）、绣框、密度图、真实感预览、Sew-Out；
- DST/PES/JEF/EXP/VP3/XXX/U01 等格式；
- `vectorcraft-cli` 无头批处理、MCP/控制协议、`vectorcraft-web` WASM 版本。

这与用户要的“Illustrator 风格、按图层改针迹”高度重合，且许可证比 Ink/Stitch 更宽松。

## 现实约束

- 仓库没有预编译 release；本地没有 Rust/1.95 工具链或 MSVC linker；
- 工作区很大（完整 VectorCraft + wgpu/egui），首次构建成本高；
- README 明确“early software，量产前必须试缝”；
- 我们的 Ink/Stitch 服务端管线已经跑通（编译、DST/PES、参数、确定性）。

## 决策

1. **立即采用 Roidery 的参数模型与面料预设**（MIT/Apache，注明来源），
   落到 `services/digitizer/app/fabric.py` 与 `docs/reference/parameters.md`；
2. **暂不把 Roidery 作为运行时内核**；继续用 Ink/Stitch worker 交付可验证的
   SVG→StitchPlan→DST 能力；
3. Phase 2 设一个**构建门槛**：在 CI（Windows runner，自带 MSVC）构建
   `vectorcraft-cli`，并跑一个 SVG→DST 的最小用例；
   - 通过：评估用 Roidery 的无头 CLI/MCP 作为服务端制版内核，或嵌入 `vectorcraft-web`；
   - 不通过：继续自研 Web 编辑器，Roidery 仅作 UX/参数参考。
   执行入口：`.github/workflows/roidery-build-gate.yml`；任务单 `docs/tasks/T-0201-roidery-build-gate.md`。
4. 不在本项目复制 Roidery 的 GPL 禁止内容；Roidery 本身是 clean-room，
   我们只使用其 MIT/Apache 代码/数值，并保留 NOTICE。

## Phase 2 门槛结果（2026-10-30）

| 项 | 结果 |
| --- | --- |
| GitHub Actions run | https://github.com/hemaohe448-dotcom/stitchord/actions/runs/41044768131/job/124026066868 |
| 结论 | **成功** |
| 总耗时 | 15m 10s |
| 产物 | DST **4,721 bytes** |
| 失败步骤/日志 | 无 |
| DST SHA-256 | 回填中未提供 |

判定：**仅证明“Windows CI 能构建 `vectorcraft-cli` 并导出非空 DST”**，不证明：

- 与 Ink/Stitch 的针迹/色块/参数等价；
- 性能、稳定性、并发安全；
- GUI/编辑器可用性、许可证边界、可部署性。

## 决策（门槛通过后）

1. 当前运行时**继续用 Ink/Stitch**，不立即替换；现有 CompileDocument/StitchPlan/DST 契约保持；
2. 启动 **T-0202 Roidery 集成评估**：验证无头 CLI/MCP 的输入格式、DST 读回、许可证 NOTICE、
   部署体积与 Windows/Linux 可移植性，再决定“服务端内核”还是“编辑器内核”；
3. 自研 Web 编辑器继续作为默认交付，Roidery 作为并行评估，不阻塞现有路线；
4. 不把“构建成功”写成“生产可用”；真实功能/上机验证仍缺。

## 后果

- 短期交付不被 Rust 构建阻塞；
- 用户喜欢的交互方向被记录，并已用其参数预设改善输出；
- Phase 2 门槛已通过，架构**可以**评估切换到 Roidery 内核（编译器/契约仍是资产），
  但尚未做任何替换；
- 需要明确告知用户：当前网页编辑器是自研，Roidery 的完整编辑体验尚未接入。

## 备选

- 立刻全面 fork Roidery：构建/维护成本与风险最高，且无本地验证条件；
- 完全忽略 Roidery：放弃一个许可证更优、功能更贴近的现成编辑器，不合理。
