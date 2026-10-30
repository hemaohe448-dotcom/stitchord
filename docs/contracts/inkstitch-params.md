# Ink/Stitch 参数映射（P1 交付物）

> **禁止凭记忆填写。** 每一项必须来自：
> - `lib/elements/*.py` 的 `get_param` / 属性读取，附 `path:line`；
> - 或 `lib/inx/*.inx` 的 UI 定义；
> - 或“实际编译 SVG → worker → plan”的观测。
>
> 未验证项写 `TODO(verify)`，不得进入编译器实现。

## 0. 命名空间与单位

- 参数属性命名空间：`http://inkstitch.org/namespace`，前缀 `inkstitch`
  （`lib/svg/tags.py:9-10`，`INKSTITCH_ATTRIBS` 由 `inkex.addNS(..., 'inkstitch')` 生成，`tags.py:208`）。
- `*_mm` 参数在读取时乘以 `PIXELS_PER_MM`（96/25.4）（`lib/elements/element.py:142-143`），
  所以 SVG 里写的是**毫米值**，内部变 px。
- 角度参数在代码里 `math.radians(...)`，所以 SVG 里写的是**度**（`fill_stitch.py:310`）。

## 1. 已接入编译器并实测

| 我们的字段 | Ink/Stitch 属性 | 类型/单位 | 默认 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `stitch.type=fill` | `style="fill:#...;stroke:none"` | SVG style | — | `fill_stitch.py:164`；端到端 2 色块 | ✅ 已验证 |
| `stitch.type=running` | `style="fill:none;stroke:#...;stroke-width:<mm>"` | SVG style | width 0.4 mm | 端到端 `Stroke`、39 针 | ✅ 已验证 |
| `stitch.rowSpacingMm` | `inkstitch:row_spacing_mm` | float, mm | 0.25 | `fill_stitch.py:379` | ✅ 实测：0.25→1956 针，0.5→1012 针（40×30 mm） |
| `stitch.angleDeg` | `inkstitch:angle` | float, 度 | 0 | `fill_stitch.py:310` | ⚠️ 已编译，未做几何对比 |
| `stitch.underlay` | `inkstitch:fill_underlay` | bool | true | `fill_stitch.py:684` | ⚠️ 已编译，未做几何对比 |

## 2. 已提取、尚未接入

| 我们的字段 | Ink/Stitch 属性 | 类型/单位 | 默认 | 证据 | 状态 |
| --- | --- | --- | --- | --- | --- |
| `fill.maxStitchLengthMm` | `inkstitch:max_stitch_length_mm` | mm | 4.0 | `fill_stitch.py:361` | TODO(verify) |
| `fill.underlayAngleDeg` | `inkstitch:fill_underlay_angle` | string/列表 | None | `fill_stitch.py:695` | TODO(verify) |
| `fill.underlayRowSpacingMm` | `inkstitch:fill_underlay_row_spacing_mm` | mm | row×3 | `fill_stitch.py:722` | TODO(verify) |
| `fill.underlayMaxStitchLengthMm` | `inkstitch:fill_underlay_max_stitch_length_mm` | mm | max_stitch | `fill_stitch.py:732` | TODO(verify) |
| `fill.underlayInsetMm` | `inkstitch:fill_underlay_inset_mm` | mm | 0 | `fill_stitch.py:743` | TODO(verify) |
| `fill.underlaySkipLast` | `inkstitch:fill_underlay_skip_last` | bool | false | `fill_stitch.py:755` | TODO(verify) |
| `fill.pullCompensationMm` | `inkstitch:pull_compensation_mm` | split mm | (0,0) | `fill_stitch.py:664` | TODO(verify) |
| `fill.pullCompensationPercent` | `inkstitch:pull_compensation_percent` | split float | (0,0) | `fill_stitch.py:679` | TODO(verify) |
| `fill.staggers` | `inkstitch:staggers` | float | 4 | `fill_stitch.py:428` | TODO(verify) |
| `fill.skipLast` | `inkstitch:skip_last` | bool | false | `fill_stitch.py:444` | TODO(verify) |
| `fill.underpath` | `inkstitch:underpath` | bool | true | `fill_stitch.py:496` | TODO(verify) |
| `fill.fillMethod` | `inkstitch:fill_method` | enum | tatami_fill | `fill_stitch.py:184` | TODO(verify) |
| `fill.randomSeed` | `inkstitch:random_seed` | string | "" | `fill_stitch.py:785` | TODO(verify) |
| `satin.*` | — | — | — | `lib/elements/satin_column/` | TODO(verify) |
| `stroke.*` | `inkstitch:stroke_method` | enum | — | `stroke.py:94` | TODO(verify) |

## 3. 实测方法（可复现）

```powershell
# 1) 生成不同 row spacing 的 SVG
python tools/e2e/compile_params.py
# 2) worker 编译
$env:PYTHONPATH='...\inkex;...\inkstitch'
.condaenv\python.exe services\inkstitch_worker\worker.py --svg artifacts\e2e\rows_half.svg --dst ... --plan ...
# 3) 对比 plan.json 的 stats.stitchCount
```

结果：默认 0.25 mm → 1956 针；0.5 mm → 1012 针（同一 40×30 mm 矩形）。说明 `row_spacing_mm`
的属性名、mm 单位、group 缩放链路均正确。

## 4. 变更记录

| 日期 | 变更 | 证据 |
| --- | --- | --- |
| 2026-10-30 | 建立骨架 | T-0101 |
| 2026-10-30 | 加入命名空间、单位规则、row spacing/angle/underlay；实测 row spacing | 本文件 §3 |
