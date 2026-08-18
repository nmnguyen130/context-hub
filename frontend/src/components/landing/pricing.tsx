"use client";

import Link from "next/link";
import { Check } from "lucide-react";

export function LandingPricing() {
  const tiers = [
    {
      name: "Developer",
      tag: "Free Tier",
      price: "$0",
      description: "For individual teams testing internal document retrieval and RAG search.",
      features: [
        "Up to 5 Workspaces",
        "Standard PDF, DOCX & Markdown parsing",
        "pgvector HNSW cosine similarity",
        "Deterministic inline citations",
        "Logical multi-tenant isolation",
      ],
      ctaText: "Deploy Free Workspace",
      ctaHref: "/register",
      featured: false,
    },
    {
      name: "Team",
      tag: "Most Popular",
      price: "$49",
      period: "/ month",
      description: "For engineering & ops teams scaling knowledge search and ingestion.",
      features: [
        "Unlimited Workspaces & Collections",
        "Multi-User Directory & RBAC Roles",
        "Hybrid Search (Dense pgvector + Sparse tsvector)",
        "Reciprocal Rank Fusion (RRF) reranking",
        "Asynchronous Celery ingestion pipeline",
        "Activity & audit logging",
      ],
      ctaText: "Start Team Workspace",
      ctaHref: "/register",
      featured: true,
    },
    {
      name: "Enterprise",
      tag: "Dedicated / VPC",
      price: "Custom",
      description: "For enterprises requiring dedicated isolation, SSO federation, and custom SLAs.",
      features: [
        "Dedicated Single-Tenant Database or VPC",
        "SAML 2.0 / OIDC SSO Integration",
        "Configurable DLP & PII regex sanitization",
        "Immutable audit log export (CSV / SIEM)",
        "Custom LLM API key & model routing policies",
        "Dedicated SLA & technical support",
      ],
      ctaText: "Contact Sales",
      ctaHref: "mailto:sales@contexthub.internal",
      featured: false,
    },
  ];

  return (
    <section id="pricing" className="py-20 border-b border-stroke bg-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="text-[11px] font-mono text-accent uppercase tracking-wider mb-1">
            Packaging & Deployment
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight font-heading">
            Predictable Plans for Every Stage
          </h2>
          <p className="text-xs text-muted mt-2">
            Start free on logical multi-tenancy, or deploy dedicated VPC infrastructure as your organization grows.
          </p>
        </div>

        {/* 3 Pricing Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 max-w-5xl mx-auto items-stretch">
          {tiers.map((tier, idx) => (
            <div
              key={idx}
              className={`p-6 rounded-xl flex flex-col justify-between transition-all ${
                tier.featured
                  ? "bg-surface border-2 border-accent shadow-lg relative"
                  : "bg-surface border border-stroke hover:border-stroke-strong"
              }`}
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-base font-bold text-primary font-heading">{tier.name}</h3>
                  <span
                    className={`text-[10px] font-mono px-2 py-0.5 rounded border ${
                      tier.featured
                        ? "bg-accent/10 text-accent border-accent/30 font-semibold"
                        : "bg-surface-elevated text-muted border-stroke"
                    }`}
                  >
                    {tier.tag}
                  </span>
                </div>

                <p className="text-xs text-muted min-h-[32px]">{tier.description}</p>

                <div className="mt-5 mb-6 flex items-baseline gap-1">
                  <span className="text-3xl font-extrabold text-primary font-heading">
                    {tier.price}
                  </span>
                  {tier.period && (
                    <span className="text-xs text-muted">{tier.period}</span>
                  )}
                </div>

                <div className="space-y-2.5 border-t border-stroke pt-4 text-xs">
                  <div className="text-[10px] font-mono text-muted uppercase mb-2">Features Included:</div>
                  {tier.features.map((f, fIdx) => (
                    <div key={fIdx} className="flex items-start gap-2 text-secondary">
                      <Check className="w-3.5 h-3.5 text-accent shrink-0 mt-0.5" />
                      <span className="leading-tight">{f}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="mt-8 pt-4 border-t border-stroke">
                <Link
                  href={tier.ctaHref}
                  className={`w-full block text-center text-xs font-semibold py-2.5 rounded-md transition-colors cursor-pointer ${
                    tier.featured
                      ? "bg-accent hover:bg-accent-hover text-white shadow-sm"
                      : "bg-surface-elevated hover:bg-surface-hover text-primary border border-stroke"
                  }`}
                >
                  {tier.ctaText}
                </Link>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
