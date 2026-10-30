# T-0201：Roidery 构建门槛（Phase 2）

状态: done
负责人: CI（GitHub Actions）
依赖: 无
对应决策: ADR-0006

## 目标

在 Windows runner（自带 MSVC）上构建 Roidery 的无头 CLI，并用一个最小 SVG 导出 DST；
以此决定是否把 Roidery 作为服务端制版内核或编辑器内核接入。

## 非目标

- 不构建桌面 GUI / WASM；
- 不修改 Roidery 源码；
- 不评估 UI/UX（另有调研）。

## 输入

- Roidery commit `0187f73daf2b5b05ff9e88cacc8c972c6abb9687`
- workflow：`.github/workflows/roidery-build-gate.yml`
- 人工操作手册：`docs/07-github-actions-guide.md`
- 结果回填表：`docs/reviews/roidery-build-result.md`

## 验收标准

- [x] AC1 `cargo build --release -p vectorcraft-cli` 成功（记录耗时、target 大小）；
- [x] AC2 `vectorcraft-cli run --in smoke.svg --cmd select.all --cmd stitch.export` 退出码 0；
- [x] AC3 产出 DST > 0 字节（**4,721 bytes**；SHA-256 未在回填中提供）；
- [x] AC4 失败时日志能定位到 crate/命令（本次成功，无失败日志）；
- [x] AC5 结果写回 ADR-0006：通过 → 评估接入；不通过 → 自研编辑器继续。

## 证据

- GitHub Actions run：
  https://github.com/hemaohe448-dotcom/stitchord/actions/runs/41044768131/job/124026066868
- 构建耗时：15m 10s；DST：4,721 bytes；结论：成功。
- 回填表：`docs/reviews/roidery-build-result.md`
- ADR：`docs/adr/0006-roidery-evaluation.md`

## 结果

门槛通过。仅证明 Windows CI 可构建 `vectorcraft-cli` 并导出非空 DST；
未证明功能等价/性能/并发/许可证/部署。下一任务 T-0202 做集成评估，
当前运行时仍为 Ink/Stitch，编辑器仍为自研。

## 风险

- Roidery 依赖 git 版 `craft-libs`，网络/分支变动可能导致构建漂移；
  已固定 Roidery commit，但其 Cargo.lock 内的 git rev 仍需记录。
- Windows runner 的 Rust 1.95 可用性；若不可用，记录实际 stable 版本。
