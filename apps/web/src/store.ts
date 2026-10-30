import { create } from "zustand";
import type { StitchPlan } from "@stitchord/contracts";
import { makeMockPlan } from "./mock";
import { pushHistory } from "./history";
import { buildSampleDocument } from "./sampleDoc";
import { serializePolyline } from "./path";
import type {
  CompileDocument,
  CompileObject,
  CompileStitch,
} from "./sampleDoc";

const COLORS = ["#c0392b", "#2980b9", "#2e7d32", "#dd6b20", "#805ad5"];

function cloneDocument(doc: CompileDocument): CompileDocument {
  return {
    ...doc,
    layers: doc.layers.map((layer) => ({
      ...layer,
      objects: layer.objects.map((obj) => ({
        ...obj,
        stitch: { ...obj.stitch },
        translateMm: obj.translateMm ? ([...obj.translateMm] as [number, number]) : undefined,
      })),
    })),
  };
}

function mapObject(
  doc: CompileDocument,
  id: string,
  update: (obj: CompileObject) => CompileObject,
): CompileDocument {
  return {
    ...doc,
    layers: doc.layers.map((layer) => ({
      ...layer,
      objects: layer.objects.map((obj) => (obj.id === id ? update(obj) : obj)),
    })),
  };
}

function makeRect(index: number): { layerId: string; obj: CompileObject } {
  const x = 10 + (index % 3) * 30;
  const y = 55 + Math.floor(index / 3) * 15;
  return {
    layerId: `layer-rect-${Date.now()}-${index}`,
    obj: {
      id: `obj-rect-${Date.now()}-${index}`,
      pathD: `M ${x},${y} L ${x + 25},${y} L ${x + 25},${y + 12} L ${x},${y + 12} Z`,
      color: { hex: COLORS[index % COLORS.length], name: "rect" },
      stitch: { type: "fill" },
    },
  };
}

interface EditorState {
  doc: CompileDocument | null;
  plan: StitchPlan;
  selectedId: string | null;
  selectedIds: string[];
  hidden: Record<string, boolean>;
  showJumps: boolean;
  fitToken: number;
  past: CompileDocument[];
  future: CompileDocument[];
  dragBase: CompileDocument | null;

  setPlan: (plan: StitchPlan) => void;
  setDoc: (doc: CompileDocument | null) => void;
  newSample: () => void;
  select: (id: string | null, additive?: boolean) => void;
  updateObject: (id: string, patch: Partial<CompileObject>) => void;
  updateStitch: (id: string, patch: Partial<CompileStitch>) => void;
  setTranslate: (id: string, value: [number, number], commit: boolean) => void;
  setTranslations: (
    entries: Array<{ id: string; value: [number, number] }>,
    commit: boolean,
  ) => void;
  setPath: (id: string, pathD: string, commit: boolean) => void;
  addRectangle: () => void;
  addLine: () => void;
  addFreehand: (points: Array<[number, number]>) => void;
  duplicateSelected: () => void;
  deleteSelected: () => void;
  moveLayer: (layerId: string, delta: number) => void;
  toggleLayer: (layerId: string) => void;
  toggleLayerLock: (layerId: string) => void;
  deleteLayer: (layerId: string) => void;
  duplicateLayer: (layerId: string) => void;
  mergeLayerDown: (layerId: string) => void;
  renameLayer: (layerId: string, name: string) => void;
  setFabric: (fabric: string) => void;
  undo: () => void;
  redo: () => void;
  toggleBlock: (id: string) => void;
  setShowJumps: (value: boolean) => void;
  requestFit: () => void;
}

const initialDoc = buildSampleDocument("woven", "fill");
const STORAGE_KEY = "stitchord.doc.v1";

function loadSavedDoc(): CompileDocument | null {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as CompileDocument;
    if (!parsed || !Array.isArray(parsed.layers) || !parsed.layers.length) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

export const useEditorStore = create<EditorState>((set, get) => ({
  doc: loadSavedDoc() ?? initialDoc,
  plan: makeMockPlan(),
  selectedId: null,
  selectedIds: [],
  hidden: {},
  showJumps: true,
  fitToken: 0,
  past: [],
  future: [],
  dragBase: null,

  setPlan: (plan) => set({ plan }),

  setDoc: (doc) =>
    set((state) => ({
      doc,
      selectedId: null,
      selectedIds: [],
      past: state.doc ? [...state.past, state.doc].slice(-100) : state.past,
      future: [],
      dragBase: null,
      fitToken: state.fitToken + 1,
    })),

  newSample: () =>
    set((state) => ({
      doc: buildSampleDocument("woven", "fill"),
      selectedId: null,
      selectedIds: [],
      past: state.doc ? [...state.past, state.doc].slice(-100) : state.past,
      future: [],
      dragBase: null,
      fitToken: state.fitToken + 1,
    })),

  select: (id, additive = false) =>
    set((state) => {
      if (!id) return { selectedId: null, selectedIds: [] };
      if (!additive) return { selectedId: id, selectedIds: [id] };
      const exists = state.selectedIds.includes(id);
      const selectedIds = exists
        ? state.selectedIds.filter((value) => value !== id)
        : [...state.selectedIds, id];
      return {
        selectedIds,
        selectedId:
          selectedIds.length === 0
            ? null
            : exists
              ? selectedIds[selectedIds.length - 1]
              : id,
      };
    }),

  updateObject: (id, patch) => {
    const { doc, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({ ...obj, ...patch }));
    set({ doc: next, past: pushHistory(past, doc), future: [] });
  },

  updateStitch: (id, patch) => {
    const { doc, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({
      ...obj,
      stitch: { ...obj.stitch, ...patch },
    }));
    set({ doc: next, past: pushHistory(past, doc), future: [] });
  },

  setTranslate: (id, value, commit) => {
    const { doc, dragBase, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({ ...obj, translateMm: value }));
    if (!commit) {
      set({ doc: next, dragBase: dragBase ?? doc });
      return;
    }
    const base = dragBase ?? doc;
    set({ doc: next, past: pushHistory(past, base), future: [], dragBase: null });
  },

  setPath: (id, pathD, commit) => {
    const { doc, dragBase, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({ ...obj, pathD }));
    if (!commit) {
      set({ doc: next, dragBase: dragBase ?? doc });
      return;
    }
    const base = dragBase ?? doc;
    set({ doc: next, past: pushHistory(past, base), future: [], dragBase: null });
  },

  setTranslations: (entries, commit) => {
    const { doc, dragBase, past } = get();
    if (!doc) return;
    let next = doc;
    for (const entry of entries) {
      next = mapObject(next, entry.id, (obj) => ({
        ...obj,
        translateMm: entry.value,
      }));
    }
    if (!commit) {
      set({ doc: next, dragBase: dragBase ?? doc });
      return;
    }
    const base = dragBase ?? doc;
    set({ doc: next, past: pushHistory(past, base), future: [], dragBase: null });
  },

  addRectangle: () => {
    const { doc, past } = get();
    if (!doc) return;
    const { layerId, obj } = makeRect(doc.layers.length);
    const next: CompileDocument = {
      ...doc,
      layers: [...doc.layers, { id: layerId, name: "rect", objects: [obj] }],
    };
    set({ doc: next, past: pushHistory(past, doc), future: [], selectedId: obj.id, selectedIds: [obj.id] });
  },

  addLine: () => {
    const { doc, past } = get();
    if (!doc) return;
    const index = doc.layers.length;
    const x = 15 + (index % 4) * 15;
    const obj: CompileObject = {
      id: `obj-line-${Date.now()}`,
      pathD: `M ${x},60 L ${x + 20},60 L ${x + 20},75`,
      color: { hex: COLORS[index % COLORS.length], name: "line" },
      stitch: { type: "running" },
    };
    const next: CompileDocument = {
      ...doc,
      layers: [
        ...doc.layers,
        { id: `layer-line-${Date.now()}`, name: "line", objects: [obj] },
      ],
    };
    set({ doc: next, past: pushHistory(past, doc), future: [], selectedId: obj.id, selectedIds: [obj.id] });
  },

  addFreehand: (points) => {
    const { doc, past } = get();
    if (!doc || points.length < 2) return;
    const id = `obj-draw-${Date.now()}`;
    const index = doc.layers.length;
    const obj: CompileObject = {
      id,
      pathD: serializePolyline({ points, closed: false }),
      color: { hex: COLORS[index % COLORS.length], name: "freehand" },
      stitch: { type: "running" },
    };
    const next: CompileDocument = {
      ...doc,
      layers: [
        ...doc.layers,
        { id: `layer-draw-${Date.now()}`, name: "freehand", objects: [obj] },
      ],
    };
    set({ doc: next, past: pushHistory(past, doc), future: [], selectedId: id, selectedIds: [id] });
  },

  duplicateSelected: () => {
    const { doc, selectedId, selectedIds, past } = get();
    if (!doc) return;
    const ids = new Set(
      selectedIds.length ? selectedIds : selectedId ? [selectedId] : [],
    );
    if (!ids.size) return;
    const created: CompileObject[] = [];
    let sequence = 0;
    const layers = doc.layers.map((layer) => {
      const objects: CompileObject[] = [];
      for (const source of layer.objects) {
        objects.push(source);
        if (!ids.has(source.id)) continue;
        sequence += 1;
        const copy: CompileObject = {
          ...source,
          id: `obj-copy-${Date.now()}-${sequence}`,
          color: { ...source.color },
          stitch: { ...source.stitch },
          translateMm: source.translateMm
            ? [source.translateMm[0] + 5, source.translateMm[1] + 5]
            : [5, 5],
        };
        created.push(copy);
        objects.push(copy);
      }
      return { ...layer, objects };
    });
    const last = created[created.length - 1];
    if (!last) return;
    set({
      doc: { ...doc, layers },
      past: pushHistory(past, doc),
      future: [],
      selectedId: last.id,
      selectedIds: created.map((copy) => copy.id),
    });
  },

  deleteSelected: () => {
    const { doc, selectedId, selectedIds, past } = get();
    if (!doc) return;
    const ids = new Set(
      selectedIds.length ? selectedIds : selectedId ? [selectedId] : [],
    );
    if (!ids.size) return;
    const layers = doc.layers
      .map((layer) => ({
        ...layer,
        objects: layer.objects.filter((obj) => !ids.has(obj.id)),
      }))
      .filter((layer) => layer.objects.length > 0);
    set({
      doc: { ...doc, layers },
      past: pushHistory(past, doc),
      future: [],
      selectedId: null,
      selectedIds: [],
    });
  },

  moveLayer: (layerId, delta) => {
    const { doc, past } = get();
    if (!doc) return;
    const index = doc.layers.findIndex((layer) => layer.id === layerId);
    const target = index + delta;
    if (index < 0 || target < 0 || target >= doc.layers.length) return;
    const layers = [...doc.layers];
    [layers[index], layers[target]] = [layers[target], layers[index]];
    set({ doc: { ...doc, layers }, past: pushHistory(past, doc), future: [] });
  },

  toggleLayer: (layerId) => {
    const { doc, past } = get();
    if (!doc) return;
    const target = doc.layers.find((layer) => layer.id === layerId);
    if (!target) return;
    const visibleCount = doc.layers.filter((layer) => layer.visible !== false).length;
    if (target.visible !== false && visibleCount <= 1) return;
    const layers = doc.layers.map((layer) =>
      layer.id === layerId ? { ...layer, visible: layer.visible === false } : layer,
    );
    set({ doc: { ...doc, layers }, past: pushHistory(past, doc), future: [] });
  },

  toggleLayerLock: (layerId) => {
    const { doc, past } = get();
    if (!doc) return;
    const layers = doc.layers.map((layer) =>
      layer.id === layerId ? { ...layer, locked: !layer.locked } : layer,
    );
    set({ doc: { ...doc, layers }, past: pushHistory(past, doc), future: [] });
  },

  deleteLayer: (layerId) => {
    const { doc, past } = get();
    if (!doc || doc.layers.length <= 1) return;
    set({
      doc: { ...doc, layers: doc.layers.filter((layer) => layer.id !== layerId) },
      past: pushHistory(past, doc),
      future: [],
      selectedId: null,
      selectedIds: [],
    });
  },

  duplicateLayer: (layerId) => {
    const { doc, past } = get();
    if (!doc) return;
    const index = doc.layers.findIndex((layer) => layer.id === layerId);
    if (index < 0) return;
    const source = doc.layers[index];
    const stamp = Date.now();
    const copy = {
      ...source,
      id: `layer-copy-${stamp}`,
      name: `${source.name ?? source.id} copy`,
      objects: source.objects.map((obj, objIndex) => ({
        ...obj,
        id: `${obj.id}-copy-${stamp}-${objIndex}`,
        color: { ...obj.color },
        stitch: { ...obj.stitch },
      })),
    };
    const layers = [...doc.layers];
    layers.splice(index + 1, 0, copy);
    set({
      doc: { ...doc, layers },
      past: pushHistory(past, doc),
      future: [],
      selectedId: null,
      selectedIds: [],
    });
  },

  mergeLayerDown: (layerId) => {
    const { doc, past } = get();
    if (!doc) return;
    const index = doc.layers.findIndex((layer) => layer.id === layerId);
    if (index <= 0) return;
    const current = doc.layers[index];
    const previous = doc.layers[index - 1];
    const merged = {
      ...previous,
      objects: [...previous.objects, ...current.objects],
    };
    const layers = [...doc.layers];
    layers.splice(index - 1, 2, merged);
    set({
      doc: { ...doc, layers },
      past: pushHistory(past, doc),
      future: [],
      selectedId: null,
      selectedIds: [],
    });
  },

  renameLayer: (layerId, name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const { doc, past } = get();
    if (!doc) return;
    const layers = doc.layers.map((layer) =>
      layer.id === layerId ? { ...layer, name: trimmed } : layer,
    );
    set({ doc: { ...doc, layers }, past: pushHistory(past, doc), future: [] });
  },

  setFabric: (fabric) => {
    const { doc, past } = get();
    if (!doc) return;
    set({ doc: { ...doc, fabric }, past: pushHistory(past, doc), future: [] });
  },

  undo: () => {
    const { past, future, doc } = get();
    if (!past.length || !doc) return;
    const previous = past[past.length - 1];
    set({
      doc: previous,
      past: past.slice(0, -1),
      future: [doc, ...future],
      selectedId: null,
      selectedIds: [],
    });
  },

  redo: () => {
    const { past, future, doc } = get();
    if (!future.length || !doc) return;
    const next = future[0];
    set({
      doc: next,
      past: pushHistory(past, doc),
      future: future.slice(1),
      selectedId: null,
      selectedIds: [],
    });
  },

  toggleBlock: (id) =>
    set((state) => ({ hidden: { ...state.hidden, [id]: !state.hidden[id] } })),

  setShowJumps: (value) => set({ showJumps: value }),

  requestFit: () => set((state) => ({ fitToken: state.fitToken + 1 })),
}));

export { cloneDocument };

// Persist the editable document (not history/plan) so a refresh keeps the work.
useEditorStore.subscribe((state, previous) => {
  if (state.doc === previous.doc) return;
  try {
    if (state.doc) {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(state.doc));
    }
    // Keep the last real project when an imported machine file temporarily
    // sets doc to null; clearing storage here would lose the user's work.
  } catch {
    /* storage may be full or disabled; editing still works in memory */
  }
});
