# 机器格式实测矩阵（2026-10-30）

> 输入：100×100 mm 文档，两个 40×30 mm 填充色块（红 `#c0392b`、蓝 `#2980b9`），
> woven 面料。导出走 `/v1/digitize/export?format=…`，读回用 pyembroidery 1.5.1。
> **读回成功不等于机台兼容**；仍需真实机型/试缝验证。

| 格式 | 字节 | 读回针数 | 读回线色数 | writer | 备注 |
| --- | --- | --- | --- | --- | --- |
| DST | 8,234 | 2,574 | 0 | Ink/Stitch | 无机台颜色（3 字母线号外部维护） |
| PES | 16,770 | 2,569 | 2 | Ink/Stitch | 原点在 0,0（不居中），Brother 线色匹配 |
| EXP | 5,158 | 2,572 | 0 | Ink/Stitch | 无机台颜色 |
| JEF | 5,298 | 2,574 | 2 | **pyembroidery fallback** | 见下方 JEF 说明 |
| VP3 | 5,480 | 2,567 | 2 | Ink/Stitch | 居中 |
| XXX | 5,518 | 2,574 | 2 | Ink/Stitch | 居中 |

针数差异（2,567–2,574，约 ±0.3%）来自各 writer 的边界针/量化策略。

## JEF 说明（重要）

- Ink/Stitch 使用的 `pystitch` JEF writer 生成的文件，**pyembroidery 的 JefReader 读不了**
  （`JefReader.py:63` 读 offset table 得到 `None`，`abs(None)` 崩溃）；
- 因此 JEF 单独回退到 `pyembroidery.write_jef`（由同一 StitchPlan 构造 pattern）；
- 这是“可读回”的最低保证，不代表 JEF 在所有 Janome 机型上的字段完全正确；
- 待办：用真实 JEF 文件对照、机型实测；若确认 pystitch bug，向上游报 issue。

## 覆盖边界

- 已覆盖 6 种导出格式的“写入 + 读回”；
- 未覆盖：真实机器、绣框分框、线色目录逐品牌、锁针/剪线字段差异；
- P5 仍需 50 份真实文件语料与机型矩阵。
