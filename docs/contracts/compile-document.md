# CompileDocument v1.0（编译器输入）

> 这是“编辑器文档 → Ink/Stitch SVG”之间的最小契约，Phase 1 只支持填充（fill）。
> 类型定义：`services/digitizer/app/compiler.py`。

## 1. 结构

```json
{
  "widthMm": 100,
  "heightMm": 100,
  "fabric": "knit",
  "name": "Order #A-1024",
  "notes": "customer: demo",
  "layers": [
    {
      "id": "layer-red",
      "name": "red",
      "objects": [
        {
          "id": "obj-red",
          "pathD": "M 10,10 L 50,10 L 50,40 L 10,40 Z",
          "color": { "hex": "#c0392b", "name": "red" },
          "stitch": { "type": "fill" }
        }
      ]
    }
  ]
}
```

## 2. 规则

1. `pathD` 使用**毫米坐标**，只允许 SVG path 命令与数字（`MmLlHhVvCcSsQqTtAaZz0-9eE+-.,` 与空白）；
   禁止引号、尖括号，防止 SVG 注入。
2. 一个 object 产生一个颜色块；同色对象是否合并由 Ink/Stitch 决定。
3. 图层顺序 = 缝制顺序；object 顺序同理。
4. `name`/`notes` 是可选工程元数据（最长 120/1000 字符），编译器忽略，
   工艺单与工程 JSON 会保留。
5. Phase 1 支持 `fill` / `running` / `satin`；satin 要求 `pathD` 含两条轨线（两个子路径），
   编译器输出 `inkstitch:satin_column="true"`。更复杂的 satin 参数（密度、拉布补偿、分段）待补。
6. `angleDeg` / `rowSpacingMm` / `underlay` / `pullCompensationMm` / `underlaySpacingMm` /
   `maxStitchLengthMm` / `satinDensityMm` / `satinHeavyUnderlay` 输出为 `inkstitch:*` 属性；
   属性名与单位见 `docs/contracts/inkstitch-params.md`。
7. `fabric` 指定面料预设（`woven`/`knit`/`pique`/`terry`/`fleece`/`denim`/`twill`/`leather`），
   为未显式设置的参数填入默认值；显式值优先。数值与出处见 `docs/reference/parameters.md`。

## 3. 编译结果

- SVG 根尺寸为 px（96 dpi）：`widthMm × 96/25.4`；
- 所有路径放在一个 `<g transform="scale(3.779527559)">` 中，把 mm 映射为 px；
- **已验证 Ink/Stitch 会应用 group transform**（2026-10-30，40×30 mm 矩形得到
  `bounds 10..50 mm`、1956 针）；
- 输出不含时间戳/随机值，同输入字节级一致。

## 4. 已验证的端到端结果

输入：100×100 mm 画布，两个 40×30 mm 矩形（红 `#c0392b`、蓝 `#2980b9`）。

| 环节 | 结果 |
| --- | --- |
| compile_svg | 2 个 path，尺寸 377.952756 px，scale 3.779527559 |
| worker plan | 2 色块 / 3490 STITCH / bounds 10..90 × 10..40 mm |
| DST | 11,012 B，SHA-256 `fd64cc3d…55c7b`（两次运行一致） |
| DST 读回 | 2 色块 / 3489 STITCH / bounds -40..40 × -15..15 mm（居中） |

**已知差异**：计划针数与 DST 读回可能相差 ≤3 针。已定位为 DST 写入器在色块起始/换色处的
边界针行为（见 `tools/e2e/compare_plan_dst.py`）：双色用例计划 3490、读回 3489；
按 0.1 mm 量化逐点对齐后，差异集中在每个色块起始位置。P1-AC3 因此采用
“逐点容差 ≤0.17 mm、针数差 ≤3” 的验收口径，而不是逐针完全相等。

### 4.1 参数与 running 实测

| 用例 | 结果 |
| --- | --- |
| 40×30 mm 填充，默认 row spacing（0.25 mm） | 1956 针 |
| 同上，`rowSpacingMm: 0.5` | 1012 针（约一半，单位与属性名正确） |
| 70 mm 折线，`type: running` | `Stroke` 元素 / 39 针 / bounds 10..50 × 50..80 mm |
| 两条 40 mm 轨线，`type: satin` | `SatinColumn` 元素 / 210 针 / bounds 10..30 × 10..50 mm |
| 同一双色文档导出 PES | 22,326 B / 2 色块 / 3495 针 / Brother 线色（`#d15400`,`#2584bb`） |
| 填充 woven（pull 0.20 / row 0.40） | 1440 针 / bounds 9.638..50.380 × 10..40.203 |
| 填充 knit（pull 0.30 / row 0.42） | 1432 针 / bounds 9.530..50.488 × 10..40.113 |
| 缎面 woven（中心线打底） | 243 针 / bounds 9.8..30.2 × 10..50 |
| 缎面 knit（轮廓+锯齿打底） | 343 针 / bounds 9.7..30.3 × 10..50 |

## 5. 待扩展

- 绣法参数：`angle`、`rowSpacingMm`、`densityMm`、`underlay`、`pullComp` 等
  （属性名与单位必须先由 `docs/contracts/inkstitch-params.md` 锁定，禁止猜）；
- running / satin；
- 多图层嵌套、文本、位图对象；
- hoop 校验与分框。
