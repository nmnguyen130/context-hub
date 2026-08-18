"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  FolderKanban,
  MessageSquareText,
  KeyRound,
  Shield,
  Users,
} from "lucide-react";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";

export function CommandPalette({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const { data: workspacesData } = useWorkspaces();
  const { data: user } = useCurrentUser();

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";
  const workspaces = workspacesData?.items || [];

  // Close on Escape
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    if (open) window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [open, onClose]);

  if (!open) return null;

  const navigateTo = (path: string) => {
    onClose();
    router.push(path);
  };

  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(query.toLowerCase())
  );

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-24 bg-black/75 backdrop-blur-xs p-4">
      <div
        className="w-full max-w-xl bg-surface border border-stroke rounded-xl shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-100"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search input header */}
        <div className="flex items-center gap-3 px-4 py-3 border-b border-stroke bg-surface-dark">
          <Search className="w-4 h-4 text-muted" />
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search workspaces, documents, or jump to..."
            autoFocus
            className="flex-1 bg-transparent text-xs text-primary placeholder:text-muted focus:outline-none"
          />
          <kbd className="px-1.5 py-0.5 rounded border border-stroke bg-surface text-[10px] font-mono text-muted">
            ESC
          </kbd>
        </div>

        <div className="p-2 max-h-80 overflow-y-auto space-y-3 text-xs">
          {/* Quick Navigation */}
          <div>
            <div className="px-2 py-1 text-[10px] font-mono text-muted uppercase tracking-wider">
              Quick Navigation
            </div>
            <div className="space-y-0.5">
              <button
                onClick={() => navigateTo("/dashboard")}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
              >
                <LayoutDashboard className="w-4 h-4 text-muted" />
                <span>Dashboard Overview</span>
              </button>
              <button
                onClick={() => navigateTo("/workspaces")}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
              >
                <FolderKanban className="w-4 h-4 text-muted" />
                <span>Workspaces & Ingestion</span>
              </button>
              <button
                onClick={() => navigateTo("/chat")}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
              >
                <MessageSquareText className="w-4 h-4 text-muted" />
                <span>Grounded RAG Chat</span>
              </button>
            </div>
          </div>

          {/* Workspaces List */}
          {filteredWorkspaces.length > 0 && (
            <div>
              <div className="px-2 py-1 text-[10px] font-mono text-muted uppercase tracking-wider">
                Workspaces
              </div>
              <div className="space-y-0.5">
                {filteredWorkspaces.map((ws) => (
                  <button
                    key={ws.id}
                    onClick={() => navigateTo(`/workspaces/${ws.id}`)}
                    className="w-full flex items-center justify-between px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
                  >
                    <div className="flex items-center gap-2.5 truncate">
                      <FolderKanban className="w-3.5 h-3.5 text-accent" />
                      <span className="truncate">{ws.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-muted">Console</span>
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Admin Shortcuts */}
          {isAdmin && (
            <div>
              <div className="px-2 py-1 text-[10px] font-mono text-muted uppercase tracking-wider">
                Admin Governance
              </div>
              <div className="space-y-0.5">
                <button
                  onClick={() => navigateTo("/settings/members")}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
                >
                  <Users className="w-4 h-4 text-muted" />
                  <span>Team Directory & RBAC Roles</span>
                </button>
                <button
                  onClick={() => navigateTo("/settings/connectors")}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
                >
                  <KeyRound className="w-4 h-4 text-muted" />
                  <span>Enterprise Connectors & Sync Health</span>
                </button>
                <button
                  onClick={() => navigateTo("/settings/audit")}
                  className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-md text-primary hover:bg-surface-elevated hover:text-accent transition-colors text-left cursor-pointer"
                >
                  <Shield className="w-4 h-4 text-muted" />
                  <span>Immutable Audit Explorer</span>
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="px-4 py-2 border-t border-stroke bg-surface-dark flex items-center justify-between text-[10px] text-muted font-mono">
          <span>Navigate with mouse or keyboard</span>
          <span>ContextHub Command Palette</span>
        </div>
      </div>
    </div>
  );
}
