"use client";

import { ShieldCheck, Search, FileCheck2, Cpu, Lock, Workflow } from "lucide-react";

export function LandingFeatures() {
  const capabilities = [
    {
      icon: ShieldCheck,
      title: "Logical Multi-Tenancy",
      tag: "Core Foundation",
      description:
        "Every database query and vector lookup is strictly filtered by tenant_id context, ensuring complete organizational data isolation.",
    },
    {
      icon: Search,
      title: "Hybrid Search (Dense + Sparse)",
      tag: "Retrieval Engine",
      description:
        "Merges pgvector cosine distance (semantic intent) with PostgreSQL tsvector full-text search using Reciprocal Rank Fusion (RRF).",
    },
    {
      icon: FileCheck2,
      title: "Verifiable Source Citations",
      tag: "Strict Grounding",
      description:
        "Outputs referenced source metadata with document names, page numbers, and exact matched text excerpts for transparent answers.",
    },
    {
      icon: Cpu,
      title: "Asynchronous Worker Pipelines",
      tag: "Scalable Ingestion",
      description:
        "Decoupled Celery workers process PDF, DOCX, Markdown, and text archives asynchronously using semantic paragraph splitting.",
    },
    {
      icon: Lock,
      title: "DLP & PII Pre-Ingest Scanner",
      tag: "Governance Layer",
      description:
        "Pre-ingestion scanning filters designed to detect and automatically mask sensitive credentials, SSNs, and credit cards before vector storage.",
    },
    {
      icon: Workflow,
      title: "AI Agents & Tool Execution",
      tag: "Workflow Automation",
      description:
        "Architecture supports ReAct agent loops, custom tool bindings, and human-in-the-loop approval gates for automated task workflows.",
    },
  ];

  return (
    <section id="capabilities" className="py-20 border-b border-stroke bg-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-14">
          <div className="text-[11px] font-mono text-accent uppercase tracking-wider mb-1">
            System Architecture
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight font-heading">
            Core Platform Capabilities
          </h2>
          <p className="text-xs text-muted mt-2">
            Engineered with strict tenant isolation, custom hybrid RAG algorithms, and enterprise security controls.
          </p>
        </div>

        {/* 6 Capabilities Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {capabilities.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="p-5 rounded-lg bg-surface border border-stroke hover:border-stroke-strong transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="w-8 h-8 rounded-md bg-surface-elevated border border-stroke flex items-center justify-center text-accent">
                      <Icon className="w-4 h-4" />
                    </div>
                    <span className="text-[10px] font-mono text-muted bg-surface-elevated px-2 py-0.5 rounded border border-stroke">
                      {item.tag}
                    </span>
                  </div>

                  <h3 className="text-sm font-bold text-primary mb-2 font-heading">{item.title}</h3>
                  <p className="text-xs text-muted leading-relaxed">
                    {item.description}
                  </p>
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
