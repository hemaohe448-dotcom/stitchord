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

Phase 0 只实现：浏览器针迹查看器 + digitizer 的 DST 读取/导出/校验；Ink/Stitch、队列、数据库在后续阶段接入。

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
    ├── Layer（顺序、可见、锁定、颜色）
    │   └── Object（路径 / 组 / 文字 / 位图源）
    │       ├── geometry: 贝塞尔路径（mm，Y 向下）
    │       ├── stitch: { type, angle, rowSpacing, density, underlay,
    │       │            pullComp, minStitch, tieIn, tieOff, start/end }
    │       └── source: 可选，指向原始位图/矢量化任务
    └── Metadata（作者、机型、线色目录、版本）
```

规则：
- 一个 Object 只产生一个颜色块；同色对象可在导出时合并（由 sequencer 决定）。
- 图层顺序即默认缝制顺序；`sequencer` 可重排以减少换色/跳针，但必须可解释、可回退。
- 文档以 JSON 存储（`.stitchord` zip：`project.json` + `assets/` + `thumbnail.png`），带 `schemaVersion` 与迁移函数。
- 文档**不存生成后的针迹**；只存缓存 hash，缓存失效即重算。

文档示例（节选）：

```json
{
  "schemaVersion": "1.0",
  "artwork": { "widthMm": 120, "heightMm": 120, "hoop": "100x100" },
  "layers": [
    {
      "id": "layer-1",
      "name": "花瓣",
      "color": { "hex": "#dd6b20", "brand": "Isacord", "code": "1104" },
      "objects": [
        {
          "id": "obj-1",
          "kind": "path",
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
        └─ worker: stitch_plan_json 扩展                     →  StitchPlan JSON
```

### 5.2 规则

- **参数属性名不得凭记忆写**。Phase 1 的第一件事是从 Ink/Stitch 源码与 `.inx` 文件中提取
  真实属性名/默认值/单位，生成 `docs/contracts/inkstitch-params.md` 与映射表，并用契约测试锁定。
- 单位换算只允许在 `compile_svg` 一处发生；任何模块不得硬编码 96 / 25.4。
- 输出的 SVG 必须能被固定版本的 Ink/Stitch 读取；解析失败要返回可定位的错误（元素 id + 原因）。
- 针迹计划 JSON 通过在 worker 内新增一个只读扩展实现（GPL，补丁公开），不改 Ink/Stitch 的绣法逻辑。
- 每次编译记录：文档 hash、编译器版本、Ink/Stitch commit、参数快照、输出 hash。

### 5.3 契约测试（Phase 1 验收核心）

准备一批“黄金 SVG”（覆盖 running / satin / fill / underlay / 多色 / 跳针 / 锁针），分别：
1. 用 Inkscape + Ink/Stitch 原生产出参考 DST；
2. 用我们的编译器产出 DST；
3. 比较：针数、色块数、换色数、包围盒（≤0.1 mm）、逐针坐标（容差 ≤0.05 mm）、文件 hash 稳定性。

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

## 7. API（Phase 0 已实现 + 规划）

| 方法 | 路径 | 状态 | 说明 |
| --- | --- | --- | --- |
| GET | `/health` | ✅ | 健康检查 |
| POST | `/v1/stitch/preview` | ✅ | 上传 DST/PES/… → StitchPlan |
| POST | `/v1/stitch/validate` | ✅ | 静态规则校验 |
| POST | `/v1/stitch/export` | ✅ | StitchPlan → DST/EXP/… |
| POST | `/v1/projects` | P4 | 创建工程 |
| GET/PUT | `/v1/projects/{id}` | P4 | 读取/保存文档 |
| POST | `/v1/assets` | P4 | 上传原图，返回签名 URL |
| POST | `/v1/vectorize` | P3 | 创建矢量化任务 |
| POST | `/v1/digitize` | P1 | 文档 → 针迹计划 |
| GET | `/v1/jobs/{id}` | P1 | 任务状态 / 进度 / 错误 |
| POST | `/v1/exports` | P5 | 导出并写入对象存储 |

约定：
- 所有写接口支持 `Idempotency-Key`；
- 任务异步化，返回 `jobId`，通过 SSE/WebSocket 推送进度；
- 错误统一 `{code, message, details, traceId}`；
- 上传限制 25 MB（Phase 0），后续按套餐调整。

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

- SVG 是不可信输入：禁用脚本/外部实体/远程引用，先消毒再进 Ink/Stitch；
- worker 无外网、只读挂载、CPU/内存/时间限额；
- 上传文件类型嗅探 + 大小限制 + 病毒扫描（Phase 4）；
- 导出下载用短时效签名 URL；
- 多租户隔离测试纳入 CI（跨租户读取必须 403）。

## 12. 非功能预算

| 指标 | 目标 |
| --- | --- |
| 预览首屏（5 万针） | < 800 ms |
| 平移/缩放 | ≥ 50 FPS（Chrome，GTX 1050 Ti 级） |
| 单次编译（2 万针） | P95 < 10 s |
| 导出 DST（5 万针） | P95 < 15 s |
| 可用性（Beta） | 99.5% |
| 任务可恢复 | worker 崩溃后自动重试 ≤ 2 次，幂等 |
