"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FolderKanban,
  MessageSquareText,
  Settings,
  Sparkles,
  ChevronLeft,
  ChevronRight,
  ShieldAlert,
} from "lucide-react";
import { useUIStore } from "@/store/ui-store";
import { clsx } from "clsx";

export function AppSidebar() {
  const pathname = usePathname();
  const { sidebarCollapsed, toggleSidebar } = useUIStore();

  const navItems = [
    {
      name: "Dashboard",
      href: "/dashboard",
      icon: LayoutDashboard,
    },
    {
      name: "Workspaces & Documents",
      href: "/workspaces",
      icon: FolderKanban,
    },
    {
      name: "Grounded RAG Chat",
      href: "/chat",
      icon: MessageSquareText,
    },
    {
      name: "Settings & Tenant Admin",
      href: "/settings",
      icon: Settings,
    },
  ];

  return (
    <aside
      className={clsx(
        "glass-panel border-r border-slate-800 bg-slate-950/80 transition-all duration-300 flex flex-col justify-between z-30 relative",
        sidebarCollapsed ? "w-16" : "w-64"
      )}
    >
      <div>
        {/* Logo Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-800/80">
          <Link href="/dashboard" className="flex items-center gap-2.5 overflow-hidden">
            <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-cyan-400 p-0.5 shrink-0">
              <div className="w-full h-full bg-slate-950 rounded-[6px] flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-indigo-400" />
              </div>
            </div>
            {!sidebarCollapsed && (
              <span className="font-bold text-lg text-white font-outfit truncate">
                Context<span className="text-gradient">Hub</span>
              </span>
            )}
          </Link>

          <button
            onClick={toggleSidebar}
            className="w-7 h-7 rounded-lg bg-slate-900 border border-slate-800 hover:bg-slate-800 flex items-center justify-center text-slate-400 hover:text-white shrink-0"
          >
            {sidebarCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </button>
        </div>

        {/* Navigation list */}
        <nav className="p-2 space-y-1 mt-2">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/dashboard" && pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-3 px-3 py-2.5 rounded-lg text-xs font-medium transition-all group relative",
                  isActive
                    ? "bg-indigo-600/20 text-indigo-300 border border-indigo-500/30 font-semibold"
                    : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                )}
                title={sidebarCollapsed ? item.name : undefined}
              >
                <item.icon
                  className={clsx(
                    "w-4 h-4 shrink-0 transition-colors",
                    isActive ? "text-indigo-400" : "group-hover:text-slate-200"
                  )}
                />
                {!sidebarCollapsed && <span>{item.name}</span>}
              </Link>
            );
          })}
        </nav>
      </div>

      {/* Footer Info */}
      {!sidebarCollapsed && (
        <div className="p-4 border-t border-slate-800/80 bg-slate-900/40">
          <div className="flex items-center gap-2 text-[11px] text-slate-400">
            <ShieldAlert className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
            <span className="truncate">Multi-Tenant Protected</span>
          </div>
        </div>
      )}
    </aside>
  );
}
