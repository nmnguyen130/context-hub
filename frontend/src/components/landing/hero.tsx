"use client";

import Link from "next/link";
import { ArrowRight, ShieldCheck, Zap, Database, Lock } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export function LandingHero() {
  return (
    <section className="relative pt-24 pb-20 overflow-hidden">
      {/* Ambient background glows */}
      <div className="ambient-glow w-[500px] h-[500px] bg-indigo-600 -top-20 -left-20" />
      <div className="ambient-glow w-[600px] h-[600px] bg-purple-600 top-1/3 -right-20" />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 relative z-10 text-center">
        {/* Top badge */}
        <div className="inline-flex items-center gap-2 mb-6">
          <Badge variant="purple" size="md">
            <Zap className="w-3.5 h-3.5 text-purple-400" />
            <span>Hybrid Dense + Sparse RRF Vector Engine</span>
          </Badge>
        </div>

        {/* Main headline */}
        <h1 className="text-4xl sm:text-6xl lg:text-7xl font-extrabold text-white tracking-tight leading-[1.1] max-w-5xl mx-auto">
          The Intelligent Neural Network for Your{" "}
          <span className="text-gradient">Enterprise Knowledge</span>
        </h1>

        {/* Subtitle */}
        <p className="mt-6 text-lg sm:text-xl text-slate-300 max-w-3xl mx-auto font-light leading-relaxed">
          Ingest scattered documents, isolate multi-tenant data with strict row-level security, and retrieve grounded answers with visual inline citations.
        </p>

        {/* Primary CTA button group */}
        <div className="mt-10 flex flex-col sm:flex-row items-center justify-center gap-4">
          <Link href="/register">
            <Button size="lg" className="w-full sm:w-auto text-base px-8 py-3.5">
              <span>Start Free Workspace</span>
              <ArrowRight className="w-5 h-5 ml-1" />
            </Button>
          </Link>
          <a href="#demo">
            <Button variant="outline" size="lg" className="w-full sm:w-auto text-base px-8 py-3.5">
              <span>See Interactive RAG Demo</span>
            </Button>
          </a>
        </div>

        {/* Key trust badges */}
        <div className="mt-16 pt-8 border-t border-slate-800/80 grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto text-slate-400 text-xs font-medium uppercase tracking-wider">
          <div className="flex items-center justify-center gap-2">
            <Lock className="w-4 h-4 text-indigo-400" />
            <span>Logical Multi-Tenancy</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Database className="w-4 h-4 text-cyan-400" />
            <span>Postgres + pgvector HNSW</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <Zap className="w-4 h-4 text-purple-400" />
            <span>Reciprocal Rank Fusion</span>
          </div>
          <div className="flex items-center justify-center gap-2">
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
            <span>Strict LLM Grounding</span>
          </div>
        </div>
      </div>
    </section>
  );
}
