# 06 开发环境（Windows）

## 1. 本机实测环境

| 组件 | 版本 / 路径 |
| --- | --- |
| OS | Windows（工作区 `D:\stitchord`） |
| Node | v24.22.1（`C:\Users\22242\.local\node-v24.22.1-win-x64`） |
| npm | 11.19.1 |
| Python | 3.14.9（`D:\miniconda\python.exe`） |
| Git | 2.56.0 |
| 代理 | `http://127.0.0.1:7890`（Clash 类工具，fake-IP 模式） |
| 缺失 | Docker、Inkscape、Codex CLI、Rust |

> 生产/CI 用 Python 3.11（Ink/Stitch 要求 ≥3.11，且 wxPython/依赖在 3.11 最稳）。
> 本机 3.14 只用于 Phase 0 的 pyembroidery 快速验证。

## 2. 网络（重要）

系统 DNS 会把 github.com 解析到 `198.18.x.x`（代理 fake-IP），`curl`/`web_fetch` 直连会失败；
必须显式走代理：

```powershell
$env:HTTP_PROXY='http://127.0.0.1:7890'
$env:HTTPS_PROXY='http://127.0.0.1:7890'

git -c http.proxy=http://127.0.0.1:7890 `
    -c https.proxy=http://127.0.0.1:7890 `
    -c http.sslBackend=openssl clone --depth 1 <repo>
```

npm 使用环境变量代理即可；缓存建议放工作区，避免沙箱写用户目录失败：

```powershell
$env:npm_config_cache='D:\stitchord\.cache\npm'
npm install --ignore-scripts --no-audit --no-fund
```

## 3. 前端

```powershell
cd D:\stitchord
npm install --ignore-scripts
npm run typecheck -w @stitchord/web
npm run test -w @stitchord/web
npm run build -w @stitchord/web
npm run dev -w @stitchord/web      # http://localhost:5173
```

**沙箱注意**：esbuild 通过管道启动子进程，在 DSH workspace-write 沙箱下会 `spawn EPERM`。
因此 `vite dev/build`、`vitest` 需要在**完全权限**下运行，或在普通 PowerShell 终端运行。
只读的 `tsc --noEmit` 不受影响。

## 4. 后端（Phase 0）

本机没有可用的 venv（`ensurepip` 子进程被沙箱拦截），采用“工作区本地依赖目录”：

```powershell
# 一次性：安装依赖到 D:\stitchord\.pylibs
$env:PIP_CACHE_DIR='D:\stitchord\.cache\pip'
D:\miniconda\python.exe -m pip install --proxy http://127.0.0.1:7890 `
  --no-cache-dir --target D:\stitchord\.pylibs `
  fastapi "uvicorn[standard]" pyembroidery pytest httpx python-multipart
```

运行 API：

```powershell
$env:PYTHONPATH='D:\stitchord\.pylibs;D:\stitchord\services\digitizer'
cd D:\stitchord
D:\miniconda\python.exe -m uvicorn app.main:app --port 8000
```

运行测试：

```powershell
$env:PYTHONPATH='D:\stitchord\.pylibs;D:\stitchord\services\digitizer'
cd D:\stitchord\services\digitizer
D:\miniconda\python.exe -m pytest -q
```

**沙箱注意**：pytest 的临时目录与 pip 的解包目录在沙箱下会被拒绝访问（`PermissionError`），
需要完全权限运行，或在 CI / 普通终端运行。CI 使用标准 venv，不受此限制。

## 5. 前后端联调

- 前端 Vite 已配置 `/api` → `http://127.0.0.1:8000`；
- 启动顺序：API → 前端；
- 打开 http://localhost:5173，导入 DST/PES 或直接看示例花样，点“导出 DST”。

### 5.1 文档生成（`/v1/digitize`，需 Python 3.11）

`/v1/digitize` 需要 Ink/Stitch，只能在 3.11 worker 环境运行：

```powershell
$env:PYTHONPATH='D:\stitchord\services\digitizer;D:\stitchord\.research\repos\inkex;D:\stitchord\.research\repos\inkstitch'
cd D:\stitchord\services\digitizer
D:\stitchord\.condaenv\python.exe -m uvicorn app.main:app --port 8000
```

启动后，网页“参数 / 生成”面板会调用该接口；测试：

```powershell
$env:PYTHONPATH='D:\stitchord\services\digitizer;D:\stitchord\.research\repos\inkex;D:\stitchord\.research\repos\inkstitch'
D:\stitchord\.condaenv\python.exe -m pytest -q
```

## 6. Docker（Phase 1 起）

本机暂未安装 Docker。安装后：

```bash
docker compose -f infra/docker-compose.yml up --build
```

Phase 1 的 digitizer 镜像会包含固定 commit 的 Ink/Stitch；镜像 digest 记录到
`docs/versions.lock.md`。

## 7. 环境变量

| 变量 | 默认 | 用途 |
| --- | --- | --- |
| `STITCHORD_WORK_DIR` | 系统临时目录 | 服务端导出临时文件目录 |
| `STITCHORD_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | CORS 白名单 |
| `STITCHORD_MAX_UPLOAD` | 25 MB（代码常量） | 上传限制 |

## 8. 已知问题

1. `npm install` 在沙箱下会因 spawn 失败；使用 `--ignore-scripts` 或完全权限。
2. Python 3.14 + 系统临时目录：pytest/pip 会 `PermissionError`；用完全权限或 CI。
3. 代理的 MITM 证书会让 curl(schannel) 报 `SEC_E_NO_CREDENTIALS`；用 git(openssl)/npm/Node，不要用 curl 直连。
4. `D:\stitchord\.research\repos\` 是只读研究克隆，已 gitignore，不进入项目源码。
