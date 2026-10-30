# Phase 1 spike: Ink/Stitch headless

Reproduces `docs/research/inkstitch-headless.md` on Windows.

## 1. Python 3.11 env

```powershell
conda create -y -p D:\stitchord\.condaenv -c conda-forge --override-channels python=3.11 pip
D:\stitchord\.condaenv\python.exe -m pip install -r tools\spike\requirements-inkstitch.txt
```

## 2. inkex at the pinned fork commit

```powershell
git init .research\repos\inkex
git -C .research\repos\inkex remote add origin https://gitlab.com/CapellanCitizen/extensions.git
git -C .research\repos\inkex -c http.proxy=http://127.0.0.1:7890 `
    -c https.proxy=http://127.0.0.1:7890 -c http.sslBackend=openssl `
    fetch --depth 1 origin a887f9d4c8adacd62786e4f46c8ef1467bedc1df
git -C .research\repos\inkex checkout FETCH_HEAD
```

## 3. Run

```powershell
$env:PYTHONPATH='D:\stitchord\.research\repos\inkex;D:\stitchord\.research\repos\inkstitch'
D:\stitchord\.condaenv\python.exe tools\spike\inkstitch_headless.py
```

Outputs: `artifacts/p1/rect.dst`, `artifacts/p1/two_colors.dst`, `*.plan.json`.

## 4. Notes

- wxPython is required at import time (see research doc F2); this is not a GUI requirement.
- The spike disables Ink/Stitch's disk cache before importing elements.
- This is a spike, not production code; production adapter will live under `services/`.
