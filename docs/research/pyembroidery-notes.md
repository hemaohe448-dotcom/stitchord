# pyembroidery 实测笔记

- 版本：1.5.1
- 日期：2026-10-30
- 环境：Windows / Python 3.14.9 / 工作区 `.pylibs`
- 探针：`scripts/probe_pyembroidery.py`

## 1. 命令常量（实测，勿凭记忆）

```text
STITCH        0
JUMP          1
TRIM          2
STOP          3
END           4
COLOR_CHANGE  5
NEEDLE_AT     177
```

注意：`COLOR_CHANGE` 不是 3，`STOP`/`END` 的顺序也与常见猜测不同。

## 2. 坐标与单位

- `EmbPattern.stitches` 中坐标单位为 **0.1 mm**；
- 写入 DST 后读回，整数坐标保持不变；`bounds()` 返回同样单位；
- 本项目契约用 mm，转换只在 `convert.py` 边界做（`/10` 与 `*10`）。

## 3. API 形态

```python
pattern = pyembroidery.EmbPattern()
pattern.add_thread({"color": "#ff0000", "name": "red"})
pattern.stitch_abs(0, 0)
pattern.color_change()
pattern.end()
pyembroidery.write_dst(pattern, path)   # 只接受路径，不接受 BytesIO
q = pyembroidery.read(path)
```

实测：
- `write_dst(pattern, stream)` 内部 `open(stream, "wb")`，因此**只能传路径**；
- 导出 API 需经临时文件中转（见 `write_stitch_file`）；
- DST 读回后 `threadlist` 为空——DST 不保存线色，预览需回填调色板；
- `read` 返回的 stitches 形如 `[x, y, command]`，末尾含 `END`。

## 4. 对契约的影响

- 色块边界由 `COLOR_CHANGE` 切分；契约不重复保存 `COLOR_CHANGE` 针，避免双换色；
- TRIM/STOP 的 DST 编码尚未验证，P1 需补测试（U-004）；
- 导出临时目录必须可写；容器内用 `/tmp`，本机用 `STITCHORD_WORK_DIR`。

## 5. 待验证

- [ ] TRIM 在 DST 中是否保留，读回是什么命令；
- [ ] PES/JEF/VP3 的 threadlist 字段（color 是 int 还是 str）；
- [ ] 大文件（>10 万针）读写性能与内存。
