"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Settings,
  Users,
  Shield,
  KeyRound,
  FileText,
  CreditCard,
  Building2,
  Lock,
} from "lucide-react";
import { useCurrentUser } from "@/features/auth/hooks/use-current-user";
import { clsx } from "clsx";

export default function SettingsLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { data: user, isLoading } = useCurrentUser();

  const isAdmin = user?.role === "ADMIN" || user?.role === "OWNER";

  const navItems = [
    { name: "General & Profile", href: "/settings/general", icon: Settings },
    { name: "Team & RBAC Roles", href: "/settings/members", icon: Users },
    { name: "DLP & Data Security", href: "/settings/security", icon: Shield },
    { name: "Enterprise SSO (SAML)", href: "/settings/sso", icon: KeyRound },
    { name: "Connectors & Sync", href: "/settings/connectors", icon: Building2 },
    { name: "Audit Explorer", href: "/settings/audit", icon: FileText },
    { name: "Plan & Billing", href: "/settings/billing", icon: CreditCard },
  ];

  if (!isLoading && !isAdmin) {
    return (
      <div className="p-12 rounded-lg bg-surface border border-stroke text-center max-w-lg mx-auto my-12 space-y-3">
        <Lock className="w-8 h-8 text-warning mx-auto" />
        <h2 className="text-base font-bold text-primary font-heading">Administrator Access Required</h2>
        <p className="text-xs text-muted leading-relaxed">
          Tenant governance, team member invitations, security DLP policies, and audit logs are restricted to Tenant Owners and Admins.
        </p>
        <Link
          href="/dashboard"
          className="inline-block mt-3 text-xs text-accent hover:underline font-semibold"
        >
          ← Return to Dashboard
        </Link>
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto space-y-6">
      {/* Header */}
      <div className="pb-4 border-b border-stroke">
        <h1 className="text-xl sm:text-2xl font-bold text-primary font-heading">
          Tenant Governance & Security Console
        </h1>
        <p className="text-xs text-muted mt-0.5">
          Configure organizational multi-tenancy policies, member roles, enterprise connectors, and audit compliance.
        </p>
      </div>

      {/* Grid: Left Sub-Navigation + Right Content */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Settings Sub-Nav (3 cols) */}
        <div className="lg:col-span-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={clsx(
                  "flex items-center gap-2.5 px-3 py-2.5 rounded-md text-xs font-medium transition-colors",
                  isActive
                    ? "bg-surface-elevated text-accent border border-stroke font-semibold"
                    : "text-muted hover:bg-surface-elevated/60 hover:text-primary"
                )}
              >
                <item.icon className="w-4 h-4 shrink-0" />
                <span>{item.name}</span>
              </Link>
            );
          })}
        </div>

        {/* Right Tab Content Panel (9 cols) */}
        <div className="lg:col-span-9 bg-surface border border-stroke rounded-xl p-6">
          {children}
        </div>
      </div>
    </div>
  );
}
