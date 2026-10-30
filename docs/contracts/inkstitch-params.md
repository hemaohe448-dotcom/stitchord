# Ink/Stitch 参数映射（P1 交付物）

> **禁止凭记忆填写。** 每一项必须来自：
> - `lib/elements/*.py` 的 `get_param` / 属性读取，附 `path:line`；
> - 或 `lib/inx/*.inx` 的 UI 定义；
> - 或“Inkscape 实际导出 SVG”的观测（附 SVG 片段）。
>
> 未验证项写 `TODO(verify)`，不得进入编译器实现。

## 映射表

| 我们的字段 | Ink/Stitch 属性 | 类型 | 单位 | 默认值 | 证据 | 验证日期 |
| --- | --- | --- | --- | --- | --- | --- |
| `stitch.type=running` | TODO(verify) | — | — | — | — | — |
| `stitch.type=satin` | TODO(verify) | — | — | — | — | — |
| `stitch.type=fill` | TODO(verify) | — | — | — | — | — |
| `stitch.angleDeg` | TODO(verify) | — | — | — | — | — |
| `stitch.rowSpacing` | TODO(verify) | — | — | — | — | — |
| `stitch.density` | TODO(verify) | — | — | — | — | — |
| `stitch.pullComp` | TODO(verify) | — | — | — | — | — |
| `stitch.underlay` | TODO(verify) | — | — | — | — | — |
| `stitch.minStitch` | TODO(verify) | — | — | — | — | — |
| `stitch.tieIn` | TODO(verify) | — | — | — | — | — |
| `stitch.tieOff` | TODO(verify) | — | — | — | — | — |

## 单位换算

- 文档：mm；
- Ink/Stitch/Inkscape：SVG 用户单位（96 dpi）；换算只在 `compile_svg` 一处；
- 证据：TODO(verify) 用实测 SVG 的宽度/`viewBox` 反推。

## 变更记录

| 日期 | 变更 | 证据 |
| --- | --- | --- |
| 2026-10-30 | 建立骨架 | T-0101 |
