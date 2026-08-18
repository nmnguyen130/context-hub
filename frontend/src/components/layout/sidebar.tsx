"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  MessageSquareText,
  Settings,
  Terminal,
  ChevronLeft,
  ChevronRight,
  Shield,
  KeyRound,
  FileText,
} from "lucide-react";
import { useUIStore } from "@/store/ui-store";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { clsx } from "clsx";

export function AppSidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();
  const { data: user } = useCurrentUser();

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";

  const userNavItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Workspaces & Ingest",
      href: "/workspaces",
      icon: FolderKanban,
    },
    {
      name: "Grounded RAG Chat",
      href: "/chat",
      icon: MessageSquareText,
    },
  ];

  const adminNavItems = [
    {
      name: "Tenant Governance",
      href: "/settings/general",
      icon: Settings,
    },
    {
      name: "Connectors & Sync",
      href: "/settings/connectors",
      icon: KeyRound,
    },
    {
      name: "Audit Explorer",
      href: "/settings/audit",
      icon: FileText,
    },
  ];

  return (
    <aside
      className={clsx(
        "bg-surface border-r border-stroke transition-all duration-200 flex flex-col justify-between z-30 relative shrink-0",
        sidebarCollapsed ? "w-16" : "w-60"
      )}
    >
      <div>
        {/* Logo Header */}
        <div className="h-14 px-3.5 flex items-center justify-between border-b border-stroke">
          <Link href="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-7 h-7 rounded-md bg-surface-dark border border-stroke flex items-center justify-center text-accent shrink-0">
              <Terminal className="w-3.5 h-3.5" />
            </div>
            {!sidebarCollapsed && (
              <span className="font-bold text-sm text-primary tracking-tight truncate font-heading">
                Context<span className="text-accent">Hub</span>
              </span>
            )}
          </Link>

          <button
            onClick={toggleSidebar}
            className="w-6 h-6 rounded bg-surface-elevated border border-stroke hover:bg-surface-hover flex items-center justify-center text-muted hover:text-primary shrink-0 transition-colors cursor-pointer"
            aria-label="Toggle Sidebar"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-3.5 h-3.5" />
            ) : (
              <ChevronLeft className="w-3.5 h-3.5" />
            )}
          </button>
        </div>

        {/* User Workspace Section */}
        <nav className="p-2 space-y-1">
          {!sidebarCollapsed && (
            <div className="px-2.5 pt-2 pb-1 text-[10px] font-mono text-muted uppercase tracking-wider">
              Workspace
            </div>
          )}
          {userNavItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-all group relative",
                  isActive
                    ? "bg-surface-elevated text-accent border border-stroke font-semibold"
                    : "text-muted hover:bg-surface-elevated/60 hover:text-primary"
                )}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon
                  className={clsx(
                    "w-4 h-4 shrink-0 transition-colors",
                    isActive ? "text-accent" : "group-hover:text-primary"
                  )}
                />
                {!sidebarCollapsed && <span className="truncate">{item.name}</span>}
              </Link>
            );
          })}

          {/* Admin Governance Section */}
          {isAdmin && (
            <>
              {!sidebarCollapsed && (
                <div className="px-2.5 pt-4 pb-1 text-[10px] font-mono text-muted uppercase tracking-wider">
                  Admin & Security
                </div>
              )}
              {adminNavItems.map((item) => {
                const isActive = pathname.startsWith(item.href.split("/")[1] + "/" + item.href.split("/")[2]);

                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={clsx(
                      "flex items-center gap-2.5 px-2.5 py-2 rounded-md text-xs font-medium transition-all group relative",
                      isActive
                        ? "bg-surface-elevated text-accent border border-stroke font-semibold"
                        : "text-muted hover:bg-surface-elevated/60 hover:text-primary"
                    )}
                    title={sidebarCollapsed ? item.name : undefined}
                  >
                    <item.icon
                      className={clsx(
                        "w-4 h-4 shrink-0 transition-colors",
                        isActive ? "text-accent" : "group-hover:text-primary"
                      )}
                    />
                    {!sidebarCollapsed && <span className="truncate">{item.name}</span>}
                  </Link>
                );
              })}
            </>
          )}
        </nav>
      </div>

      {/* Footer Info */}
      {!sidebarCollapsed && (
        <div className="p-3 border-t border-stroke bg-surface-dark">
          <div className="flex items-center gap-2 text-[10px] font-mono text-muted">
            <Shield className="w-3.5 h-3.5 text-success shrink-0" />
            <span className="truncate">TENANT ISOLATED</span>
          </div>
        </div>
      )}
    </aside>
  );
}
