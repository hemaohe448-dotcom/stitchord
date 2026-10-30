import { create } from "zustand";
import type { StitchPlan } from "@stitchord/contracts";
import { makeMockPlan } from "./mock";

interface EditorState {
  plan: StitchPlan;
  hidden: Record<string, boolean>;
  showJumps: boolean;
  fitToken: number;
  setPlan: (plan: StitchPlan) => void;
  toggleBlock: (id: string) => void;
  setShowJumps: (value: boolean) => void;
  requestFit: () => void;
}

export const useEditorStore = create<EditorState>((set) => ({
  plan: makeMockPlan(),
  hidden: {},
  showJumps: true,
  fitToken: 0,
  setPlan: (plan) => set({ plan, hidden: {}, fitToken: 0 }),
  toggleBlock: (id) =>
    set((state) => ({
      hidden: { ...state.hidden, [id]: !state.hidden[id] },
    })),
  setShowJumps: (value) => set({ showJumps: value }),
  requestFit: () => set((state) => ({ fitToken: state.fitToken + 1 })),
}));
