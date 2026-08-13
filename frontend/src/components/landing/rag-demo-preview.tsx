"use client";

import { useState } from "react";
import { Sparkles, FileText, CheckCircle2, Copy, Search, CornerDownLeft } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export function RAGDemoPreview() {
  const [activeCitation, setActiveCitation] = useState<number | null>(null);

  const sampleCitations = [
    {
      id: 1,
      docName: "Security_Compliance_2026.pdf",
      page: 14,
      excerpt:
        "All customer data must be isolated logically using tenant_id foreign key constraints on every relational table. Access vectors are queried using pgvector HNSW indices.",
    },
    {
      id: 2,
      docName: "Architecture_Spec_v3.md",
      page: 4,
      excerpt:
        "Hybrid search combines dense vector cosine similarity with Postgres tsvector sparse full-text search. Reciprocal Rank Fusion (RRF) merges ranks with constant k=60.",
    },
  ];

  return (
    <section id="demo" className="py-20 relative">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <Badge variant="info" size="md">
            Live Preview Engine
          </Badge>
          <h2 className="text-3xl sm:text-4xl font-bold text-white mt-3 tracking-tight font-outfit">
            Grounded Answers with <span className="text-gradient">Verifiable Citations</span>
          </h2>
          <p className="text-slate-400 text-sm mt-2 max-w-2xl mx-auto">
            ContextHub forces AI models to answer strictly using your internal documents, providing clickable source page coordinates.
          </p>
        </div>

        {/* Interactive Chat Window Mockup */}
        <div className="glass-panel rounded-2xl border border-slate-700/60 shadow-2xl overflow-hidden bg-slate-950/90 max-w-4xl mx-auto">
          {/* Header Bar */}
          <div className="bg-slate-900/90 px-4 py-3 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-rose-500/80" />
              <div className="w-3 h-3 rounded-full bg-amber-500/80" />
              <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
              <span className="text-xs font-mono text-slate-400 ml-2">
                contexthub://workspace/security-policies
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Badge variant="success" size="sm">
                <CheckCircle2 className="w-3 h-3" />
                <span>RRF Reranked</span>
              </Badge>
            </div>
          </div>

          {/* Chat Timeline */}
          <div className="p-6 space-y-6">
            {/* User Message */}
            <div className="flex gap-3 justify-end">
              <div className="bg-indigo-600/90 text-white rounded-2xl rounded-tr-none px-4 py-3 text-sm max-w-lg shadow-md">
                How does ContextHub enforce multi-tenant security and hybrid search retrieval?
              </div>
            </div>

            {/* AI Streaming Response */}
            <div className="flex gap-3">
              <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shrink-0 shadow-md">
                <Sparkles className="w-4 h-4 text-white" />
              </div>
              <div className="bg-slate-900/80 border border-slate-800 rounded-2xl rounded-tl-none p-5 text-sm text-slate-200 leading-relaxed max-w-2xl space-y-3">
                <p>
                  ContextHub enforces enterprise data separation by appending a mandatory{" "}
                  <code className="bg-slate-800 text-indigo-300 px-1.5 py-0.5 rounded text-xs">
                    tenant_id
                  </code>{" "}
                  filter to all database queries. All client relational data is strictly isolated
                  at the row level.{" "}
                  <button
                    onClick={() => setActiveCitation(activeCitation === 1 ? null : 1)}
                    className="inline-flex items-center gap-1 bg-indigo-950/80 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-500/40 text-[11px] font-semibold px-2 py-0.5 rounded-full transition-all"
                  >
                    <FileText className="w-3 h-3 text-indigo-400" />
                    <span>[^1] Security_Compliance.pdf: p.14</span>
                  </button>
                </p>

                <p>
                  For content retrieval, ContextHub executes a combined search combining dense vector
                  cosine similarity (using pgvector HNSW) and sparse full-text keyword search. The
                  candidate results are re-ordered using Reciprocal Rank Fusion (RRF) before LLM synthesis.{" "}
                  <button
                    onClick={() => setActiveCitation(activeCitation === 2 ? null : 2)}
                    className="inline-flex items-center gap-1 bg-indigo-950/80 hover:bg-indigo-900/80 text-indigo-300 border border-indigo-500/40 text-[11px] font-semibold px-2 py-0.5 rounded-full transition-all"
                  >
                    <FileText className="w-3 h-3 text-indigo-400" />
                    <span>[^2] Architecture_Spec.md: p.4</span>
                  </button>
                </p>

                {/* Interactive Citation Detail Drawer */}
                {activeCitation && (
                  <div className="mt-4 pt-3 border-t border-slate-800 bg-slate-950/80 p-3.5 rounded-xl border border-indigo-500/30 animate-in fade-in slide-in-from-top-2">
                    <div className="flex items-center justify-between text-xs text-indigo-300 font-semibold mb-1">
                      <span className="flex items-center gap-1.5">
                        <FileText className="w-3.5 h-3.5" />
                        {sampleCitations[activeCitation - 1].docName} (Page{" "}
                        {sampleCitations[activeCitation - 1].page})
                      </span>
                      <span className="text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded-full border border-emerald-500/30">
                        Score: 0.96
                      </span>
                    </div>
                    <p className="text-xs text-slate-300 italic bg-slate-900/90 p-2.5 rounded-lg border border-slate-800">
                      &quot;{sampleCitations[activeCitation - 1].excerpt}&quot;
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* Fake Input Box */}
          <div className="bg-slate-900/60 p-4 border-t border-slate-800 flex items-center gap-3">
            <div className="flex-1 relative flex items-center">
              <Search className="w-4 h-4 text-slate-500 absolute left-3" />
              <input
                type="text"
                disabled
                placeholder="Ask anything about your uploaded documents..."
                className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-9 pr-4 py-2.5 text-xs text-slate-300 placeholder-slate-500 cursor-not-allowed"
              />
            </div>
            <div className="bg-indigo-600 p-2 rounded-xl text-white opacity-80">
              <CornerDownLeft className="w-4 h-4" />
            </div>
          </div>
        </div>
      </div>
    </section>
  );
}
