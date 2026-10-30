# 验收状态（2026-10-30）

> 目的：区分“能演示/有测试”与“已达生产门禁”。**当前不能声称已通过工业生产验证。**

## 1. 已交付并有证据

| 能力 | 证据 |
| --- | --- |
| 文档 → SVG → Ink/Stitch → StitchPlan/DST/PES | 后端 82 tests；黄金语料 |
| 6 格式导出 + 读回 | `docs/reference/machine-formats.md`；参数化测试 |
| 分层编辑：显隐、锁定、复制、改名、合并、多选 | Playwright 10 条 |
| 曲线/折线节点编辑、自由绘制 | `curve.ts` 7 tests；E2E |
| fill/running/satin 参数 | 后端编译 + UI 字段 |
| 绣框/针长/跳针/剪线/色块校验 | 服务端权威校验 + 422 导出拦截 |
| 图片矢量化（Lab k-means、去背景、细节三档） | `test_vectorize.py` 8 tests |
| SVG 导入 | `test_svg_import.py` 5 tests |
| 工艺单 PDF（中英抬头） | `test_api.py` |
| 对象级局部重算 | `test_object_group_cache...`；ADR-0007 |
| 100 步 undo + 确定性导出 | E2E：100 次移动/撤销后 DST 哈希相同 |
| 工程 JSON / SQLite 工程库 / 乐观并发 | 后端 CRUD + 409 测试；E2E |
| API key / 限流 / body cap / SVG 防护 | `test_api.py` |
| 错误边界 | `ErrorBoundary.tsx`，构建通过 |

## 2. 未完成 / 未验证

| 项 | 状态 |
| --- | --- |
| Docker worker 镜像 | **未通过**：旧构建在 wxPython 4.3.2 源码编译失败；已改 4.2.5 Linux wheel，尚未重跑 |
| GitHub `ci` | 上次失败于 Vitest 误收集 e2e；已修，尚未重跑 |
| 认证/多租户 | 只有可选 API key；无用户/归属 |
| 真实上机试缝 | **没有** |
| JEF 机台字段 | 仅读回，未机型验证 |
| ML 分割/照片质量基准 | **没有**；只有颜色量化基线 |
| 性能预算（10 万针） | 未测 |
| 中文工艺单正文 | 仅抬头；正文英文 |
| 冲突自动合并 | 409 提示，需手动重载 |

## 3. 生产门禁（建议）

- [ ] worker-image 在 GitHub Actions 构建成功；
- [ ] 容器 `/ready` 200 + `/v1/digitize` 200；
- [ ] `ci` 全绿，digitize/golden 不 skip；
- [ ] 真实 DST/PES 在目标机器试缝；
- [ ] 认证/项目归属；
- [ ] 备份/恢复演练（SQLite/持久卷）；
- [ ] 10 万针性能与内存预算。

以上未全部通过前，只能定位为“可演示的制版原型/内部试用”。

## 4. 本机验收命令

```powershell
# 后端
$env:PYTHONPATH='D:\stitchord\services\digitizer;D:\stitchord\.research\repos\inkex;D:\stitchord\.research\repos\inkstitch'
D:\stitchord\.condaenv\python.exe -m pytest -q

# 前端单测
cd D:\stitchord\apps\web
npm test

# E2E（自动起 API/Vite，需 Edge + 3.11 worker）
npm run test:e2e
```

最近结果：后端 **82 passed**，前端 **17 passed**，E2E **10 passed**。
