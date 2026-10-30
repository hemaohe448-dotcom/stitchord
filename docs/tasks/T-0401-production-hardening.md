# T-0401: 生产硬化（审计修复 + SVG 导入）

状态: done
负责人: DSH（主代理）+ subagent 审计
依赖: T-0101, T-0102

## 目标

修复 2026-10-30 独立审计中的可证明问题，并补 SVG 导入：

1. 服务端权威校验：边界/统计从实际针迹重算，拒绝 NaN，导出也校验绣框；
2. 前端校验 fail-closed，导出传绣框；
3. 工艺单与导出计划一致（预览去 underlay 时，工艺单改用完整计划）；
4. 工程被导入/新建覆盖时保留上一版到 undo，autosave 不因 doc=null 删除；
5. SVG 导入（rect/circle/path/group transform/viewBox/弧线转曲线）。

## 非目标

- 认证/配额/限流、Docker 镜像构建、CI 去 skip、100 步 undo 上限；
- ML 分割、局部重算、真实上机试缝。

## 验收标准

- [x] 伪造 1×1 mm bounds + 200 mm 针迹 → `OUTSIDE_HOOP`；
- [x] NaN 坐标 → `NON_FINITE_COORDINATE`；
- [x] 100 mm 文档以 50 mm 绣框导出 → 422 + `OUTSIDE_HOOP`；
- [x] `computed_stats` 忽略伪造 stats；
- [x] SVG 导入 3 色/group transform/弧线转 C，接口 200；
- [x] 3.11 全量 70 passed；前端 tsc/build 通过。

## 证据

```text
PYTHONPATH=services/digitizer;.research/repos/inkex;.research/repos/inkstitch
.condaenv/python.exe -m pytest -q  -> 70 passed
apps/web: tsc --noEmit -> 0; vite build -> ok
```

## 风险与未知

- Dockerfile 已补固定 Ink/Stitch/inkex + GTK/wx，但**本机无 Docker，未构建验证**；
- CI 仍可能跳过 Ink/Stitch 用例；
- 未做认证/限流/请求体上限；
- SVG 实体防护未做（仅大小/UTF-8）。
