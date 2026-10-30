import { create } from "zustand";
import type { StitchPlan } from "@stitchord/contracts";
import { makeMockPlan } from "./mock";
import { buildSampleDocument } from "./sampleDoc";
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
  hidden: Record<string, boolean>;
  showJumps: boolean;
  fitToken: number;
  past: CompileDocument[];
  future: CompileDocument[];
  dragBase: CompileDocument | null;

  setPlan: (plan: StitchPlan) => void;
  setDoc: (doc: CompileDocument | null) => void;
  newSample: () => void;
  select: (id: string | null) => void;
  updateObject: (id: string, patch: Partial<CompileObject>) => void;
  updateStitch: (id: string, patch: Partial<CompileStitch>) => void;
  setTranslate: (id: string, value: [number, number], commit: boolean) => void;
  addRectangle: () => void;
  addLine: () => void;
  deleteSelected: () => void;
  moveLayer: (layerId: string, delta: number) => void;
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
  hidden: {},
  showJumps: true,
  fitToken: 0,
  past: [],
  future: [],
  dragBase: null,

  setPlan: (plan) => set({ plan }),

  setDoc: (doc) =>
    set({
      doc,
      selectedId: null,
      past: [],
      future: [],
      dragBase: null,
      fitToken: get().fitToken + 1,
    }),

  newSample: () =>
    set({
      doc: buildSampleDocument("woven", "fill"),
      selectedId: null,
      past: [],
      future: [],
      dragBase: null,
      fitToken: get().fitToken + 1,
    }),

  select: (id) => set({ selectedId: id }),

  updateObject: (id, patch) => {
    const { doc, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({ ...obj, ...patch }));
    set({ doc: next, past: [...past, doc], future: [] });
  },

  updateStitch: (id, patch) => {
    const { doc, past } = get();
    if (!doc) return;
    const next = mapObject(doc, id, (obj) => ({
      ...obj,
      stitch: { ...obj.stitch, ...patch },
    }));
    set({ doc: next, past: [...past, doc], future: [] });
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
    set({ doc: next, past: [...past, base], future: [], dragBase: null });
  },

  addRectangle: () => {
    const { doc, past } = get();
    if (!doc) return;
    const { layerId, obj } = makeRect(doc.layers.length);
    const next: CompileDocument = {
      ...doc,
      layers: [...doc.layers, { id: layerId, name: "rect", objects: [obj] }],
    };
    set({ doc: next, past: [...past, doc], future: [], selectedId: obj.id });
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
    set({ doc: next, past: [...past, doc], future: [], selectedId: obj.id });
  },

  deleteSelected: () => {
    const { doc, selectedId, past } = get();
    if (!doc || !selectedId) return;
    const layers = doc.layers
      .map((layer) => ({
        ...layer,
        objects: layer.objects.filter((obj) => obj.id !== selectedId),
      }))
      .filter((layer) => layer.objects.length > 0);
    set({
      doc: { ...doc, layers },
      past: [...past, doc],
      future: [],
      selectedId: null,
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
    set({ doc: { ...doc, layers }, past: [...past, doc], future: [] });
  },

  setFabric: (fabric) => {
    const { doc, past } = get();
    if (!doc) return;
    set({ doc: { ...doc, fabric }, past: [...past, doc], future: [] });
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
    });
  },

  redo: () => {
    const { past, future, doc } = get();
    if (!future.length || !doc) return;
    const next = future[0];
    set({
      doc: next,
      past: [...past, doc],
      future: future.slice(1),
      selectedId: null,
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
    } else {
      window.localStorage.removeItem(STORAGE_KEY);
    }
  } catch {
    /* storage may be full or disabled; editing still works in memory */
  }
});
