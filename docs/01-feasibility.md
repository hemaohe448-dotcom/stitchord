# 01 可行性与许可证

> 核查日期：2026-10-30。所有第三方结论都附 commit / 文件行号；未核实的内容明确标为 `TODO(verify)`。
> 本文不是法律意见；许可证结论需律师复核后才能对外承诺。

## 1. 结论摘要

1. **Ink/Stitch 是唯一成熟、可复用的机器绣花开源内核**：GPL-3.0，Python ≥3.11，Inkscape 扩展架构，覆盖 fill / satin / running / underlay / 命令 / 多格式导出；仍在活跃维护（HEAD `d225262`，2026-10-27）。
2. **Embroiderly 不是机器绣花软件，而是十字绣图纸设计器**：GPL-3.0，Vue + Rust/WASM + Tauri。它的“Illustrator 式图层”体验值得借鉴，但其数据模型是十字绣格子针，不能直接承载 DST 的针迹序列。直接复用其代码会把我们锁进十字绣模型，并触发 GPL 义务。
3. **“图片矢量化 + 精美”不能靠端到端生成模型一把梭**：可落地的是“ML 分割/抠图 + 经典矢量化 + 绣法规划 + 人工微调”。实物照片反推针迹属于 R&D（TRL 3–4），必须单独立项、设 go/no-go，不能写进 MVP 承诺。

## 2. 事实核查

| # | 断言 | 证据 | 置信度 |
| --- | --- | --- | --- |
| F1 | Ink/Stitch 采用 GPL-3.0 | `inkstitch/LICENSE:1-2`；仓库根 LICENSE | 高 |
| F2 | Ink/Stitch 要求 Python ≥3.11，依赖 pystitch / inkex / shapely / wxPython 等 | `inkstitch/pyproject.toml:4-33` | 高 |
| F3 | Ink/Stitch 以 Inkscape 扩展方式运行：`from lib import extensions` 在 `:131` 导入全部扩展，`:137-147` 按 `--extension=<name>` 反射实例化 | `inkstitch/inkstitch.py:131-147` | 高 |
| F4 | 导出扩展把机器文件二进制写到 stdout，由 Inkscape 落盘 | `inkstitch/lib/extensions/output.py:39-75` | 高 |
| F5 | 绣法模块覆盖 running / satin / fill / tatami / contour / guided / meander / ripple / cross-stitch / tartan 等 | `inkstitch/lib/stitches/`（14 个模块） | 高 |
| F6 | `INKSTITCH_OFFLINE_SCRIPT` 只切换调试器/脚本生成路径，**不能**证明官方支持无 GUI 调用 | `inkstitch/inkstitch.py:75-101` | 高（反向证据） |
| F7 | Embroiderly 自我定义为“cross-stitch patterns”桌面应用 | `embroiderly/README.md:5` | 高 |
| F8 | Embroiderly 源码 GPL-3.0-or-later；文档 CC-BY-SA-4.0 | `embroiderly/README.md:24-33` | 高 |
| F9 | Embroiderly 是 web-first：Vue + Wasm + Tauri，核心编辑在 Rust/WASM | `embroiderly/ARCHITECTURE.md:3-37` | 高 |
| F10 | Embroiderly 的图像导入面向十字绣图纸 | `embroiderly/packages/image-import/README.md:3` | 高 |
| F11 | pyembroidery 1.5.1 命令常量：STITCH=0, JUMP=1, TRIM=2, STOP=3, END=4, COLOR_CHANGE=5, NEEDLE_AT=177 | 本机实测，见 `docs/research/pyembroidery-notes.md` | 高 |
| F12 | pyembroidery 内部坐标单位 0.1 mm；写入 DST 后读回可保持 0.1 mm 精度 | 本机 round-trip 测试 `services/digitizer/tests/test_convert.py` | 高 |
| F13 | 扩展包 import 时即加载 wxPython（`params.py:15`），因此无 wx 的容器会在导入阶段失败 | `inkstitch/lib/extensions/__init__.py:6-20`、`lib/extensions/params.py:15` | 高 |
| F14 | DST 单条记录最大位移 121 × 0.1 mm = 12.1 mm | `pyembroidery/DstWriter.py:7-8` | 高 |

### 关于 Roidery（已定位）

用户指认的项目是 [`lork-fork/Roidery`](https://github.com/lork-fork/Roidery)（commit `0187f73`，2026-10-20）：

- **MIT OR Apache-2.0**，Rust，基于 VectorCraft（Illustrator 式矢量编辑）；
- 具备图层/Sequencer、填充/缎面/running/字母、面料预设、绣框、DST/PES/JEF/EXP/VP3/XXX 导出；
- 有 `vectorcraft-cli` 无头批处理、MCP/控制协议，以及 `vectorcraft-web`（WASM）版本；
- 明确标注 early software，量产前必须试缝；
- 仓库无预编译 release；本机没有 Rust/MSVC 工具链，暂不能本地构建验证。

结论：Roidery 是比 Ink/Stitch 更贴近“Illustrator 式编辑器”的候选，但当前无法在本机构建，
且完整接入（Rust/WASM + 账户/项目）是独立工程。见 [ADR-0006](adr/0006-roidery-evaluation.md)。

## 3. 三个项目怎么定位

| 项目 | 真实定位 | 可复用 | 不可复用 / 风险 |
| --- | --- | --- | --- |
| Ink/Stitch | Inkscape 里的机器绣花制版平台 | 绣法算法、针迹计划、机器格式 IO、参数体系、线色目录、测试语料 | 不能直接做 Web 编辑器；强依赖 Inkscape 文档模型；GPL |
| Embroiderly | 十字绣图纸设计器（web-first） | 图层交互、画布性能方案、WASM 计算分层、工程化程度 | 数据模型是十字绣格针；不是 DST 针迹编辑器；GPL |
| Roidery | Illustrator 式 Rust 绣花制版应用（VectorCraft fork） | 图层/Sequencer、绣法、面料预设、格式、无头 CLI/MCP | 早期软件、无 release、需 Rust 构建；完整 Web 接入成本高 |

**给用户的直说**：你喜欢的“Illustrator 风格”是一种交互目标，但**没有证据表明 Embroiderly 实现了
机器绣花式的图层针迹编辑**——它的 `ARCHITECTURE.md:30` 里的 “layers” 指的是软件分层，不是绣花图层。
因此我们借鉴的是“图层化编辑”的产品方向，而不是它的实现；不能把 Embroiderly 当机器绣花编辑器直接用。
我们要做的是“Illustrator 式图层 + Ink/Stitch 的针迹内核”，这是一个新的编辑器，而不是换皮。

## 4. 整合方案对比

### 方案 A（推荐）：自有文档模型 + Ink/Stitch 作为“编译器”

```text
Stitchord 文档(JSON) --compile--> Ink/Stitch SVG --Ink/Stitch CLI--> StitchPlan + DST/PES...
```

- Ink/Stitch 跑在独立 Python worker 容器里，锁定 commit；
- 我们维护 JSON → SVG 的确定性编译器（参数映射表 + 契约测试）；
- 需要针迹计划 JSON 时，在 worker 内加一个很小的 GPL 扩展（读 StitchPlan 并序列化），补丁公开；
- 升级 Ink/Stitch = 升级镜像 + 跑回归语料，不污染业务代码。

优点：边界清晰、可测试、可替换；缺点：要维护参数映射，初期只能覆盖常用绣法。

### 方案 B：把 Ink/Stitch 当库 fork 进后端

- 直接 import `lib.stitch_plan` / `lib.elements`，绕过 Inkscape；
- 升级困难、与 inkex 文档对象强耦合、测试面大；
- 仅作为方案 A 中“生成 StitchPlan JSON”的容器内实现细节，不作为系统边界。

### 方案 C：自研制版内核

- 需要重写绣法、顺序、补偿、格式、机器适配；以人年计；
- 不现实作为起点，但可作为长期“去 GPL 化”的备选（成本极高）。

**决策：A。** 详见 [ADR-0002](adr/0002-own-doc-model-inkstitch-compiler.md)。

## 5. 许可证与商业化

- Ink/Stitch：GPL-3.0；Embroiderly：GPL-3.0-or-later。
- **SaaS 不构成 GPL 的“分发”**；但以下行为会触发义务：向客户交付含 Ink/Stitch 的私有化镜像、
  分发修改过的 Ink/Stitch 二进制、把 GPL 模块 import 进同一进程形成结合作品。
- Python 没有 C 语言意义上的“静态链接”；判断边界看是否同一进程、是否共享数据结构、是否构成
  衍生作品。**独立进程 + 文件/JSON 契约**是目前较可辩护的隔离方式，但仍需律师逐案确认。
- 我们自己的代码选择 **GPL-3.0-or-later**：可以直接复用/修改 GPL 生态，法律路径最简单；
  商业化靠托管服务、支持、模板与算力，而不是靠闭源许可证。
- **贡献者授权**：仓库目前没有 CLA/DCO。若未来需要重新授权（例如闭源双许可），必须现在就加
  DCO/CLA，否则无法单方面改变已合并贡献的许可证。
- 如果未来必须闭源：自有编辑器/编译器可以保持专有（前提是未复制 GPL 代码），Ink/Stitch 继续作为
  独立进程且不随产品分发；若必须随私有化交付，则整个分发包需满足 GPL。**不需要“重写编辑器”**，
  但需要严格审计代码来源与模型许可证。
- ML 模型/权重也要做许可证审计（例如部分分割/抠图模型禁止商用）；未确认前不得进入生产链路。

> 待人类确认：商业模式是否允许 GPL？若投资方要求闭源，请在 Phase 0 决策，否则后期返工成本极高。

## 6. 矢量化与“精美”的技术现实

### 6.1 能稳定工作的

| 环节 | 方案 | 成熟度 | 说明 |
| --- | --- | --- | --- |
| 主体抠图 | BiRefNet / RMBG 类模型 | 高 | 电商图、白底图效果好；复杂背景需 SAM |
| 区域分割 | SAM 2 / SAM 自动掩码 + 颜色聚类 | 高 | 得到语义区域，仍需人工合并/修正 |
| 轮廓矢量化 | vtracer / potrace | 高 | 快、确定性好；产生节点多，需要简化 |
| 曲线拟合 / 简化 | RDP + 三次贝塞尔拟合 | 高 | 控制节点数与最小特征宽度 |
| 矢量化优化 | diffvg 可微渲染 | 中 | 用像素损失微调曲线，适合 logo |
| 绣法分类 | 宽度/长宽比/骨架分析 | 中 | 大面→tatami，细长→satin，线→running |

> 上表的“成熟度”是工程判断，不是 E2/E3 证据；进入 P3 前必须用基准集实测。
> `TODO(verify)`：SAM2 / BiRefNet / RMBG 等模型与权重的许可证（有的限制商用），未确认不得上线。

### 6.2 不能直接用的

- **端到端 image→SVG 生成模型**（StarVector / OmniSVG / 各类 “SVG-LLM”）：能生成“像”的图，
  但尺寸、拓扑、文字、Logo 细节不可靠；对生产制版是不可接受的幻觉源。
  可作为“风格建议”，不能作为几何真相。
- **“任意照片一键出精品 DST”**：目前没有成熟开源方案。照片里有透视、褶皱、反光、遮挡，
  针迹互相覆盖，颜色受光照影响；反推针序本质上是病态逆问题。

### 6.3 可交付的质量定义

“精美”必须可测量，否则无法验收：

1. 区域 IoU ≥ 0.90（对人工矢量化参考）；
2. 轮廓 Chamfer 距离 ≤ 0.3 mm；
3. 最小特征宽度 ≥ 0.8 mm（低于则合并/删除，避免烂针）；
4. 自动初稿的人工修改时间 ≤ 10 分钟（对 80% 基准图）；
5. 试缝样片人工评分 ≥ 4/5，返工率 < 20%。

### 6.4 实物照片 → 针迹（Phase 7，R&D）

可行路径：先做“照片 → 矢量化 → 制版”（今天就能工作），再研究“照片 → 针迹反推”。

研究路线：
1. 采集配对数据：已知 DST → 实际缝合 → 多角度/多光照拍照（≥50 组）；
2. 图像矫正 / 去褶皱 / 线迹增强；
3. 针脚检测（方向滤波 + 分割网络）与线色聚类；
4. 图结构追踪得到候选针迹，再做序列推断；
5. 以 Chamfer 距离、stitch-level F1、色块数误差评估；F1 的匹配规则必须预先定义
   （建议：同色块内，预测针与参考针端点距离 ≤ 1.0 mm 且方向差 ≤ 30° 记为匹配）；
6. 50 组数据只够“评测/可行性”，不足以训练大模型；需要时另行扩采；
7. 达不到阈值就明确停止，不把 R&D 包装成功能。

## 7. 能力缺口（需要自研）

| 能力 | 现状 | 自研内容 |
| --- | --- | --- |
| Web 图层编辑器 | 无现成可用的机器绣花版 | 文档模型、命令栈、画布渲染、命中测试 |
| JSON → Ink/Stitch SVG 编译器 | 无 | 参数映射、单位换算、确定性输出、回归语料 |
| 自动绣法规划 | Ink/Stitch 有绣法，无“从图自动选绣法” | 区域分类、方向场、密度/补偿策略 |
| 生产校验 | Ink/Stitch 有部分检查 | 规则引擎、机型配置、分框、工艺单 |
| 照片反推 | 无成熟方案 | 数据集 + 模型 + 评测（R&D） |

## 8. 待决问题（Phase 0 必须回答）

1. ~~Roidery 到底是什么？~~ 已定位：`lork-fork/Roidery`（MIT/Apache）。
2. ~~商业上能否接受 GPL-3.0？~~ 已确认接受（仅服务端调用、不售卖代码）。
3. 首批目标机型与幅面（Brother / Tajima / Barudan；单头 / 多头）？
4. 是否有真实绣花机与打样条件（决定“生产级”验收能否闭环）？
5. 部署形态：公有云 SaaS、私有化、还是两者都要？
6. 是否投入 Rust/WASM 构建链，把 Roidery 的编辑器内核接进来（Phase 2 门槛）？
