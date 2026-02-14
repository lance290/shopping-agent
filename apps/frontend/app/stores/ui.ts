/**
 * UI store: manages sidebar, modals, and other UI state
 */

import { create } from 'zustand';

interface UIStoreState {
  // Core state
  isSidebarOpen: boolean;
  isReportBugModalOpen: boolean;

  // Actions
  setSidebarOpen: (isOpen: boolean) => void;
  toggleSidebar: () => void;
  setReportBugModalOpen: (isOpen: boolean) => void;
}

export const useUIStore = create<UIStoreState>((set) => ({
  // Initial state
  isSidebarOpen: false,
  isReportBugModalOpen: false,

  setSidebarOpen: (isOpen) => set({ isSidebarOpen: isOpen }),
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setReportBugModalOpen: (isOpen) => set({ isReportBugModalOpen: isOpen }),
}));
