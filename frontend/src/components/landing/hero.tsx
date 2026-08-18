"use client";

import Link from "next/link";
import { ArrowRight, Terminal, Shield, Database, FileCheck2, Cpu } from "lucide-react";

export function LandingHero() {
  return (
    <section className="relative pt-20 pb-16 border-b border-stroke bg-canvas tech-grid">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 text-center relative z-10">
        {/* Monospaced System Tag */}
        <div className="inline-flex items-center gap-2 px-3 py-1 rounded border border-stroke bg-surface text-muted text-[11px] font-mono mb-6">
          <span className="w-1.5 h-1.5 rounded-full bg-accent"></span>
          <span>CONTEXTHUB CORE SPEC v1.0</span>
          <span className="text-stroke-strong">|</span>
          <span className="text-secondary">ENTERPRISE KNOWLEDGE PLATFORM</span>
        </div>

        {/* Primary Headline */}
        <h1 className="text-3xl sm:text-5xl lg:text-6xl font-bold text-primary tracking-tight max-w-4xl mx-auto leading-[1.15] font-heading">
          Connect internal knowledge to secure,{" "}
          <span className="text-accent">grounded AI workflows.</span>
        </h1>

        {/* Subtitle / Value Proposition */}
        <p className="mt-5 text-sm sm:text-base text-muted max-w-2xl mx-auto leading-relaxed">
          Ingest institutional documents, enforce strict tenant-level access isolation, and run accurate hybrid RAG retrieval with verifiable citations and automated task execution.
        </p>

        {/* 2 Primary CTAs */}
        <div className="mt-8 flex flex-col sm:flex-row items-center justify-center gap-3">
          <Link
            href="/register"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-accent hover:bg-accent-hover text-white text-xs font-semibold px-5 py-2.5 rounded-md transition-colors shadow-sm"
          >
            <span>Deploy Free Workspace</span>
            <ArrowRight className="w-4 h-4" />
          </Link>
          <a
            href="#tour"
            className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-surface hover:bg-surface-elevated text-primary border border-stroke hover:border-stroke-strong text-xs font-medium px-5 py-2.5 rounded-md transition-colors"
          >
            <Terminal className="w-4 h-4 text-muted" />
            <span>View Interactive Tour</span>
          </a>
        </div>

        {/* Secondary Technical Spec Strip */}
        <div className="mt-14 pt-8 border-t border-stroke/70 grid grid-cols-2 lg:grid-cols-4 gap-4 max-w-4xl mx-auto text-left">
          <div className="p-3 rounded-lg bg-surface/50 border border-stroke/60">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <Shield className="w-3.5 h-3.5" />
              <span>Multi-Tenant DB Scope</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Mandatory tenant_id context constraints in SQLAlchemy UoW.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-surface/50 border border-stroke/60">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <Database className="w-3.5 h-3.5" />
              <span>Hybrid Search (RRF)</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              pgvector HNSW cosine similarity + Postgres full-text tsvector.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-surface/50 border border-stroke/60">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <FileCheck2 className="w-3.5 h-3.5" />
              <span>Verifiable Citations</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Deterministic source linking with page numbers and exact text excerpts.
            </p>
          </div>

          <div className="p-3 rounded-lg bg-surface/50 border border-stroke/60">
            <div className="flex items-center gap-2 text-accent text-xs font-semibold">
              <Cpu className="w-3.5 h-3.5" />
              <span>Async Parsing Workers</span>
            </div>
            <p className="text-[11px] text-muted mt-1">
              Celery background pipelines with modular text & PDF splitters.
            </p>
          </div>
        </div>
      </div>
    </section>
  );
}
