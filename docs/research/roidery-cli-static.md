# Roidery CLI 静态评估（T-0202，进行中）

> 日期：2026-10-30；Roidery commit `0187f73daf2b5b05ff9e88cacc8c972c6abb9687`。
> 本文只来自源码/文档/CI 元数据，**不含运行结果**；运行评估仍未完成。

## 1. 入口

`apps/vectorcraft-cli/src/main.rs`：

- `run`：无头批处理，`--in FILE` 打开（任意可读格式）或新建，
  `--cmd ID [--params JSON]` 依次执行，`--export FILE` 额外导出；
- `convert`：`IN OUT` 格式转换；
- `info` / `bench` / `perf`；
- `mcp`：MCP stdio 服务（`mcp --headless` 可无 GUI）。

README 的示例（`README.md:106-112`）：

```sh
vectorcraft-cli run --in art.svg --cmd select.all \
  --cmd stitch.export --params '{"path":"art.dst"}'
```

## 2. 输入/输出

- 输入：`document.open` 能读的格式，SVG 只是其中一种；
- 导出：`stitch.export` 参数 `path`，格式由扩展名推断；
- `--export` 也支持 SVG/PNG/原生 `.vectorcraft`（CLI 测试 `run_batch_exports`）。

## 3. 构建与依赖

- workspace `version = "0.10.0"`，`edition = 2024`，`rust-version = "1.95"`；
- CLI 依赖 `vectorcraft-engine`、`vectorcraft-render` 等（不是独立小二进制）；
- Windows 下额外依赖 `winsafe` / DirectWrite（字体枚举），非 Windows 有 CoreText 分支；
- 是否存在 GPU/显示硬依赖：**TODO(verify)**，需实际在 Linux 容器运行。

## 4. 许可证

- 根 `Cargo.toml`：`license = "MIT OR Apache-2.0"`；
- `NOTICE` 记录 VectorCraft 版权、Roidery 分支关系，以及第三方素材：
  pyembroidery 线色表（MIT）、Lucide（ISC/MIT）、Source Sans/Serif/Inter（OFL-1.1）；
- 若接入，需要保留 `NOTICE` 与第三方许可证文本；具体分发方式见 T-0202 AC5。

## 5. CI 构建证据

| 项 | 值 |
| --- | --- |
| run | https://github.com/hemaohe448-dotcom/stitchord/actions/runs/41044768131/job/124026066868 |
| 结论 | 成功 |
| 耗时 | 15m 10s |
| artifact | `roidery-smoke-dst`，zip 1,392 B，zip SHA-256 `5ef38cdd076a7267b8bdd2ba274ae698e730c82a052debdfee2436ff7cee4a05`（GitHub API 元数据） |
| DST | 4,721 B（用户回填） |

artifact 下载需要 GitHub 认证（未提供 token），因此本轮**无法读回 DST 做针数/色块对比**。

## 6. 结论（暂定）

- CLI 的批处理入口和“任意格式读入 + stitch.export”满足服务端评估的最低形态；
- 构建体积/GPU/Linux 可移植性/针迹等价性都未验证，不能仅凭“构建成功”切换到 Roidery；
- 当前运行时继续 Ink/Stitch，T-0202 仍为 `doing`。
