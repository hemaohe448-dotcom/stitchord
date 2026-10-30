# Stitchord

> 面向工业生产的花样制版 Web 平台：从图片 / 矢量稿到可上机的 DST、PES 等绣花文件。

Stitchord 不是 Inkscape 的网页壳，也不是把开源项目简单拼在一起。它由三层组成：

1. **编辑层**：图层 / 对象 / 针迹参数编辑（目标是 Illustrator 式的可控性，不是复刻其 UI），非破坏式改针；
2. **编译层**：把工程文档确定性编译为 Ink/Stitch 可消费的 SVG，再产出针迹计划与机器文件；
3. **智能层**：图像分割 → 矢量化 → 绣法规划（自动制版），以及后续的实物照片针迹反推。

## 当前状态

**Phase 0 已完成；Phase 1 主体完成；Phase 2 编辑器 MVP + Phase 3 基线矢量化进行中。**

已用固定的 Ink/Stitch commit 在无 Inkscape 的进程内跑通
“文档 → SVG → StitchPlan → DST/PES”，支持 fill/running/satin、面料预设、网页拖拽编辑，
以及“图片 → 量化/矢量化 → 绣花文档”的确定性基线。
见 [无头验证](docs/research/inkstitch-headless.md)、[参数依据](docs/reference/parameters.md)、
[矢量化基线](docs/research/vectorization-baseline.md)。

## 目录

```text
apps/web/               # Vite + React 编辑器（Phase 0：针迹查看器骨架）
packages/contracts/     # 跨端契约：StitchPlan / 文档模型类型
services/digitizer/     # Python 打版服务（FastAPI + pyembroidery；Phase 1 接入 Ink/Stitch）
docs/                   # 决策、架构、路线图、协作规范
infra/                  # 本地与部署编排
```

## 快速开始

```bash
# 前端
npm install
npm run dev            # http://localhost:5173

# 打版服务（Python 3.11+，建议独立 venv）
cd services/digitizer
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn app.main:app --reload --port 8000
```

Windows PowerShell 下可参考 [`docs/06-dev-setup.md`](docs/06-dev-setup.md)。
生成针迹（`/v1/digitize`）需要 Python 3.11 + Ink/Stitch，启动方式见该文档 5.1。

## 文档

| 文档 | 内容 |
| --- | --- |
| [00 产品定义](docs/00-overview.md) | 用户、范围、非目标、成功指标 |
| [01 可行性与许可证](docs/01-feasibility.md) | Ink/Stitch / Embroiderly 事实核查、整合方案、法律边界 |
| [02 架构](docs/02-architecture.md) | 系统架构、文档模型、编译契约、API、矢量化流水线 |
| [03 路线图](docs/03-roadmap.md) | P0–P8 阶段、每步验收标准、证据要求 |
| [04 智能体协作手册](docs/04-agent-playbook.md) | 分工、交接、防幻觉、上下文治理 |
| [05 生产质量](docs/05-production-quality.md) | 工业上机要求、验证矩阵、测试缝合 |
| [06 开发环境](docs/06-dev-setup.md) | Windows / 代理 / 依赖安装 |
| [07 GitHub Actions 操作手册](docs/07-github-actions-guide.md) | 小白版：上传仓库、手动跑构建、取结果 |
| [参数依据](docs/reference/parameters.md) | Ink/Stitch + Wilcom + Roidery 的密度/补偿/打底 |
| [机器格式矩阵](docs/reference/machine-formats.md) | 6 种导出格式的字节/针数/线色/读回结果 |
| [验收状态](docs/09-acceptance-status.md) | 已交付 / 未验证 / 生产门禁，一页看清 |
| [工艺单 PDF](services/digitizer/app/worksheet.py) | 预览 + 参数 + 线色顺序 + 估算线量/工时 |
| [ADRs](docs/adr/) | 关键决策记录 |

## 许可证

本项目采用 **GPL-3.0-or-later**。原因与商业影响见 [ADR-0001](docs/adr/0001-license-gpl.md)。
Ink/Stitch 与 Embroiderly 均为 GPL-3.0 系（前者 GPL-3.0，后者 GPL-3.0-or-later）；任何直接复用其代码的分发形态都必须满足 GPL 义务。
