# Ink/Stitch 源码笔记（Phase 1 依据）

- 仓库：`inkstitch/inkstitch`
- Commit：`d22526223c2296044d9dd6145cc78de3bb0d5c75`（2026-10-27）
- 许可证：GPL-3.0
- 本地路径（研究克隆，不提交）：`.research/repos/inkstitch/`

## 1. 运行形态

- 不是独立应用，而是 Inkscape 扩展集合；
- 入口 `inkstitch.py`：解析 `--extension=<name>`，把 `foo_bar` 转成 `FooBar` 类并实例化
  （`inkstitch.py:127-147`）；
- 离线脚本开关：环境变量 `INKSTITCH_OFFLINE_SCRIPT`（`inkstitch.py:75-79`）；
- 导出扩展 `lib/extensions/output.py`：
  - 解析 `--format=...` 等自定义参数（`output.py:19-38`）；
  - `elements_to_stitch_groups` → `stitch_groups_to_stitch_plan` → `write_embroidery_file`
    （`output.py:40-75`）；
  - 结果写到 **stdout 二进制**，由 Inkscape 负责落盘。

## 2. 关键模块

| 模块 | 作用 |
| --- | --- |
| `lib/elements/` | SVG 元素 → 绣法参数/几何 |
| `lib/stitches/` | 14 个绣法模块（running/satin/fill/tatami/contour/guided/meander/ripple/cross-stitch/…） |
| `lib/stitch_plan/` | StitchPlan / ColorBlock / Stitch / 生成与读取 |
| `lib/output.py` | StitchPlan → pystitch 写入器（DST/PES/…） |
| `lib/threads/` | 线色目录与调色板匹配 |
| `lib/extensions/` | 80+ 扩展入口（output/params/lettering/simulator/…） |

## 3. 无头调用假设（必须由 T-0101 证实）

假设（**未验证**，不得写进实现）：

```bash
INKSTITCH_OFFLINE_SCRIPT=true \
python inkstitch.py --extension=output --format=dst input.svg > out.dst
```

需要确认：
- 输入 SVG 是位置参数还是 stdin；
- 是否需要 `--output` / `--id` 等 inkex 参数；
- 退出码与错误输出（stderr）约定；
- 无 wxPython 时 import 链是否失败；
- `--format` 支持列表与大小写。

## 4. 针迹计划 JSON 的取得方式

两条路：

1. **补丁扩展**（推荐）：在 worker 内新增 `lib/extensions/stitch_plan_json.py`，复用
   `elements_to_stitch_groups` + `stitch_groups_to_stitch_plan`，序列化为契约 JSON；
   GPL 补丁随镜像公开。
2. 先导出 DST，再用 pyembroidery 读回（会丢失参数与部分命令语义，仅作降级）。

## 5. 参数映射的提取方法

禁止凭记忆写属性名。步骤：

1. 在 `lib/elements/*.py` 中搜 `inkstitch:` / `param` / `get_param`；
2. 在 `lib/inx/*.inx` 中找 UI 名称、默认值、单位；
3. 用 Ink/Stitch 在 Inkscape 里对同一图形导出 SVG，观察实际写入的属性；
4. 每条记录到 `docs/contracts/inkstitch-params.md`：属性名、类型、单位、默认值、源码行号、验证日期。

## 6. 风险

- 依赖 wxPython/GTK：容器体积大，import 可能失败；
- Inkscape 文档模型（命名空间、layer、clone、LPE）比我们需要的复杂；
- 版本升级可能改变参数语义；
- 导出到 stdout 的二进制协议不适合直接做 API，需要包装。

## 7. P1 最小目标

- 3 种绣法（running / satin / tatami fill）+ 单色/双色 + 跳针；
- 12 份黄金 SVG；
- DST + PES 两种输出；
- StitchPlan JSON；
- 确定性 hash；
- 失败输入的结构化错误。
