import { create } from "zustand";
import { persist } from "zustand/middleware";
import { Workspace } from "@/types";

interface WorkspaceState {
  activeWorkspaceId: string | null;
  activeWorkspace: Workspace | null;
  setActiveWorkspace: (workspace: Workspace | null) => void;
  setActiveWorkspaceId: (id: string | null) => void;
}

export const useWorkspaceStore = create<WorkspaceState>()(
  persist(
    (set) => ({
      activeWorkspaceId: null,
      activeWorkspace: null,
      setActiveWorkspace: (workspace) =>
        set({
          activeWorkspace: workspace,
          activeWorkspaceId: workspace?.id || null,
        }),
      setActiveWorkspaceId: (id) => set({ activeWorkspaceId: id }),
    }),
    {
      name: "contexthub_workspace_storage",
      partialize: (state) => ({ activeWorkspaceId: state.activeWorkspaceId }),
    }
  )
);
