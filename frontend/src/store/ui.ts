import { create } from "zustand";

type UiState = {
  currentSessionId: string | null;
  setCurrentSessionId: (value: string | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (value: boolean) => void;
};

export const useUiStore = create<UiState>((set) => ({
  currentSessionId: null,
  setCurrentSessionId: (value) => set({ currentSessionId: value }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (value) => set({ isSidebarOpen: value })
}));
