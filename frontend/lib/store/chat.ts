"use client";

import { create } from "zustand";
import type { ChatMessage } from "@/lib/types";

interface ChatState {
  open: boolean;
  context: { investigationId?: string; page?: string };
  messages: ChatMessage[];
  setOpen: (open: boolean) => void;
  setContext: (context: { investigationId?: string; page?: string }) => void;
  push: (message: ChatMessage) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set) => ({
  open: false,
  context: {},
  messages: [],
  setOpen: (open) => set({ open }),
  setContext: (context) => set({ context }),
  push: (message) => set((state) => ({ messages: [...state.messages, message] })),
  reset: () => set({ messages: [] }),
}));
