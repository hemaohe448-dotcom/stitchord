# 当前状态

- 阶段：**P1 Ink/Stitch 无头编译**（进行中）
- 更新：2026-10-30
- 分支：`main`

## 已完成

- [x] 可行性核查：Ink/Stitch / Embroiderly 的定位、许可证、代码结构；
- [x] 架构决策：自有文档模型 + Ink/Stitch 编译器（ADR-0002）；
- [x] 许可证决策草案：GPL-3.0-or-later（ADR-0001，待确认）；
- [x] 路线图 P0–P8 与可执行验收标准；
- [x] 多智能体协作/防幻觉/上下文规范；
- [x] 前端骨架：DST/PES 导入 → StitchPlan → Canvas 渲染 → 导出 DST；
- [x] 后端骨架：预览 / 校验 / 导出 API；
- [x] 测试：前端 2 个单测，后端 10 个单测/契约测试；
- [x] 构建：`tsc --noEmit`、`vite build` 通过；
- [x] Claude 独立架构评审（`docs/reviews/2026-10-30-architecture-review.md`），阻断项已处置
  （`docs/reviews/2026-10-30-response.md`）；
- [x] **P1 无头验证**：Ink/Stitch 库调用可在无 Inkscape 的进程内生成 StitchPlan + DST；
  10px 矩形 48 针、双色 419 针、输出确定；证据 `docs/research/inkstitch-headless.md`；
- [x] 发现并记录：wxPython 是 import 硬依赖、必须关闭磁盘缓存、plan(px) 与 DST(0.1mm/居中) 的差异。

## 进行中

- [ ] P1 worker 适配层：SVG/文档 → plan JSON + DST，参数映射，12 份黄金语料；
- [ ] 把评审修正提交（DST 12.1 mm、wx 依赖、GPL 措辞、契约测试口径）；
- [ ] 用户确认：Roidery 是什么、GPL 商业边界、目标机型。

## 下一步（按优先级）

1. **T-0101**：Ink/Stitch 无头编译 spike（Docker + 固定 commit + 黄金 SVG）。
2. **T-0102**：矢量化基准集与评测脚本（不依赖 Ink/Stitch，可并行）。
3. **T-0103**：编辑器文档模型 + 命令栈设计（P2 前置）。

## 阻塞 / 风险

| 项 | 影响 | 需要谁 |
| --- | --- | --- |
| Docker / Inkscape 未安装 | T-0101 无法本机验证 | 人类安装或提供 CI runner |
| 无绣花机/打样条件 | 无法完成 P6 生产级验收 | 人类对接打样伙伴 |
| GPL 未确认 | 影响架构与商业设计 | 产品负责人 |
| Roidery 未定位 | 需求可能遗漏 | 用户提供链接/截图 |

## 环境快照

- Node 24.22.1 / npm 11.19.1
- Python 3.14.9（`.pylibs` 本地依赖）；CI 用 3.11
- 代理 `127.0.0.1:7890`
- 前端构建需完全权限（esbuild spawn）
