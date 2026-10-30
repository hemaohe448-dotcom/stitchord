# StitchPlan 契约 v1.0

> 唯一事实来源：`packages/contracts/src/index.ts` 与 `services/digitizer/app/models.py`。
> 本文件解释语义；JSON Schema 见 `stitch-plan.schema.json`。

## 1. 结构

```json
{
  "schemaVersion": "1.0",
  "unit": "mm",
  "bounds": { "minX": 0, "minY": 0, "maxX": 80, "maxY": 60 },
  "colorBlocks": [
    {
      "id": "cb-1",
      "color": { "hex": "#c0392b", "name": "red", "brand": "Isacord", "code": "1104" },
      "stitches": [
        { "x": 1.2, "y": 3.4, "command": "STITCH" },
        { "x": 5.6, "y": 7.8, "command": "JUMP" }
      ]
    }
  ],
  "stats": {
    "stitchCount": 1,
    "jumpCount": 1,
    "trimCount": 0,
    "colorChanges": 0,
    "colorBlocks": 1
  }
}
```

## 2. 不变量

1. `unit` 固定 `"mm"`；坐标为毫米浮点，Y 轴向下为正。
2. **色块即换色**：`colorBlocks` 的顺序就是缝制顺序；相邻色块之间隐含一次换色。
3. `stitches` 中**不得**出现 `COLOR_CHANGE`；换色由色块边界表达。
4. `STITCH` 表示“从当前位置缝到该点”；`JUMP` 表示“移动到该点但不缝”；`TRIM` 表示剪线后移动；
   `STOP`/`END`/`NEEDLE_AT` 为机器控制，不产生几何。
5. `bounds` 覆盖所有色块的所有点；允许略大于实际针迹包围盒，但不得小于。
6. `stats` 必须与内容一致；消费方可以重算校验，不一致视为无效。
7. `id` 在单次计划内唯一、稳定；重新生成时允许变化，但需与文档对象 id 建立映射。
8. 坐标精度：内部保留 ≥ 3 位小数；导出 DST 时按 0.1 mm 量化。

## 3. 单位与量化

- 契约：mm；
- DST/PES 等：0.1 mm（整数）；
- 量化规则：`round(mm * 10)`，采用银行家舍入还是四舍五入必须在导出器固定并测试；
- 预览必须使用**导出后的量化坐标**，否则会出现“预览与成品差半针”。

## 4. 版本策略

- `schemaVersion` 采用 `MAJOR.MINOR`；破坏性变更升 MAJOR；
- 新增可选字段升 MINOR；消费方必须忽略未知字段；
- 迁移函数与契约测试必须同时更新；
- 所有 API 响应带 `schemaVersion`，前端 `isStitchPlan` 做最小校验。

## 5. 与 Ink/Stitch 的关系

- Ink/Stitch 的 StitchPlan 是内部对象；本契约是跨进程投影；
- 命令映射以 pyembroidery 实测常量为准（见 `docs/research/pyembroidery-notes.md`）；
- 任何映射变更必须附实测证据与回归测试。
