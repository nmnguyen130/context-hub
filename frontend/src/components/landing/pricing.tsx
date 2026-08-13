"use client";

import Link from "next/link";
import { Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export function LandingPricing() {
  const tiers = [
    {
      name: "Starter",
      badge: "Free Developer Tier",
      price: "$0",
      period: "forever",
      description: "For individual teams testing internal document retrieval.",
      features: [
        "Up to 20 Users",
        "10 GB Ingestion Storage",
        "Logical Multi-Tenant Isolation",
        "Hybrid RAG + Citations",
        "Standard PDF/Markdown Parsers",
      ],
      buttonText: "Start Free",
      buttonVariant: "outline" as const,
      popular: false,
    },
    {
      name: "Professional",
      badge: "Most Popular",
      price: "$49",
      period: "per month",
      description: "For growing organizations requiring scaling RAG search & custom connectors.",
      features: [
        "Unlimited Users",
        "500 GB Ingestion Storage",
        "Cohere Rerank API Integration",
        "Redis Sliding-Window Rate Limiting",
        "Workspace RBAC Permissions",
        "Priority Support",
      ],
      buttonText: "Get Pro Plan",
      buttonVariant: "primary" as const,
      popular: true,
    },
    {
      name: "Enterprise",
      badge: "VPC & Hybrid",
      price: "Custom",
      period: "annual billing",
      description: "Dedicated single-tenant DB, custom SAML/SSO federation, and DLP scanner.",
      features: [
        "Dedicated VPC / On-Prem Deployment",
        "Unlimited Ingest Storage",
        "SAML 2.0 / Okta SSO Integration",
        "Pre-ingest DLP (PII Redaction)",
        "Immutable Audit Logs CSV Export",
        "Dedicated Solutions Architect",
      ],
      buttonText: "Contact Sales",
      buttonVariant: "secondary" as const,
      popular: false,
    },
  ];

  return (
    <section id="pricing" className="py-20 relative">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <Badge variant="purple" size="md">
            Flexible Scaling
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold text-white font-outfit tracking-tight mt-3">
            Transparent Packaging for <span className="text-gradient">Every Team Size</span>
          </h2>
          <p className="text-slate-400 text-sm mt-2 max-w-xl mx-auto">
            Choose the plan that fits your institutional data ingestion needs.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-stretch">
          {tiers.map((tier, idx) => (
            <Card
              key={idx}
              className={`glass-card flex flex-col justify-between relative ${
                tier.popular
                  ? "border-indigo-500/60 shadow-2xl shadow-indigo-500/10 ring-1 ring-indigo-500/50"
                  : ""
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white text-[10px] font-bold uppercase tracking-wider px-3 py-0.5 rounded-full shadow-md">
                  Most Popular
                </div>
              )}

              <div>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-xl font-bold">{tier.name}</CardTitle>
                    <Badge variant={tier.popular ? "info" : "neutral"}>
                      {tier.badge}
                    </Badge>
                  </div>
                  <CardDescription className="mt-2 text-xs">
                    {tier.description}
                  </CardDescription>

                  <div className="mt-6 flex items-baseline gap-1">
                    <span className="text-4xl font-extrabold text-white font-outfit">
                      {tier.price}
                    </span>
                    <span className="text-slate-400 text-xs font-normal">
                      /{tier.period}
                    </span>
                  </div>
                </CardHeader>

                <div className="px-5 py-4 space-y-3">
                  <p className="text-xs font-semibold text-slate-300 uppercase tracking-wider">
                    Included Features:
                  </p>
                  {tier.features.map((feature, fIdx) => (
                    <div key={fIdx} className="flex items-center gap-2.5 text-xs text-slate-300">
                      <div className="w-4 h-4 rounded-full bg-emerald-950 border border-emerald-500/40 flex items-center justify-center shrink-0">
                        <Check className="w-2.5 h-2.5 text-emerald-400" />
                      </div>
                      <span>{feature}</span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="p-5 pt-0 mt-6">
                <Link href="/register">
                  <Button variant={tier.buttonVariant} className="w-full">
                    {tier.buttonText}
                  </Button>
                </Link>
              </div>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
