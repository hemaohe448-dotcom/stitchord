# T-0102：矢量化基准集与评测脚本

状态: todo
负责人: Builder / QA
依赖: 无（可与 T-0101 并行）
对应验收: P3-AC1 … P3-AC3

## 目标

在写矢量化服务之前，先有“可证伪”的评测：30 张基准图、人工参考、指标脚本。
避免“看起来不错”的自我欺骗。

## 非目标

- 不训练模型；
- 不接 GPU；
- 不做 UI。

## 输入

- `docs/05-production-quality.md`
- `docs/02-architecture.md` 第 8 节
- `docs/contracts/stitch-plan.md`

## 步骤

1. 选 30 张授权图片：Logo、扁平插画、文字、渐变、照片风各 6 张；
2. 每张人工制作参考：区域掩码（PNG）+ 矢量化轮廓（SVG）；
3. 写 `tools/benchmark/`：计算区域 IoU、轮廓 Chamfer、最小宽度、节点数；
4. 写基线：vtracer/potrace + 简化（不接 ML），输出指标；
5. 生成 `docs/datasets/vectorization.md` 索引（来源、许可、hash）。

## 验收标准

- [ ] AC1 30 张图 + 参考齐全，许可可追溯；
- [ ] AC2 脚本一条命令输出 JSON 报告（每图 + 汇总）；
- [ ] AC3 基线指标可复现（同输入同输出）；
- [ ] AC4 报告含失败案例与原因分类；
- [ ] AC5 无版权不明素材入库。

## 证据

- `artifacts/benchmark/<date>/report.json`
- `docs/datasets/vectorization.md`
