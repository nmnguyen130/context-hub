"use client";

import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import { FolderKanban, LogOut, Building2 } from "lucide-react";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { useCurrentTenant } from "@/features/tenant/hooks/use-tenant";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { authApi } from "@/lib/api/auth";
import { Badge } from "@/components/ui/badge";
import { toast } from "sonner";

export function AppHeader() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { data: user } = useCurrentUser();
  const { tenantDisplayName, clearTenantSlug } = useCurrentTenant();
  const { data: workspacesData } = useWorkspaces();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceStore();

  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Ignore logout error
    } finally {
      clearTenantSlug();
      queryClient.clear();
      toast.success("Signed out.");
      router.push("/login");
    }
  };

  const workspaces = workspacesData?.items || [];

  const displayName = user?.display_name || user?.email.split("@")[0] || "User";
  const initials = user?.display_name
    ? user.display_name.split(" ").map((n) => n[0]).join("").toUpperCase().slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || "U";

  return (
    <header className="h-16 border-b border-slate-800 bg-slate-950/70 backdrop-blur-md px-6 flex items-center justify-between z-20">
      {/* Workspace Selector */}
      <div className="flex items-center gap-3">
        <div className="flex items-center gap-2 bg-slate-900 border border-slate-800 rounded-lg px-3 py-1.5 text-xs text-slate-300">
          <FolderKanban className="w-4 h-4 text-indigo-400" />
          <span className="text-slate-500 font-medium">Workspace:</span>
          <select
            value={activeWorkspaceId || ""}
            onChange={(e) => setActiveWorkspaceId(e.target.value || null)}
            className="bg-transparent text-slate-100 font-semibold focus:outline-none cursor-pointer"
          >
            <option value="" className="bg-slate-900">
              -- Select Workspace --
            </option>
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.id} className="bg-slate-900">
                {ws.name}
              </option>
            ))}
          </select>
        </div>

        {tenantDisplayName && (
          <Badge variant="purple" size="sm" className="hidden sm:inline-flex">
            <Building2 className="w-3 h-3 text-purple-400" />
            <span>{tenantDisplayName}</span>
          </Badge>
        )}
      </div>

      {/* User Actions */}
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center text-xs font-bold text-white shadow-md">
              {initials}
            </div>
            <div className="hidden md:flex flex-col text-left">
              <span className="text-xs font-semibold text-slate-200">
                {displayName}
              </span>
              <span className="text-[10px] text-indigo-400 uppercase font-medium">
                {user.role}
              </span>
            </div>
          </div>
        )}

        <button
          onClick={handleLogout}
          className="p-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-400 hover:text-rose-400 hover:border-rose-500/30 transition-colors"
          title="Sign Out"
        >
          <LogOut className="w-4 h-4" />
        </button>
      </div>
    </header>
  );
}
