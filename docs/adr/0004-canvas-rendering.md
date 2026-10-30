# ADR-0004：画布用 Canvas，不用 SVG DOM

- 状态：接受
- 日期：2026-10-30

## 背景

绣花文件动辄数万针；SVG DOM 节点数会拖垮浏览器。Embroiderly 也用 Canvas/WASM 路线。

## 决策

- Phase 0–2：Canvas 2D 批量 path 渲染；
- 超过性能预算后切 WebGL（PixiJS 或自研批处理）；
- 选中框、节点手柄等少量交互元素用独立 DOM/SVG 覆盖层；
- 命中测试用空间索引（rbush），不依赖 DOM。

## 后果

- 需要自己做坐标变换、命中测试、可访问性替代；
- 渲染与导出共用 StitchPlan，避免两套几何；
- 大文档可分块/离屏渲染。
