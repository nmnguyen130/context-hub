"use client";

import { FolderInput, ShieldLock, Search, Workflow, FileText } from "lucide-react";

export function StoryPipeline() {
  const steps = [
    {
      num: "01",
      title: "Connect",
      icon: FolderInput,
      description: "Ingest organizational documents (PDF, Markdown, text) into workspaces with modular parser workers.",
      detail: "Supports custom chunking & incremental re-indexing",
    },
    {
      num: "02",
      title: "Secure",
      icon: ShieldLock,
      description: "Enforce mandatory tenant_id context constraints and role-based access control at the database layer.",
      detail: "Row-level tenant isolation across all queries",
    },
    {
      num: "03",
      title: "Retrieve",
      icon: Search,
      description: "Perform hybrid dense-sparse search (pgvector + tsvector) combined with Reciprocal Rank Fusion (RRF).",
      detail: "Generates verifiable page & offset citations",
    },
    {
      num: "04",
      title: "Act",
      icon: Workflow,
      description: "Execute task automation through tool calling and ReAct agent workflows with human approval gates.",
      detail: "Sandboxed execution for structured workflows",
    },
    {
      num: "05",
      title: "Govern",
      icon: FileText,
      description: "Monitor access via immutable audit trails, apply DLP regex masking for PII, and control token budgets.",
      detail: "System logging of all mutating operations",
    },
  ];

  return (
    <section id="pipeline" className="py-16 border-b border-stroke bg-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between mb-10 gap-4">
          <div>
            <div className="text-[11px] font-mono text-accent uppercase tracking-wider mb-1">
              Architectural Workflow
            </div>
            <h2 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight font-heading">
              From Ingestion to Governed Execution
            </h2>
          </div>
          <p className="text-xs text-muted max-w-md">
            ContextHub structures enterprise AI knowledge into a deterministic 5-stage pipeline.
          </p>
        </div>

        {/* 5-Step Pipeline Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-3">
          {steps.map((step) => {
            const Icon = step.icon;
            return (
              <div
                key={step.num}
                className="p-4 rounded-lg bg-surface border border-stroke hover:border-stroke-strong transition-all flex flex-col justify-between"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="font-mono text-xs text-accent font-bold">
                      {step.num}
                    </span>
                    <div className="w-7 h-7 rounded bg-surface-elevated border border-stroke flex items-center justify-center text-muted">
                      <Icon className="w-3.5 h-3.5 text-accent" />
                    </div>
                  </div>

                  <h3 className="text-sm font-bold text-primary mb-1.5 font-heading">{step.title}</h3>
                  <p className="text-xs text-muted leading-relaxed">
                    {step.description}
                  </p>
                </div>

                <div className="mt-4 pt-3 border-t border-stroke/60 text-[10px] font-mono text-secondary">
                  {step.detail}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
}
