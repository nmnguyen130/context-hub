"use client";

import { Shield, Cpu, Layers, Workflow, Search, Terminal } from "lucide-react";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";

export function LandingFeatures() {
  const features = [
    {
      icon: <Layers className="w-6 h-6 text-indigo-400" />,
      title: "Logical Multi-Tenancy",
      description:
        "Guaranteed data isolation across organizations using mandatory tenant_id context constraints and indexed PostgreSQL partitioning.",
    },
    {
      icon: <Search className="w-6 h-6 text-cyan-400" />,
      title: "Hybrid RAG Engine",
      description:
        "Combines dense pgvector cosine similarity with sparse tsvector full-text search. Reciprocal Rank Fusion (RRF) delivers top context accuracy.",
    },
    {
      icon: <Cpu className="w-6 h-6 text-purple-400" />,
      title: "Cohere & Gemini Rerankers",
      description:
        "Reorders candidate search chunks dynamically to ensure LLMs receive hyper-relevant context windows without hallucination.",
    },
    {
      icon: <Shield className="w-6 h-6 text-emerald-400" />,
      title: "Verifiable Inline Citations",
      description:
        "Every generated answer includes clickable citation badges linking directly to page numbers, document names, and source excerpts.",
    },
    {
      icon: <Workflow className="w-6 h-6 text-amber-400" />,
      title: "Background Celery Worker",
      description:
        "Asynchronous document ingestion pipeline handles PDFs, Markdown, and text files using custom semantic chunkers.",
    },
    {
      icon: <Terminal className="w-6 h-6 text-rose-400" />,
      title: "Enterprise Audit Trail",
      description:
        "Tracks all mutating actions, authentication events, and document updates in immutable system audit logs.",
    },
  ];

  return (
    <section id="features" className="py-20 relative bg-slate-950/40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl sm:text-4xl font-bold text-white font-outfit tracking-tight">
            Engineered for <span className="text-gradient">Enterprise Intelligence</span>
          </h2>
          <p className="text-slate-400 text-sm mt-3 max-w-2xl mx-auto">
            Everything your team needs to retrieve, organize, and automate internal knowledge securely.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {features.map((item, idx) => (
            <Card key={idx} className="glass-card hover:translate-y-[-2px]">
              <CardHeader>
                <div className="w-12 h-12 rounded-xl bg-slate-800/80 border border-slate-700/60 flex items-center justify-center mb-4">
                  {item.icon}
                </div>
                <CardTitle className="text-base font-semibold">{item.title}</CardTitle>
                <CardDescription className="mt-2 text-xs leading-relaxed">
                  {item.description}
                </CardDescription>
              </CardHeader>
            </Card>
          ))}
        </div>
      </div>
    </section>
  );
}
