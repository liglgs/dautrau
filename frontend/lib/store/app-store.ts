"use client";

import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { Role } from "@/lib/types";

export type Density = "comfortable" | "compact";

interface AppState {
  role: Role;
  demoMode: boolean;
  density: Density;
  sidebarCollapsed: boolean;
  commandOpen: boolean;
  setRole: (role: Role) => void;
  toggleDemoMode: () => void;
  setDensity: (density: Density) => void;
  toggleSidebar: () => void;
  setCommandOpen: (open: boolean) => void;
}

export const useAppStore = create<AppState>()(
  persist(
    (set) => ({
      role: "investigator",
      demoMode: true,
      density: "comfortable",
      sidebarCollapsed: false,
      commandOpen: false,
      setRole: (role) => set({ role }),
      toggleDemoMode: () => set((state) => ({ demoMode: !state.demoMode })),
      setDensity: (density) => set({ density }),
      toggleSidebar: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      setCommandOpen: (commandOpen) => set({ commandOpen }),
    }),
    {
      name: "vigilens-app",
      // Không đọc localStorage trong lúc render: máy chủ và trình duyệt phải dựng cùng một cây.
      // `Providers` gọi `useAppStore.persist.rehydrate()` sau khi mount.
      skipHydration: true,
    },
  ),
);

export const ROLE_LABEL: Record<Role, string> = {
  visitor: "Khách",
  investigator: "Điều tra viên",
  reviewer: "Dược sĩ duyệt",
  admin: "Quản trị",
};

export function canReview(role: Role) {
  return role === "reviewer";
}

/** Yêu cầu agent tìm thêm bằng chứng: người duyệt gửi quyết định, quản trị xem được cùng luồng. */
export function canRequestMore(role: Role) {
  return role === "reviewer" || role === "admin";
}
