# ADR-0007：对象级针迹组缓存（局部重算 MVP）

- 状态：接受
- 日期：2026-10-30
- 相关：ADR-0002、`services/digitizer/app/inkstitch_adapter.py`

## 背景

Ink/Stitch 的编译入口是整份 SVG：`stitch_groups_to_stitch_plan(groups)` 需要全部对象。
直接“只编译一个对象”会改变跳针/换色/边界行为，不能保证与完整文档一致。

但实际耗时主要在 **每个叶子对象的 `element.embroider()`**，而不是最后的 plan 组装。

## 决策

1. 以 **SVG 叶子元素**（编译器为每个对象生成 `<path id="obj-id">`）为缓存单元；
2. 缓存 key = 叶子元素序列化 XML + 根 `width/height/viewBox/version` 的 SHA-256；
3. 命中则复用该对象的 stitch groups；未命中才重新 `embroider()`；
4. 每次仍对所有 groups 调用 `stitch_groups_to_stitch_plan`，保证跳针/换色/边界行为
   与完整编译一致；
5. 缓存为进程内 LRU（最多 256 个对象），不持久化；对象内容/参数/位移变化会自然失效。

## 证据

`tests/test_digitize.py::test_object_group_cache_reuses_unchanged_objects`：

- 同一文档第二次编译：`groups_reused == 2`，DST 字节与第一次完全相同；
- 只移动红色对象后：复用一个未变对象，蓝色色块 stitches 数组逐项相同；
- 改变的对象重新生成，DST 不同。

## 后果

- 未变对象不再重复做绣法展开，编辑大文档时是实际加速；
- 输出仍与整文档编译一致（测试约束），不会出现“预览/导出不一致”；
- 局限性：plan 组装仍全量；缓存只在单进程；跨进程/多副本不共享；
- 若 Ink/Stitch 的 `element.embroider()` 引入跨对象状态，本缓存需重新审计。
