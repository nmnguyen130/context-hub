"use client";

import { ShieldCheck, KeyRound, Database, FileText } from "lucide-react";

export function SecuritySection() {
  const securityPoints = [
    {
      icon: Database,
      title: "Enforced Tenant Scoping",
      desc: "Every database query requires explicit tenant_id filters verified by context middleware and Unit of Work sessions.",
    },
    {
      icon: KeyRound,
      title: "JWT & Multi-Tenant Claims",
      desc: "Stateless HttpOnly authentication with tenant slug mapping and scoped role permissions (Admin, Member, Viewer).",
    },
    {
      icon: ShieldCheck,
      title: "Data Loss Prevention (DLP)",
      desc: "Configurable regex filters designed to sanitize credit cards, SSNs, and API keys prior to chunk embedding.",
    },
    {
      icon: FileText,
      title: "Activity & Audit Trails",
      desc: "Captures mutating operations, document lifecycle updates, and permission changes in persistent audit logs.",
    },
  ];

  return (
    <section id="security" className="py-20 border-b border-stroke bg-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 items-center">
          {/* Left Column: Context & Guarantees */}
          <div className="lg:col-span-5 space-y-4">
            <div className="text-[11px] font-mono text-accent uppercase tracking-wider">
              Security & Data Governance
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight font-heading">
              Built on Logical Multi-Tenancy Architecture
            </h2>
            <p className="text-xs text-muted leading-relaxed">
              ContextHub is designed specifically for organizations that cannot risk cross-tenant data leakage or hallucinated AI responses. All retrieval operations are strictly bounded by organizational ownership.
            </p>

            <div className="pt-2">
              <div className="p-3 rounded-lg bg-surface border border-stroke text-xs font-mono text-secondary space-y-1.5">
                <div className="text-[10px] text-accent uppercase font-bold">SQLAlchemy Context Invariant:</div>
                <code className="text-[11px] text-primary block bg-canvas p-2 rounded border border-stroke">
                  SELECT * FROM chunks WHERE tenant_id = :ctx_tenant_id
                </code>
              </div>
            </div>
          </div>

          {/* Right Column: 4 Security Cards */}
          <div className="lg:col-span-7 grid grid-cols-1 sm:grid-cols-2 gap-4">
            {securityPoints.map((pt, idx) => {
              const Icon = pt.icon;
              return (
                <div
                  key={idx}
                  className="p-4 rounded-lg bg-surface border border-stroke flex flex-col justify-between"
                >
                  <div>
                    <div className="w-7 h-7 rounded bg-surface-elevated border border-stroke flex items-center justify-center text-accent mb-3">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <h3 className="text-xs font-bold text-primary mb-1 font-heading">{pt.title}</h3>
                    <p className="text-[11px] text-muted leading-relaxed">{pt.desc}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
}
