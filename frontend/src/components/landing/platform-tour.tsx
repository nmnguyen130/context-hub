"use client";

import { useState } from "react";
import {
  FileText,
  ShieldCheck,
  CheckCircle2,
  Workflow,
  ShieldAlert,
  Search,
  Sparkles,
  Lock,
} from "lucide-react";

export function PlatformTour() {
  const [activeTab, setActiveTab] = useState<"rag" | "agent" | "dlp">("rag");
  const [agentApproved, setAgentApproved] = useState(false);

  return (
    <section id="tour" className="py-20 border-b border-stroke bg-canvas">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="text-[11px] font-mono text-accent uppercase tracking-wider mb-1">
            Platform Capabilities Preview
          </div>
          <h2 className="text-2xl sm:text-3xl font-bold text-primary tracking-tight font-heading">
            Interactive System Preview
          </h2>
          <p className="text-xs text-muted mt-2">
            Explore realistic product workflows for grounded retrieval, autonomous task execution, and pre-ingestion governance.
          </p>
        </div>

        {/* 3-Tab Switcher */}
        <div className="flex justify-center mb-6">
          <div className="inline-flex p-1 rounded-lg bg-surface border border-stroke">
            <button
              onClick={() => setActiveTab("rag")}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeTab === "rag"
                  ? "bg-surface-elevated text-accent border border-stroke shadow-xs"
                  : "text-muted hover:text-primary"
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Permission-Aware RAG & Citations</span>
            </button>

            <button
              onClick={() => setActiveTab("agent")}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeTab === "agent"
                  ? "bg-surface-elevated text-accent border border-stroke shadow-xs"
                  : "text-muted hover:text-primary"
              }`}
            >
              <Workflow className="w-3.5 h-3.5" />
              <span>AI Agent & Tool Calling</span>
            </button>

            <button
              onClick={() => setActiveTab("dlp")}
              className={`flex items-center gap-2 px-4 py-2 rounded-md text-xs font-medium transition-all cursor-pointer ${
                activeTab === "dlp"
                  ? "bg-surface-elevated text-accent border border-stroke shadow-xs"
                  : "text-muted hover:text-primary"
              }`}
            >
              <ShieldAlert className="w-3.5 h-3.5" />
              <span>DLP & PII Redaction Filter</span>
            </button>
          </div>
        </div>

        {/* Realistic Product UI Container */}
        <div className="max-w-5xl mx-auto rounded-xl bg-surface border border-stroke overflow-hidden shadow-2xl">
          {/* Top Bar simulating system window */}
          <div className="h-10 bg-surface-dark border-b border-stroke px-4 flex items-center justify-between text-xs font-mono text-muted">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-stroke"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-stroke"></span>
              <span className="w-2.5 h-2.5 rounded-full bg-stroke"></span>
              <span className="ml-2 text-[11px] text-secondary">ContextHub Enterprise UI — Active Scope: Tenant ID [a9f8-411e]</span>
            </div>
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
              <span>UoW Tenant Isolation: Enforced</span>
            </div>
          </div>

          {/* Mode 1: RAG & Citations */}
          {activeTab === "rag" && (
            <div className="p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
              {/* Left Column: Chat Conversation */}
              <div className="lg:col-span-7 space-y-4">
                {/* User Query */}
                <div className="p-3.5 rounded-lg bg-surface-elevated border border-stroke text-xs">
                  <div className="text-[10px] font-mono text-muted mb-1 uppercase">User Query · Workspace: Engineering</div>
                  <p className="text-primary">
                    What are the mandatory logical multi-tenancy rules required for database queries in our backend?
                  </p>
                </div>

                {/* Grounded Assistant Answer */}
                <div className="p-4 rounded-lg bg-surface-dark border border-stroke text-xs space-y-3">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-1.5 text-accent font-semibold text-[11px]">
                      <Sparkles className="w-3.5 h-3.5" />
                      <span>ContextHub Grounded Retrieval</span>
                    </div>
                    <span className="text-[10px] font-mono text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">
                      Zero Hallucination Grounding
                    </span>
                  </div>

                  <p className="text-primary leading-relaxed">
                    According to the architecture standards, all database models except global tables must include a <code className="bg-surface-elevated text-accent px-1 py-0.5 rounded font-mono">tenant_id: UUID</code> column with an index. Every SELECT, UPDATE, and DELETE query must explicitly filter by this tenant ID context <span className="inline-flex items-center gap-1 bg-surface-elevated border border-accent/40 text-accent font-mono text-[10px] px-1.5 py-0.2 rounded font-semibold cursor-pointer">[^1]</span>. Context is extracted from JWT claims and injected into thread-safe context variables during request execution <span className="inline-flex items-center gap-1 bg-surface-elevated border border-accent/40 text-accent font-mono text-[10px] px-1.5 py-0.2 rounded font-semibold cursor-pointer">[^2]</span>.
                  </p>
                </div>
              </div>

              {/* Right Column: Source Citation Inspector */}
              <div className="lg:col-span-5 p-4 rounded-lg bg-surface-dark border border-stroke text-xs space-y-3">
                <div className="flex items-center justify-between border-b border-stroke pb-2">
                  <div className="flex items-center gap-1.5 text-primary font-semibold">
                    <FileText className="w-3.5 h-3.5 text-accent" />
                    <span>Citation [^1] Inspector</span>
                  </div>
                  <span className="font-mono text-[10px] text-success">Score: 0.94 (RRF)</span>
                </div>

                <div className="space-y-2 text-[11px]">
                  <div className="flex justify-between">
                    <span className="text-muted">Source Document:</span>
                    <span className="text-primary font-mono">GEMINI.md</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Section / Heading:</span>
                    <span className="text-primary">§2. Logical Multi-Tenancy</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-muted">Access Control Check:</span>
                    <span className="text-success flex items-center gap-1">
                      <ShieldCheck className="w-3 h-3" /> Tenant Validated
                    </span>
                  </div>
                </div>

                <div className="pt-2 border-t border-stroke">
                  <span className="text-[10px] font-mono text-muted uppercase">Exact Matched Text Chunk:</span>
                  <div className="mt-1 p-2.5 rounded bg-surface border border-stroke text-secondary font-mono text-[11px] leading-relaxed">
                    &quot;Every relational table (except global settings) must contain a tenant_id: UUID column and an index on (tenant_id). All queries must explicitly filter by tenant_id.&quot;
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Mode 2: AI Agents & Tools */}
          {activeTab === "agent" && (
            <div className="p-6 space-y-4">
              <div className="flex items-center justify-between border-b border-stroke pb-3">
                <div className="flex items-center gap-2">
                  <Workflow className="w-4 h-4 text-accent" />
                  <span className="font-semibold text-xs text-primary">ReAct Agent Task Execution Plan</span>
                </div>
                <span className="text-[10px] font-mono text-warning bg-warning/10 border border-warning/20 px-2 py-0.5 rounded">
                  Human Approval Gate Configured
                </span>
              </div>

              {/* Step Timeline */}
              <div className="space-y-2.5 text-xs font-mono">
                {/* Step 1 */}
                <div className="p-3 rounded bg-surface-dark border border-stroke flex items-start gap-3">
                  <span className="text-success mt-0.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </span>
                  <div className="space-y-0.5">
                    <span className="text-muted">STEP 1 · Tool: search_workspace_documents</span>
                    <p className="text-primary font-sans">
                      Executed vector search for &quot;Q3 onboarding guidelines&quot; in Workspace &apos;HR&apos;. Found 2 relevant sections.
                    </p>
                  </div>
                </div>

                {/* Step 2 */}
                <div className="p-3 rounded bg-surface-dark border border-stroke flex items-start gap-3">
                  <span className="text-success mt-0.5">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                  </span>
                  <div className="space-y-0.5">
                    <span className="text-muted">STEP 2 · Tool: generate_structured_checklist</span>
                    <p className="text-primary font-sans">
                      Extracted 5 required onboarding steps for new engineering employees with citation references.
                    </p>
                  </div>
                </div>

                {/* Step 3: Approval Gate */}
                <div className="p-3 rounded bg-surface-elevated border border-accent/40 flex items-start justify-between gap-3">
                  <div className="space-y-1">
                    <div className="flex items-center gap-1.5 text-accent font-bold">
                      <Lock className="w-3.5 h-3.5" />
                      <span>STEP 3 · Awaiting Human Approval before publish_to_workspace()</span>
                    </div>
                    <p className="text-primary font-sans text-xs">
                      The agent generated a new document &apos;Engineering_Onboarding_Checklist_Q3.md&apos;. Do you approve saving to the shared collection?
                    </p>
                  </div>

                  <button
                    onClick={() => setAgentApproved(!agentApproved)}
                    className={`px-3 py-1.5 rounded text-xs font-semibold font-sans transition-colors shrink-0 cursor-pointer ${
                      agentApproved
                        ? "bg-success text-black"
                        : "bg-accent hover:bg-accent-hover text-white"
                    }`}
                  >
                    {agentApproved ? "✓ Approved & Executed" : "Confirm Action"}
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Mode 3: DLP & Governance */}
          {activeTab === "dlp" && (
            <div className="p-6 grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Ingest Payload Before DLP */}
              <div className="p-4 rounded-lg bg-surface-dark border border-stroke text-xs space-y-2">
                <div className="flex items-center justify-between border-b border-stroke pb-2">
                  <span className="text-muted font-mono">Raw Ingestion Stream (Before DLP)</span>
                  <span className="text-[10px] text-danger font-mono bg-danger/10 border border-danger/20 px-2 py-0.5 rounded">
                    PII Detected
                  </span>
                </div>
                <div className="p-3 rounded bg-surface border border-stroke font-mono text-[11px] text-secondary space-y-1">
                  <p>Customer Name: Jane Doe</p>
                  <p className="text-danger bg-danger/10 px-1 rounded">SSN: 452-98-1044</p>
                  <p className="text-danger bg-danger/10 px-1 rounded">Card: 4111-2222-3333-4444</p>
                  <p>Account Type: Enterprise Tenant</p>
                </div>
              </div>

              {/* Ingest Payload After DLP Sanitization */}
              <div className="p-4 rounded-lg bg-surface-dark border border-stroke text-xs space-y-2">
                <div className="flex items-center justify-between border-b border-stroke pb-2">
                  <span className="text-muted font-mono">Sanitized Chunk Injected to pgvector</span>
                  <span className="text-[10px] text-success font-mono bg-success/10 border border-success/20 px-2 py-0.5 rounded">
                    Redaction Applied
                  </span>
                </div>
                <div className="p-3 rounded bg-surface border border-stroke font-mono text-[11px] text-primary space-y-1">
                  <p>Customer Name: Jane Doe</p>
                  <p className="text-success bg-success/10 px-1 rounded font-bold">[REDACTED PII: SSN]</p>
                  <p className="text-success bg-success/10 px-1 rounded font-bold">[REDACTED PII: CREDIT_CARD]</p>
                  <p>Account Type: Enterprise Tenant</p>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
