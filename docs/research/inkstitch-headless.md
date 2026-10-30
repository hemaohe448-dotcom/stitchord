# Ink/Stitch 无头验证（2026-10-30）

> 结论先行：**Ink/Stitch 的绣法管线可以在没有 Inkscape GUI 的进程里直接调用**，生成
> StitchPlan 与 DST，且输出确定。但它**仍然需要 wxPython**（不是 GUI 显示，而是 import 链）。
> 这不等于“无依赖”，生产镜像必须安装 wxPython/GTK，或维护一份较深的惰性化补丁。

## 1. 环境

| 组件 | 版本 / 来源 |
| --- | --- |
| Python | 3.11.18（conda-forge，`.condaenv`） |
| Ink/Stitch | `d22526223c2296044d9dd6145cc78de3bb0d5c75`（2026-10-27） |
| inkex | `a887f9d4c8adacd62786e4f46c8ef1467bedc1df`（`CapellanCitizen/extensions`） |
| wxPython | 4.3.2（Windows wheel） |
| pystitch | 1.0.1 |
| pyembroidery | 1.5.1（仅用于读回验证） |

复现脚本：`tools/spike/inkstitch_headless_v2.py`；依赖：`tools/spike/requirements-inkstitch.txt`。

## 2. 实测结果

### 2.1 10×10 px 矩形（默认填充）

```json
{"name":"rect","elements":["FillStitch"],"blocks":1,"stitches":48,
 "dst_bytes":662,"sha256":"ab5ffbf7...b950",
 "bounds":{"minX":0.0,"minY":0.0,"maxX":2.646,"maxY":2.646}}
```

### 2.2 两条不同颜色填充路径

```json
{"name":"two_colors","elements":["FillStitch","FillStitch"],"blocks":2,"stitches":419,
 "dst_bytes":1781,"sha256":"82381741...31b7",
 "bounds":{"minX":2.646,"minY":2.646,"maxX":23.812,"maxY":10.583}}
```

- 颜色：`#c0392b` / `#2980b9`（来自 SVG inline style）；
- 色块数 = 2，符合预期；
- 连续运行两次，两个 DST 的 SHA-256 完全一致（确定性成立）。

## 3. 关键发现

### F1. 可以绕过 Inkscape 与 `inkstitch.py` 入口

直接使用：

```python
from lib.elements import node_to_elements
from lib.stitch_plan.stitch_plan import stitch_groups_to_stitch_plan
from lib import output

[element] = node_to_elements(node)
groups = element.embroider(None)
plan = stitch_groups_to_stitch_plan(groups)
output.write_embroidery_file(path, plan, svg_root, settings={"date": ""})
```

不经过 `inkstitch.py` 的 `--extension` 反射，也不需要 Inkscape 进程。这比 CLI 更适合 worker：
输入/输出是文件与对象，不依赖 Inkscape 的 stdout 二进制协议。

### F2. 但 `lib.elements` 仍然依赖 wxPython

失败链（未安装 wx 时）：

```text
lib.elements → fill_stitch → lib.stitches → tartan_fill → lib.tartan.palette → import wx
lib.elements.utils.nodes → node_to_elements() → from ...sew_stack import SewStack
  → lib.sew_stack.stitch_layers → ... → stitch_layer_editor → import wx.html
```

- `lib/tartan/palette.py:10` 顶层 `import wx`（只用于 GUI 的 stripe sizer 方法）；
- `lib/sew_stack/__init__.py:1` 顶层 `import wx`（实际未使用）；
- `lib/sew_stack/stitch_layers/stitch_layer_editor.py:4` 顶层 `import wx.html`；
- `lib/elements/utils/nodes.py:45` 在 `node_to_elements()` 内**无条件**构造 `SewStack(node)`。

尝试过最小惰性化补丁（tartan + sew_stack），仍被 `stitch_layer_editor` 挡住；继续打补丁会侵入
GUI 包，维护成本高于收益。**决策：Phase 1 worker 镜像安装 wxPython/GTK**，不做深度 fork。

### F3. 必须关闭 Ink/Stitch 磁盘缓存

默认会写 `%LOCALAPPDATA%\inkstitch\...\cache\stitch_plan\cache.db`；在受限/只读 HOME 或并发 worker
下会抛 `PermissionError`。无头模式必须在导入元素前设置：

```python
import lib.utils.settings as settings
settings.global_settings._settings["cache_size"] = 0
```

### F4. 坐标：plan 是 px，DST 是 0.1 mm 且被居中

- `StitchPlan` 内坐标是 SVG 用户单位（96 dpi）：10 px 矩形 → `maxX=2.646 mm`；
- `write_embroidery_file()` 用 `scale = 10 / PIXELS_PER_MM` 转 0.1 mm，并以
  `origin = bbox 中心` 平移（`lib/output.py:56-93`）；
- 因此 DST 读回的 bounds 是 `(-106,-40,106,40)`（0.1 mm），而 plan 是 `2.646..23.812 mm`。
- 预览/导出比较时必须先按 bbox 中心平移，不能直接逐点比较。

### F5. 颜色对象没有 `.hex`

`ThreadColor` 暴露的是 `hex_digits`（如 `C0392B`），不是 `hex`。投影到 StitchPlan 时要拼 `#`：

```python
digits = getattr(block.color, "hex_digits", None)
hex_color = f"#{digits.lower()}" if digits else "#000000"
```

### F6. 确定性可用

同一输入、同一版本、关闭缓存后，连续两次 DST 字节级一致（见上方 SHA）。这满足 P1-AC4 的基础条件，
但还要固定 DST 头名称（`pattern.extras['name']` 来自 SVG 文件名，`lib/output.py:64`）。

### F7. `INKSTITCH_OFFLINE_SCRIPT` 不是无头开关

它只影响调试器/脚本生成路径（`inkstitch.py:75-101`），与“无 GUI 执行”无关。无头能力来自
直接调用库，而不是这个环境变量。

## 4. 尚未验证

- satin / running / underlay / 跳针 / 锁针等更多绣法；
- 参数属性映射（fill angle、row spacing、pull compensation 等）；
- PES 导出与线色；
- 2 万针性能；
- Linux 容器内 wxPython/GTK 安装与运行；
- 与 Inkscape 原生输出的逐针对比（需要安装 Inkscape 作为参考环境）。

## 5. 对架构的影响

- **P1 实现路径改为“库调用”**（原 ADR-0002 的 B 方案作为容器内实现），系统边界仍是独立 worker；
- 需要维护一个薄适配层：`SVG/文档 → node_to_elements → embroider → StitchPlan/DST`；
- 镜像体积会因 wxPython/GTK 增大；若不可接受，再评估深补丁或自研绣法；
- 参数映射仍是最大工作量，不能因为“跑通 DST”而跳过。
