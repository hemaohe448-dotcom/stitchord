# T-0202：Roidery 集成评估（门槛通过后）

状态: doing
负责人: 架构 / 后端
依赖: T-0201（已完成）
对应决策: ADR-0006

## 目标

在“构建成功”的基础上，判断 Roidery 能否作为：

- A. 服务端制版内核（`vectorcraft-cli` / MCP），或
- B. 浏览器编辑器内核（`vectorcraft-web` WASM），或
- C. 仅继续作为 UX/参数参考。

## 非目标

- 不修改 Roidery 源码；
- 不替换现有 Ink/Stitch 运行时；
- 不做完整 UI 集成或上机试缝。

## 输入

- Roidery commit `0187f73daf2b5b05ff9e88cacc8c972c6abb9687`
- 构建 run：https://github.com/hemaohe448-dotcom/stitchord/actions/runs/41044768131/job/124026066868
- artifact：`roidery-smoke-dst`（DST 4,721 B）
- 现有 CompileDocument / StitchPlan 契约、`docs/contracts/`

## 验收标准

- [ ] AC1 记录 `vectorcraft-cli --help` / 版本 / 运行所需 DLL/资源；
- [ ] AC2 用 3 个 SVG（fill/running/satin）导出 DST，记录退出码、字节数、耗时、峰值内存；
- [ ] AC3 DST 读回并与 Ink/Stitch 同输入比较：针数、色块、换色、包围盒（允许差异需说明）；
- [ ] AC4 记录 Windows/Linux 可移植性：是否需要 MSVC/图形驱动/wgpu；Linux 容器能否跑；
- [ ] AC5 许可证审计：MIT/Apache 代码与依赖 NOTICE、是否需要分发声明；
- [ ] AC6 给出 A/B/C 决策与理由；若选 A/B，附最小 PoC 计划与回滚方案。

## 证据

- 静态评估：`docs/research/roidery-cli-static.md`（入口、依赖、许可证、CI 元数据）；
- GitHub artifact 下载需认证，本轮未取得 DST 本体；AC2/AC3 仍未完成；
- CLI 输出、DST、读回统计、耗时/内存（待运行）；
- 决策记录（ADR-0006 更新或新 ADR）。

## 风险与未知

- 构建成功不等于运行时无 GPU/显示依赖；
- artifact 未提供 SHA-256，字节级回归需补；
- WASM 版本与 CLI 的代码路径可能不同，不能互相证明。
