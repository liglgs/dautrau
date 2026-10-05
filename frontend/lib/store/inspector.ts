"use client";

import { create } from "zustand";
import type { EvidenceItem } from "@/lib/types";

export interface InspectorTarget {
  investigationId: string;
  evidence: EvidenceItem;
  quoteIndex?: number;
}

interface InspectorState {
  target: InspectorTarget | null;
  open: (target: InspectorTarget) => void;
  close: () => void;
}

export const useInspector = create<InspectorState>((set) => ({
  target: null,
  open: (target) => set({ target }),
  close: () => set({ target: null }),
}));
