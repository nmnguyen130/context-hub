"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { useQueryClient } from "@tanstack/react-query";
import {
  FolderKanban,
  LogOut,
  Building2,
  Search,
  Bell,
  CheckCircle2,
} from "lucide-react";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { useCurrentTenant } from "@/features/tenant/hooks/use-tenant";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { authApi } from "@/lib/api/auth";
import { CommandPalette } from "@/components/command-palette";
import { toast } from "sonner";

export function AppHeader() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const [commandPaletteOpen, setCommandPaletteOpen] = useState(false);
  const [notificationsOpen, setNotificationsOpen] = useState(false);

  const { data: user } = useCurrentUser();
  const { tenantDisplayName, clearTenantSlug } = useCurrentTenant();
  const { data: workspacesData } = useWorkspaces();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceStore();

  const workspaces = workspacesData?.items || [];

  // Automatically select first workspace if none active
  useEffect(() => {
    if (!activeWorkspaceId && workspaces.length > 0) {
      setActiveWorkspaceId(workspaces[0].id);
    }
  }, [activeWorkspaceId, workspaces, setActiveWorkspaceId]);

  // Global ⌘K shortcut listener
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setCommandPaletteOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

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

  const displayName = user?.display_name || user?.email.split("@")[0] || "User";
  const initials = user?.display_name
    ? user.display_name
        .split(" ")
        .map((n) => n[0])
        .join("")
        .toUpperCase()
        .slice(0, 2)
    : user?.email?.[0]?.toUpperCase() || "U";

  // Mock operational notifications
  const notifications = [
    {
      id: "1",
      title: "Ingestion Pipeline Status",
      message: "Workspace 'Engineering Specs' finished indexing 4 documents.",
      time: "10m ago",
    },
    {
      id: "2",
      title: "Security DLP Invariant",
      message: "Pre-ingestion regex filter active. Zero secrets detected.",
      time: "1h ago",
    },
  ];

  return (
    <>
      <header className="h-14 border-b border-stroke bg-surface px-4 flex items-center justify-between z-20">
        {/* Left: Workspace Selector & ⌘K Search */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 bg-surface-elevated border border-stroke rounded-md px-2.5 py-1 text-xs text-secondary">
            <FolderKanban className="w-3.5 h-3.5 text-accent" />
            <span className="text-muted font-medium hidden sm:inline">Workspace:</span>
            <select
              value={activeWorkspaceId || ""}
              onChange={(e) => setActiveWorkspaceId(e.target.value || null)}
              className="bg-transparent text-primary font-semibold focus:outline-none cursor-pointer text-xs"
            >
              {workspaces.length === 0 ? (
                <option value="" className="bg-surface">
                  No Workspaces
                </option>
              ) : (
                workspaces.map((ws) => (
                  <option key={ws.id} value={ws.id} className="bg-surface">
                    {ws.name}
                  </option>
                ))
              )}
            </select>
          </div>

          {/* Quick ⌘K Search Button */}
          <button
            onClick={() => setCommandPaletteOpen(true)}
            className="hidden md:flex items-center gap-2 px-2.5 py-1 rounded-md bg-surface-elevated border border-stroke text-xs text-muted hover:text-primary transition-colors cursor-pointer"
          >
            <Search className="w-3.5 h-3.5" />
            <span>Search or jump to...</span>
            <kbd className="px-1.5 py-0.2 rounded border border-stroke bg-surface text-[10px] font-mono">
              ⌘K
            </kbd>
          </button>
        </div>

        {/* Right: Tenant Badge, Notifications, User Profile & Logout */}
        <div className="flex items-center gap-3">
          {tenantDisplayName && (
            <div className="hidden lg:flex items-center gap-1.5 px-2 py-0.5 rounded bg-surface-elevated border border-stroke text-[10px] font-mono text-secondary">
              <Building2 className="w-3 h-3 text-accent" />
              <span>{tenantDisplayName}</span>
            </div>
          )}

          {/* Notification Center Bell */}
          <div className="relative">
            <button
              onClick={() => setNotificationsOpen(!notificationsOpen)}
              className="p-1.5 rounded-md bg-surface-elevated border border-stroke text-muted hover:text-primary transition-colors relative cursor-pointer"
              title="Notifications"
            >
              <Bell className="w-3.5 h-3.5" />
              <span className="absolute -top-0.5 -right-0.5 w-2 h-2 rounded-full bg-accent"></span>
            </button>

            {notificationsOpen && (
              <div className="absolute right-0 mt-2 w-80 bg-surface border border-stroke rounded-xl shadow-2xl p-3 space-y-2 z-50 text-xs">
                <div className="flex items-center justify-between border-b border-stroke pb-2">
                  <span className="font-bold text-primary text-xs font-heading">System Activity</span>
                  <button
                    onClick={() => setNotificationsOpen(false)}
                    className="text-muted hover:text-primary text-[11px] cursor-pointer"
                  >
                    Close
                  </button>
                </div>
                <div className="space-y-1.5">
                  {notifications.map((n) => (
                    <div key={n.id} className="p-2 rounded-md bg-surface-elevated border border-stroke space-y-0.5">
                      <div className="flex items-center justify-between text-[11px] font-semibold text-primary">
                        <div className="flex items-center gap-1">
                          <CheckCircle2 className="w-3 h-3 text-success" />
                          <span>{n.title}</span>
                        </div>
                        <span className="text-[10px] text-muted font-mono">{n.time}</span>
                      </div>
                      <p className="text-[11px] text-muted leading-relaxed">{n.message}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* User Profile */}
          {user && (
            <div className="flex items-center gap-2">
              <div className="w-7 h-7 rounded-md bg-accent/20 border border-accent/40 flex items-center justify-center text-xs font-bold text-accent">
                {initials}
              </div>
              <div className="hidden md:flex flex-col text-left">
                <span className="text-xs font-semibold text-primary truncate max-w-[120px]">
                  {displayName}
                </span>
                <span className="text-[9px] text-accent uppercase font-mono tracking-wider">
                  {user.role}
                </span>
              </div>
            </div>
          )}

          {/* Logout Button */}
          <button
            onClick={handleLogout}
            className="p-1.5 rounded-md bg-surface-elevated border border-stroke text-muted hover:text-danger hover:border-danger/30 transition-colors cursor-pointer"
            title="Sign Out"
          >
            <LogOut className="w-3.5 h-3.5" />
          </button>
        </div>
      </header>

      {/* Command Palette Modal */}
      <CommandPalette
        open={commandPaletteOpen}
        onClose={() => setCommandPaletteOpen(false)}
      />
    </>
  );
}
