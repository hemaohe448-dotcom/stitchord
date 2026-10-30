# Ink/Stitch worker (Phase 1)

Headless adapter around a pinned Ink/Stitch checkout. No Inkscape process, no
`inkstitch.py` extension dispatch. Requires Python 3.11 and wxPython at import time
(see `docs/research/inkstitch-headless.md`).

## Run locally (Windows, existing `.condaenv`)

```powershell
$env:PYTHONPATH='D:\stitchord\.research\repos\inkex;D:\stitchord\.research\repos\inkstitch'
D:\stitchord\.condaenv\python.exe services\inkstitch_worker\worker.py `
  --svg services\inkstitch_worker\fixtures\two_paths.svg `
  --dst artifacts\worker\two_paths.dst `
  --plan artifacts\worker\two_paths.plan.json
```

Expected: 2 color blocks, ~419 stitches, deterministic DST hash across runs.

## Status

- [x] Flat SVG (paths with fill) -> StitchPlan JSON + DST
- [x] Deterministic output (cache disabled, fixed DST name not yet handled)
- [ ] Satin / running / underlay parameters
- [ ] PES and other formats
- [ ] Docker image (not built; Docker unavailable on the current machine)
- [ ] Golden corpus + comparison against Inkscape reference
