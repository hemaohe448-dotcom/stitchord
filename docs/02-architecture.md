# 02 架构

## 1. 架构原则

1. **单一几何真相**：预览、导出、统计都来自同一份 `StitchPlan`；禁止“预览一套、导出另一套”。
2. **文档与针迹分离**：工程文档保存“意图”（路径、图层、绣法参数），针迹计划是派生结果，可重算、可缓存。
3. **确定性编译**：同一文档 + 同一版本 = 同一字节输出；时间戳、随机数、哈希顺序不得进入几何。
4. **毫米制**：内部一律 mm；SVG 的 px 换算集中在一个模块（96 dpi），DST 的 0.1 mm 只在 IO 边界出现。
5. **进程隔离 GPL 内核**：Ink/Stitch 只存在于 worker 容器，通过文件/JSON 契约交互，不链接进业务代码。
6. **可替换**：编译器、矢量化器、导出器都是带契约的适配器；任何一层都能被替换或降级。

## 2. 系统上下文

```text
┌──────────────────────────── Browser ────────────────────────────┐
│ React 编辑器                                                     │
│  ├─ 文档状态（图层/对象/参数）  ├─ 画布渲染（Canvas/WebGL）        │
│  ├─ 命令栈（undo/redo）         └─ StitchPlan 预览                │
└───────────────┬─────────────────────────────────────────────────┘
                │ HTTPS / JSON / multipart
┌───────────────▼─────────────────────────────────────────────────┐
│ API（FastAPI 模块化单体）                                         │
│  auth · projects · assets · jobs · exports · billing(后置)       │
└───┬───────────────┬───────────────────┬─────────────────────────┘
    │               │                   │
┌───▼────┐   ┌──────▼──────┐   ┌────────▼─────────┐
│Postgres│   │ S3 / MinIO  │   │ Redis（队列/缓存）│
└────────┘   └─────────────┘   └────────┬─────────┘
                                        │
                    ┌───────────────────┼────────────────────┐
                    │                   │                    │
          ┌─────────▼────────┐ ┌────────▼─────────┐ ┌────────▼─────────┐
          │ digitizer worker │ │ vectorizer worker│ │ render/export    │
          │ Ink/Stitch 固定版 │ │ SAM2/BiRefNet/   │ │ PNG/PDF/工艺单    │
          │ pyembroidery      │ │ vtracer (GPU)    │ │                  │
          └──────────────────┘ └──────────────────┘ └──────────────────┘
```

Phase 1 已实现：浏览器针迹查看/生成 + digitizer 的 DST 读取/导出/校验 + 文档→SVG→StitchPlan/DST
（`/v1/digitize`，需 Python 3.11 + Ink/Stitch）；队列、数据库、多租户在后续阶段接入。

## 3. 仓库结构

```text
apps/web/                 React 19 + Vite 编辑器
packages/contracts/       StitchPlan / 文档模型 TS 类型与校验
services/digitizer/       FastAPI + pyembroidery（Phase 1 加 Ink/Stitch）
services/api/             （Phase 4）业务 API：账户、项目、任务、计费
services/vectorizer/      （Phase 3）分割/矢量化 worker
infra/                    docker-compose、部署清单
docs/                     决策与契约
```

Phase 0 把 digitizer 作为唯一后端；Phase 4 再拆出独立业务 API，避免过早微服务化。

## 4. 文档模型

```text
Project
└── Artwork（画布：宽高 mm、hoop、背景）
    ├── Layer（顺序、可见、锁定、默认线色）
    │   └── Object（路径 / 组 / 文字 / 位图源）
    │       ├── color:     线色（权威值；Layer 默认色可被覆盖）
    │       ├── geometry:  贝塞尔路径（mm，Y 向下）
    │       ├── stitch: { type, angleDeg, rowSpacingMm, densityMm,
    │       │            underlay, pullCompMm, minStitchMm, tieIn, tieOff }
    │       └── source:    可选，指向原始位图/矢量化任务
    └── Metadata（作者、机型、线色目录、版本）
```

规则：
- **颜色在 Object 上**，Layer 只提供默认值；一个 Object 产生一个颜色块。
- 一个 Object 只产生一个颜色块；同色对象可在导出时合并（由 sequencer 决定）。
- `rowSpacingMm` 是填充行距，`densityMm` 是缎面/针脚间距，两者不可混用。
- 画布必须落在声明的 hoop 内；超出时必须走“分框”流程（Phase 5），否则校验拒绝。
- 图层顺序即默认缝制顺序；`sequencer` 可重排以减少换色/跳针，但必须可解释、可回退。
- 当前工程格式：**普通 JSON**（无 zip、无 `schemaVersion`/迁移；计划 P4 再升级为 `.stitchord` 包）。
- 文档**不存生成后的针迹**；只存缓存 hash，缓存失效即重算。

文档示例（节选）：

```json
{
  "schemaVersion": "1.0",
  "artwork": { "widthMm": 100, "heightMm": 100, "hoop": "100x100" },
  "layers": [
    {
      "id": "layer-1",
      "name": "花瓣",
      "defaultColor": { "hex": "#dd6b20" },
      "objects": [
        {
          "id": "obj-1",
          "kind": "path",
          "color": { "hex": "#dd6b20", "brand": "Isacord", "code": "1104" },
          "geometry": { "closed": true, "nodes": [] },
          "stitch": { "type": "satin", "angleDeg": 45, "densityMm": 0.4 }
        }
      ]
    }
  ]
}
```

## 5. 编译契约（核心风险点）

### 5.1 流程

```text
Document(JSON)
  └─ compile_svg()  →  Ink/Stitch 兼容 SVG（96dpi，带参数属性）
        └─ worker: inkstitch --extension=output --format=dst  →  DST 字节
        └─ worker: stitch_plan_json 扩展                     →  StitchPlan JSON（权威）
```

**单一真相**：`StitchPlan` 由 worker 内的 Ink/Stitch 管线生成一次；预览与导出都消费这一份计划。
pyembroidery 只用于导入、round-trip 验证与独立回归，不作为第二条生产导出路径。
**已记录例外**：JEF 因 pystitch writer 不可读回而回退 pyembroidery（见 `docs/reference/machine-formats.md`）；
机器文件导入仍走 pyembroidery 读入，不参与“文档→机器文件”主链路。
若两者的 DST 字节出现差异，以 Ink/Stitch 产物为准并调查差异，不得并行维护两套几何。

### 5.2 规则

- **参数属性名不得凭记忆写**。Phase 1 的第一件事是从 Ink/Stitch 源码与 `.inx` 文件中提取
  真实属性名/默认值/单位，生成 `docs/contracts/inkstitch-params.md` 与映射表，并用契约测试锁定。
- **wxPython 风险**：`lib/extensions/__init__.py` 会 import 全部扩展，其中 `params.py:15` 顶层
  `import wx`。因此“无 Inkscape GUI”不等于“无 wx/GTK 依赖”；镜像必须安装 wxPython/GTK，或对
  扩展加载做惰性化补丁。P1 必须先验证这一点（T-0101）。
- 单位换算只允许在 `compile_svg` 一处发生；任何模块不得硬编码 96 / 25.4。
- 输出的 SVG 必须能被固定版本的 Ink/Stitch 读取；解析失败要返回可定位的错误（元素 id + 原因）。
- 针迹计划 JSON 通过在 worker 内新增一个只读扩展实现（GPL，补丁公开），不改 Ink/Stitch 的绣法逻辑。
- 每次编译记录：文档 hash、编译器版本、Ink/Stitch commit、参数快照、输出 hash。
- 机器文件内**不得**写入时间戳；DST 头里的名称必须固定/来自文档 id，否则字节级回归失效。

### 5.3 契约测试（Phase 1 验收核心）

输入是**黄金 JSON 文档**，不是 SVG（SVG 是被测编译器的输出）。每份用例包含：

- `input.json`：图层/对象/绣法参数；
- `reference.svg`：人工确认过的 Ink/Stitch 兼容 SVG；
- `reference.dst`：用参考环境（Inkscape + 固定 Ink/Stitch）导出的 DST。

验证链：
1. `compile_svg(input.json)` 与 `reference.svg` 的结构/参数等价（属性级对比）；
2. 编译产物与 `reference.dst` 比较：针数、色块数、换色数、包围盒（同 writer 时要求 ≤0.1 mm）；
3. 同一 writer 下逐针坐标比较：按 0.1 mm 量化后必须**完全一致**（不是 0.05 mm 容差，
   因为 0.05 mm 小于 DST 分辨率）；
4. 不同 writer（Ink/Stitch vs pyembroidery）只比较针数/色块/换色与包围盒，并允许 ≤1% 针数差；
   逐针坐标不跨 writer 比较；
5. 连续 3 次编译输出字节级一致（固定 DST 头名称，排除时间戳）。

任何一项不达标即阻断合并。

## 6. 渲染与编辑器

### 6.1 渲染

- Phase 0：Canvas 2D 批量 path；单画布 10 万针可接受，先验证交互。
- Phase 2：若帧率不达标，切 PixiJS/WebGL（线段批处理 + 实例化），DOM/SVG 只做选中框与控制柄。
- 坐标：世界 mm → 屏幕 px 的仿射变换集中在 `canvas/transform.ts`；渲染与命中测试共用。
- 大文档：按颜色块/空间索引（rbush）裁剪；离屏 worker 做镶嵌与简化。

### 6.2 编辑交互（Phase 2）

- 图层树：显示/隐藏/锁定/排序/合并/改色；
- 对象：选择、节点编辑、布尔运算（服务端 shapely 或 WASM）、变换；
- 针迹参数：绣法、角度、行距、密度、打底、补偿、起收针、锁针；
- 命令栈：所有修改走 command，支持 100 步 undo/redo；
- 重新生成：只重算受影响对象；生成中显示 stale 标记，不阻塞编辑。

## 7. API（Phase 1 已实现 + 规划）

| 方法 | 路径 | 状态 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | ✅ | 健康检查 |
| POST | `/v1/stitch/preview` | ✅ | 上传 DST/PES/… → StitchPlan |
| POST | `/v1/stitch/validate` | ✅ | 静态规则校验 |
| POST | `/v1/stitch/export` | ✅ | StitchPlan → DST/EXP/… |
| POST | `/v1/stitch/check` | ✅ P2 | 静态规则 + 绣框适配校验 |
| POST | `/v1/worksheet` | ✅ P5 | StitchPlan → A4 工艺单 PDF |
| POST | `/v1/digitize` | ✅ P1 | CompileDocument → StitchPlan（Ink/Stitch） |
| POST | `/v1/digitize/export` | ✅ P1 | CompileDocument → DST 字节（确定性） |
| POST | `/v1/projects` | P4 | 创建工程 |
| GET/PUT | `/v1/projects/{id}` | P4 | 读取/保存文档 |
| POST | `/v1/assets` | P4 | 上传原图，返回签名 URL |
| POST | `/v1/vectorize` | ✅ P3 基线 | 图片 → CompileDocument（vtracer，无 ML） |
| GET | `/v1/jobs/{id}` | P4 | 任务状态 / 进度 / 错误 |
| POST | `/v1/exports` | P5 | 导出并写入对象存储 |

约定（**目标态，当前未实现**）：
- 所有写接口支持 `Idempotency-Key`；
- 任务异步化，返回 `jobId`，通过 SSE/WebSocket 推送进度；
- 错误统一 `{code, message, details, traceId}`；
- 上传限制 15 MB（当前实现），后续按套餐调整。

## 8. 矢量化流水线（Phase 3）

```text
upload
 → 预处理（EXIF、去背景可选、超分可选）
 → 分割（SAM2 自动掩码 / 颜色聚类 / 文本提示）
 → 区域合并与层级（遮挡关系）
 → 矢量化（vtracer 彩色 / potrace 二值）
 → 简化与拓扑修复（RDP、曲线拟合、自交清理、最小宽度）
 → 绣法分类（宽度/骨架/长宽比）
 → 参数化（角度、行距、密度、打底、补偿）
 → StitchPlan 预览 → 人工修正 → 导出
```

设计要点：
- 分割结果与矢量结果都保留“可回溯到原图区域”的 id，便于用户点选修正；
- 每个阶段可单独重跑；中间结果落对象存储，避免重复 GPU 计算；
- 质量门槛不达标时**明确告知**，不偷偷输出烂稿。

## 9. 照片反推针迹（Phase 7，R&D）

单独服务、单独数据模型，不进入主链路：

```text
照片 → 矫正/去褶皱 → 针脚检测 → 线色聚类 → 针迹图 → 序列推断 → DST
```

- 训练/评测数据必须自建：已知 DST → 缝合 → 拍摄；
- 指标：Chamfer、stitch-level F1、色块数误差、人工可用率；
- 不达标即停止，不对外宣称“照片一键转 DST”。

## 10. 数据与存储

| 数据 | 存储 | 说明 |
| --- | --- | --- |
| 用户/项目/权限 | Postgres | RLS 或应用层租户过滤 |
| 文档 JSON | Postgres JSONB + 版本表 | 每次保存生成 revision |
| 原图/导出/预览 | S3/MinIO | 租户前缀 + 生命周期策略 |
| 任务 | Redis + Postgres | 队列用 Redis，状态落库 |
| 缓存 | Redis | 编译结果按 hash 缓存 |

备份：Postgres 每日全量 + WAL；对象存储版本化；每季度恢复演练。

## 11. 安全

**已实现（2026-10-30）**：
- 可选 `X-API-Key`（`STITCHORD_API_KEY`）、每客户端每分钟限流（`STITCHORD_RATE_LIMIT`）、
  20 MB 请求体上限、Ink/Stitch 编译串行锁；
- SVG 导入拒绝 DTD/ENTITY/`<script>`，元素上限 5000；
- 矢量化先缩到 2000 px 再处理，拒绝 NaN/超范围 `widthMm`。

**仍未实现**：
- worker 无外网、只读挂载、CPU/内存/时间限额（Dockerfile 未构建验证；compose 未加限额）；
- 病毒扫描、短时效签名 URL、多租户隔离测试。

## 12. 非功能预算

| 指标 | 目标 |
| --- | --- |
| 预览首屏（5 万针） | < 800 ms |
| 平移/缩放 | ≥ 50 FPS（Chrome，GTX 1050 Ti 级） |
| 单次编译（2 万针） | P95 < 10 s |
| 导出 DST（5 万针） | P95 < 15 s |
| 可用性（Beta） | 99.5% |
| 任务可恢复 | worker 崩溃后自动重试 ≤ 2 次，幂等 |
