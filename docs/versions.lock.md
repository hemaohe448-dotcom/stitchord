# 版本锁定

> 任何“升级”都必须更新本文件并跑回归；禁止浮动版本进入生产。

## 外部项目（研究克隆，不提交源码）

| 项目 | Commit | 日期 | 许可证 | 用途 |
| --- | --- | --- | --- | --- |
| inkstitch/inkstitch | `d22526223c2296044d9dd6145cc78de3bb0d5c75` | 2026-10-27 | GPL-3.0 | 编译/绣法内核 |
| embroidery-space/embroiderly | `38b5f39e1e0a892205c608e0849c9b43be89482c` | 2026-10-17 | GPL-3.0-or-later | UX/架构参考（不复用代码） |

## 运行时与依赖（本机实测）

| 依赖 | 版本 | 来源 |
| --- | --- | --- |
| Node.js | 24.22.1 | 本机 |
| npm | 11.19.1 | 本机 |
| Python | 3.14.9（开发） / 3.11（CI/生产） | 本机 / 规划 |
| react | 19.3.1 | package-lock |
| vite | 7.3.7 | package-lock |
| vitest | 3.2.7 | package-lock |
| typescript | 5.9.3 | package-lock |
| zustand | 5.0.16 | package-lock |
| fastapi | 0.162.0 | pip |
| pydantic | 2.14.2 | pip |
| starlette | 1.10.0 | pip |
| pyembroidery | 1.5.1 | pip |
| python-multipart | 0.0.32 | pip |

## 待锁定（P1）

- [ ] Ink/Stitch 运行镜像 digest；
- [ ] Inkscape 版本（仅用于生成参考输出，不进入生产）；
- [ ] 字体/线色目录版本；
- [ ] Node/Python 基础镜像 digest。
