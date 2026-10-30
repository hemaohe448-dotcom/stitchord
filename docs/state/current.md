# 当前状态

- 阶段：**P1 Ink/Stitch 无头编译**（进行中）
- 更新：2026-10-30
- 分支：`main`

## 已完成

- [x] 可行性核查：Ink/Stitch / Embroiderly 的定位、许可证、代码结构；
- [x] 架构决策：自有文档模型 + Ink/Stitch 编译器（ADR-0002）；
- [x] 许可证决策：GPL-3.0-or-later（ADR-0001，已确认：服务端调用、不售卖代码）；
- [x] 路线图 P0–P8 与可执行验收标准；
- [x] 多智能体协作/防幻觉/上下文规范；
- [x] 前端骨架：DST/PES 导入 → StitchPlan → Canvas 渲染 → 导出 DST；
- [x] 后端骨架：预览 / 校验 / 导出 API；
- [x] 测试：前端 17 个单测 + 10 条 Playwright E2E，后端 83 个单测/契约测试（3.11 全量）；
- [x] 构建：`tsc --noEmit`、`vite build` 通过；
- [x] Claude 独立架构评审（`docs/reviews/2026-10-30-architecture-review.md`），阻断项已处置
  （`docs/reviews/2026-10-30-response.md`）；
- [x] **P1 无头验证**：Ink/Stitch 库调用可在无 Inkscape 的进程内生成 StitchPlan + DST；
  10px 矩形 48 针、双色 419 针、输出确定；证据 `docs/research/inkstitch-headless.md`；
- [x] **P1 worker 适配层**：`services/inkstitch_worker/worker.py` 输入扁平 SVG，输出
  StitchPlan JSON + DST；双色 fixture 通过契约校验（pydantic）且两次运行 SHA 一致；
- [x] **P1 编译器 + 端到端**：`services/digitizer/app/compiler.py` 把 CompileDocument(mm)
  编译为 SVG(px)；100×100 文档 → 2 色块/3490 针 → DST 11,012 B，两次运行 SHA 一致；
  DST 读回 3489 针（1 针差异待解释）；
- [x] **P1 参数与 running**：`row_spacing_mm` 实测生效（0.25→1956 针，0.5→1012 针）；
  `type: running` 生成 `Stroke`/39 针；参数映射表 `docs/contracts/inkstitch-params.md`；
- [x] **P1 satin + PES**：双轨线 `satin` 生成 `SatinColumn`/210 针；同一文档导出 PES
  （22,326 B / 2 色块 / Brother 线色匹配）；
- [x] **需求确认**：Roidery = `lork-fork/Roidery`（MIT/Apache，Rust/VectorCraft）；
  GPL 已接受（仅服务端调用）；ADR-0001 更新；
- [x] **面料参数预设**：8 种面料（Roidery 数值 + Wilcom 规则 + Ink/Stitch 语义）
  落到 `services/digitizer/app/fabric.py`；实测 woven/knit 的填充与缎面差异；
  依据 `docs/reference/parameters.md`；ADR-0006 记录 Roidery 定位；
- [x] **统一 3.11 服务**：`/v1/digitize` + `/v1/digitize/export` 接入 Ink/Stitch；
  本地 3.11 测试 26 passed；live API：knit 填充 1432 针、DST 4817 B、导出确定性；
  修掉 server 线程 `stop` 属性与 Ink/Stitch `check_stop_flag` 的冲突；
- [x] **Web 生成面板**：面料/针法选择 → 调用 `/v1/digitize` → 画布更新；已构建并截图；
- [x] **P2 编辑器 MVP**：图层/对象列表、选中、画布拖拽移动、颜色/针法/行距/角度/坐标编辑、
  删除、图层排序、撤销/重做、修改后 450ms 自动重编译；编辑结果可导出 DST；
- [x] **P2 持久化**：工程文档写入 localStorage，刷新后恢复（历史/计划不持久化）；
- [x] **P1 自引用黄金语料**：12 个文档用例 + 平移/确定性，覆盖 fill/running/satin、面料、
  参数、三对象；3.11 全量 **83 passed**（尚缺 Inkscape 参考逐针对比）；
- [x] **P3 基线矢量化**：`/v1/vectorize`（Pillow 量化 + VTracer + mm 缩放）→ CompileDocument；
  网页“图片矢量化”按钮；合成图 2 层/2 路径 → 2,956 针/DST 9,407 B；
  现已支持颜色数 2–16、去白底（边缘洪泛填充，兼容非白背景）、
  扁平/照片两种风格（照片模式=中值+轻微模糊+CIELAB k-means，实验性）、
  细节三档（filter_speckle 2/4/12、layer_difference 8/16/28）；
  证据 `docs/research/vectorization-baseline.md`；
- [x] **P2 项目 IO/快捷键**：工程 JSON 保存/打开、复制对象、Ctrl+Z/Y/D、Delete、方向键微移；
  与 localStorage 自动保存互补；
- [x] **P2 节点编辑（曲线+折线）**：节点方块、入/出控制柄、拖拽改形；M/L/C/Z 均支持，
  弧线/多子路径明确拒绝；前端 15 个单测（路径/曲线/缩放）；
- [x] **P2 自由绘制**：画布按住拖动生成走线对象（自动选中、可节点编辑、自动重编译）；
  CDP 端到端验证：画一笔后 3 对象 / 2,585 针；
- [x] **P2 图层显隐/删除**：图层眼睛开关（不参与编译）、删除图层、至少保留一个可见层；
  编译器新增 `visible` 与回归测试；
- [x] **P2 预览/矢量化控制**：显示打底开关（预览用 underlay=false，导出仍用完整文档；
  实测 1440→1212 针）、矢量化颜色数 2–16、去白底开关；
- [x] **P2 多选**：Shift+点击对象多选、整体拖拽、批量删除/复制；选中描边叠加；
  CDP 验证：3 对象中选 2 → 复制后 5 对象，仍选中 2 个；
- [x] **生产校验**：`/v1/stitch/check`（静态规则 + 绣框适配），网页 5 种绣框预设、
  错误时禁用导出；`OUTSIDE_HOOP` / `TIGHT_HOOP_MARGIN` 测试；
- [x] **P5 格式导出**：网页可选 DST/PES/JEF/EXP/VP3/XXX；`/v1/digitize/export?format=`
  走 Ink/Stitch writer；6 格式全部读回通过，矩阵见 `docs/reference/machine-formats.md`；
  JEF 因 pystitch writer 不可读回，临时回退 pyembroidery；
- [x] **工艺单 PDF**：`/v1/worksheet` 生成 A4 一页（预览、尺寸、绣框、面料、针数/跳针/剪线、
  线色顺序、估算线量与工时）；网页“工艺单”按钮下载；
- [x] **SVG 导入**：`/v1/import/svg` 用 svgelements 解析 rect/circle/path/group transform，
  viewBox → mm，弧线转曲线；网页导入框直接识别 `.svg`；
- [x] **服务端权威校验**：边界/统计从实际针迹重算，拒绝 NaN/Infinity；
  `/v1/digitize/export` 也执行绣框校验（越框 422）；前端校验失败时 fail-closed；
- [x] **请求安全**：可选 `X-API-Key`、每分钟限流、20 MB body cap、编译串行锁、
  SVG 拒绝 DTD/ENTITY/script、矢量化先缩图再处理；
- [x] **结果缓存**：按文档 JSON + 格式做 32 项 LRU，导出返回 `X-Stitch-Cache: hit/miss`；
  不改“文档→SVG→Ink/Stitch”主链路。
- [x] **P2 针迹播放**：播放/暂停、进度条、慢/中/快、当前针高亮；仅前端，构建通过；
- [x] **历史上限**：前端 undo 栈统一经 `pushHistory` 截到 100 步；前端 17 个单测；
  E2E 验证 100 次移动 + 100 次撤销后导出的 DST SHA-256 与初始一致。
- [x] **Playwright 主流程**：9 条 E2E（加载/新增撤销/改参数/保存打开/DST 导入/
  对象隐藏锁定/图层复制改名合并+锁定/100 步撤销 hash/导出）全部通过，41.5s；
- [x] **对象级隐藏/锁定**：隐藏对象不参与编译，锁定对象不可在画布选中/拖动/节点编辑；
  编译器有 hidden 回归测试；
- [x] **针法参数面板扩展**：running 针距/线宽，satin 密度/拉布补偿，fill/satin 打底开关；
- [x] **图层管理**：重命名（失焦/Enter 提交）、复制图层、向下合并；对象 id 去重；
- [x] **图层锁定**：锁定后画布不可选中/拖动/节点编辑，仍参与编译；对象级锁定继续保留；
- [x] **工程名/订单抬头**：`CompileDocument.name` 可编辑、随工程 JSON 保存，
  工艺单 PDF 抬头使用该名称（空则 Stitchord Design）；中文抬头用 STSong CID 字体；
- [x] **对象级局部重算 MVP**：按 SVG 叶子元素缓存 Ink/Stitch stitch groups；
  未变对象复用、变更对象重算，plan 组装仍全量以保证与完整编译一致；
  测试：复用 2 个对象时 DST 字节相同；改红块后蓝块 stitches 逐项相同。ADR-0007；
- [x] **服务端工程库（单租户）**：SQLite `/v1/projects` CRUD；网页“保存到服务器/项目库”；
  从服务器打开后再保存走 PUT，不会重复新建；PUT 带 `expectedUpdatedAt`，
  过期写返回 409，避免静默覆盖；无认证/多租户；
- [x] **界面错误边界**：React `ErrorBoundary` 防止白屏，提示工程仍在 localStorage；
- [x] **验收状态文档**：`docs/09-acceptance-status.md` 区分已交付/未验证/生产门禁。
- [x] **就绪探针**：`/ready` 检查 Ink/Stitch import；`/health` 仍只表示进程存活，
  compose healthcheck 已改用 `/ready`。
- [x] **上机规则扩展**：跳针过长、跳针比例过高、剪线过多、色块过多均给出 warning；
  不阻塞导出，交由制版师判断。
- [x] **worker 镜像 CI 入口**：容器 App 已启动 `/health` ✅；`/ready` 503（Ink/Stitch import 失败），
  `/ready` 现在返回 import traceback，workflow 增加 wx/Ink-Stitch 诊断步骤；待重跑定位。
- [x] **GitHub ci**：commit `0653c89` 成功；Vitest 已排除 e2e。
- [x] **ADR-0006 用户决策**：选 **A**——自研编辑器优先，Roidery 仅评估，不替换运行时。
- [x] **ADR-0006 门槛通过（2026-10-30）**：CI 成功构建 `vectorcraft-cli`（15m 10s，
  DST 4,721 B）；仅证明可构建/最小导出，T-0202 静态评估中。
- [x] 发现并记录：wxPython 是 import 硬依赖、必须关闭磁盘缓存、plan(px) 与 DST(0.1mm/居中) 的差异。

## 进行中

- [ ] P1 worker 镜像（Dockerfile 已写，**未构建验证**）与 12 份黄金语料；
- [ ] P1 收尾：Inkscape 参考逐针对比、DST 边界针差异固定测试、性能与错误输入；
- [ ] T-0202 Roidery 集成评估（CLI/MCP 输入、DST 读回、许可证、部署体积、跨平台）；
- [ ] 生产硬化：认证/配额/请求体上限、SVG 实体防护、CI 去 skip、真实上机试缝；
- [ ] P2 剩余：锁定/合并/布尔、起收针/锁针、密度、性能预算。

## 下一步（按优先级）

1. **T-0202 Roidery 集成评估**：CLI/MCP 输入、DST 读回、许可证、部署体积、跨平台。
2. **Worker 镜像/CI**：在 GitHub Actions 构建 Dockerfile，跑 `/v1/digitize` 冒烟。
3. **P2/P3**：锁定/布尔、ML 分割与质量基准。
4. **生产硬化**：认证/限流、请求体上限、SVG 消毒与超时。

## 阻塞 / 风险

| 项 | 影响 | 需要谁 |
| --- | --- | --- |
| 无 Docker / Linux runner | worker 镜像无法本机构建验证 | 人类安装或 CI |
| 无绣花机/打样条件 | 无法完成 P6 生产级验收 | 人类对接打样伙伴 |
| 无 Rust/MSVC 工具链 | Roidery 内核无法本地构建 | Phase 2 CI 门槛 |
| 目标机型/幅面未定 | 校验规则与预设无法最终标定 | 用户确认 |
| 无认证/配额 | 公网部署会暴露无界算力 | 产品/后端 |

## 环境快照

- Node 24.22.1 / npm 11.19.1
- Python 3.14.9（`.pylibs` 本地依赖）；CI 用 3.11
- Python 3.11.18（`.condaenv`，Ink/Stitch + wxPython + inkex）
- 代理 `127.0.0.1:7890`
- 前端构建需完全权限（esbuild spawn）
