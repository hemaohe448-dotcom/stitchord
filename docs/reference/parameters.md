# 绣花参数依据（Ink/Stitch + Wilcom + Roidery）

> 目的：让“默认参数”有出处，而不是拍脑袋。所有数值都是**起点**，必须试缝校准。
> 访问日期：2026-10-30。外部页面内容仅作资料引用。

## 1. 来源

| 来源 | 链接 | 用来支撑什么 |
| --- | --- | --- |
| Wilcom EmbroideryStudio — About auto fabrics | https://docs.wilcom.com/embroiderystudio/28/en/OnlineHelp/Digitizing/properties/properties-9.htm | 面料 → 密度/拉布补偿/打底的定性规则 |
| Wilcom EmbroideryStudio — Stitch Quality | https://docs.wilcom.com/embroiderystudio/26/en/OnlineHelp/Quality/PART_Quality/PART_Quality.htm | 间距、拉布补偿、打底共同决定质量 |
| Ink/Stitch — Underlay tutorial | https://inkstitch.org/tutorials/underlay/ | 打底类型与宽度区间；包边 inset 0.4–0.6 mm |
| Ink/Stitch — Fill stitch | https://inkstitch.org/docs/stitches/fill-stitch/ | 填充打底 90° 交叉、行距更宽；pull compensation 行为 |
| Ink/Stitch — Satin column | https://inkstitch.org/docs/stitches/satin-column/ | 缎面密度/拉布补偿/三种打底 |
| Ink/Stitch — Push/Pull compensation | https://inkstitch.org/tutorials/push-pull-compensation/ | 补偿受面料/稳定/密度/打底/机速影响，必须试缝 |
| Roidery `fabric.rs`（MIT/Apache） | https://github.com/lork-fork/Roidery/blob/main/crates/emb-stitch/src/fabric.rs | 8 种面料的数值化预设（本地核对 commit `0187f73`） |

## 2. 文档给出的规则（摘要）

- **Wilcom Auto Fabrics**：弹力/厚面料 → 更大拉布补偿；厚/密面料 → 放松密度（加大间距）；
  针织/毛圈 → 增加边缘或锯齿打底；牛仔/厚斜纹 → 略降密度、较小补偿、较长针迹。
- **Wilcom Stitch Quality**：正确的针距 + 足够拉布补偿 + 与面料匹配的打底，三者缺一不可。
- **Ink/Stitch Underlay**：薄面料少打底、厚面料多打底；密度越高越需要打底；
  中心线打底适合 1–2 mm 缎面，轮廓打底适合 2–3.5 mm，更宽时叠加锯齿；
  轮廓打底 inset 基础值 0.4–0.6 mm。
- **Ink/Stitch Fill**：填充打底通常与面线成 90°，行距明显更宽；`pull compensation`
  会把每行向外扩展以抵消收缩。
- **Ink/Stitch Push/Pull**：补偿量受面料、稳定、尺寸、针法/密度、打底、绷框、机速影响，
  必须用相同条件试缝后微调。

## 3. 采用的数值预设

来自 Roidery `fabric.rs`（MIT/Apache），已在本仓库 `services/digitizer/app/fabric.py` 中实现；
与 Wilcom 的定性规则一致（弹力/毛圈补偿更大、打底更重；牛仔/皮革密度更松、补偿更小）。

| 面料 | 缎面密度 mm | 拉布补偿 mm | 填充行距 mm | 填充针长 mm | 打底行距 mm | 重打底 |
| --- | --- | --- | --- | --- | --- | --- |
| woven 平纹棉 | 0.40 | 0.20 | 0.40 | 3.0 | 2.5 | 否（中心线） |
| knit 针织 | 0.42 | 0.30 | 0.42 | 3.0 | 2.0 | 是（轮廓+锯齿） |
| pique 珠地 | 0.40 | 0.30 | 0.40 | 3.0 | 2.0 | 是 |
| terry 毛圈 | 0.36 | 0.35 | 0.38 | 3.0 | 1.8 | 是 |
| fleece 抓绒 | 0.38 | 0.35 | 0.40 | 3.0 | 2.0 | 是 |
| denim 牛仔 | 0.42 | 0.15 | 0.42 | 3.5 | 3.0 | 否 |
| twill 斜纹/帽料 | 0.40 | 0.25 | 0.40 | 3.0 | 2.5 | 否 |
| leather 皮革 | 0.50 | 0.10 | 0.50 | 3.5 | 3.5 | 否 |

## 4. 映射到 Ink/Stitch 属性

| 预设字段 | Ink/Stitch 属性 | 说明 |
| --- | --- | --- |
| fill row spacing | `inkstitch:row_spacing_mm` | mm；已验证 0.25→1956 针、0.5→1012 针 |
| fill stitch length | `inkstitch:max_stitch_length_mm` | mm |
| fill underlay spacing | `inkstitch:fill_underlay_row_spacing_mm` | mm |
| pull compensation | `inkstitch:pull_compensation_mm` | mm；已验证改变包围盒 |
| satin density | `inkstitch:zigzag_spacing_mm` | mm，针入点间距 |
| satin heavy underlay | `contour_underlay` + `zigzag_underlay` + insets | 已验证针数增加 |
| satin light underlay | `center_walk_underlay` | 单中心线 |

## 5. 实测（40×30 mm 填充 / 20×40 mm 缎面）

| 用例 | 针数 | 包围盒 |
| --- | --- | --- |
| fill woven（pull 0.20，row 0.40） | 1440 | 9.638..50.380 × 10.0..40.203 |
| fill knit（pull 0.30，row 0.42） | 1432 | 9.530..50.488 × 10.0..40.113 |
| satin woven（pull 0.20，中心线） | 243 | 9.8..30.2 × 10..50 |
| satin knit（pull 0.30，轮廓+锯齿） | 343 | 9.7..30.3 × 10..50 |

说明：knit 的填充包围盒更宽（补偿更大），缎面针数明显更多（重打底生效）。这与文档规则一致。

## 6. 边界与后续

- 这些是**起点**，不是生产认证；必须按 `docs/05-production-quality.md` 做试缝。
- Ink/Stitch 的 `*_mm` 参数在读取时会乘 `PIXELS_PER_MM`（`element.py:142-143`），
  所以 SVG 中写毫米值；本仓库已验证。
- Roidery 的缎面密度定义是“单边相邻针入点间距”，与 Ink/Stitch 的 `zigzag_spacing_mm`
  语义一致，已按此映射；更复杂的缎面分割/收针仍待 P1 补测。
- Wilcom 的数值预设未公开成表格；本仓库只用其定性规则交叉验证，不复制其专有数据。
