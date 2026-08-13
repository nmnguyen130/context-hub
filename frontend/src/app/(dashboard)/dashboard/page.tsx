"use client";

import Link from "next/link";
import {
  FolderKanban,
  FileText,
  MessageSquareText,
  Database,
  ArrowUpRight,
  Plus,
  Sparkles,
} from "lucide-react";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useDocuments } from "@/features/documents/hooks/use-documents";
import { Card, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";

export default function DashboardPage() {
  const { data: workspacesData, isLoading: loadingWs } = useWorkspaces();
  const { activeWorkspaceId } = useWorkspaceStore();
  const { data: documentsData } = useDocuments(activeWorkspaceId);

  const totalWorkspaces = workspacesData?.items.length || 0;
  const totalDocuments = documentsData?.items.length || 0;

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Welcome Banner */}
      <div className="glass-panel p-6 sm:p-8 rounded-2xl border border-slate-800 bg-gradient-to-r from-indigo-950/40 via-purple-950/20 to-slate-950 relative overflow-hidden">
        <div className="ambient-glow w-96 h-96 bg-indigo-600/30 -top-20 -right-20" />

        <div className="relative z-10 flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <Badge variant="purple" size="md" className="mb-3">
              <Sparkles className="w-3.5 h-3.5 text-purple-400" />
              <span>Multi-Tenant AI Knowledge Network</span>
            </Badge>
            <h1 className="text-2xl sm:text-3xl font-bold text-white font-outfit">
              Enterprise Neural Dashboard
            </h1>
            <p className="text-slate-400 text-xs sm:text-sm mt-1 max-w-2xl">
              Centralize organizational intelligence, manage hybrid RAG document ingestion, and start grounded conversations.
            </p>
          </div>

          <div className="flex items-center gap-3">
            <Link href="/workspaces">
              <Button leftIcon={<Plus className="w-4 h-4" />}>New Workspace</Button>
            </Link>
            <Link href="/chat">
              <Button variant="outline" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
                Launch RAG Chat
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Analytics Stat Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        <Card className="glass-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Total Workspaces</span>
              <div className="p-2 rounded-lg bg-indigo-950/80 text-indigo-400 border border-indigo-500/30">
                <FolderKanban className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-white font-outfit">
                {loadingWs ? "..." : totalWorkspaces}
              </span>
            </div>
          </CardHeader>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Active Documents</span>
              <div className="p-2 rounded-lg bg-cyan-950/80 text-cyan-400 border border-cyan-500/30">
                <FileText className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4">
              <span className="text-3xl font-extrabold text-white font-outfit">
                {totalDocuments}
              </span>
            </div>
          </CardHeader>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">Vector Index Mode</span>
              <div className="p-2 rounded-lg bg-purple-950/80 text-purple-400 border border-purple-500/30">
                <Database className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-lg font-bold text-emerald-400 font-outfit">
                pgvector HNSW
              </span>
            </div>
          </CardHeader>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <div className="flex items-center justify-between">
              <span className="text-xs text-slate-400 font-medium">RAG Fusion Model</span>
              <div className="p-2 rounded-lg bg-emerald-950/80 text-emerald-400 border border-emerald-500/30">
                <MessageSquareText className="w-4 h-4" />
              </div>
            </div>
            <div className="mt-4 flex items-center gap-2">
              <span className="text-lg font-bold text-white font-outfit">
                Dense + Sparse RRF
              </span>
            </div>
          </CardHeader>
        </Card>
      </div>

      {/* Quick Navigation Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <Card className="glass-card p-6">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <FolderKanban className="w-5 h-5 text-indigo-400" />
              Workspace Management
            </CardTitle>
            <CardDescription>
              Create private or shared knowledge collections and ingest PDFs, Markdown, and text archives.
            </CardDescription>
          </CardHeader>
          <div className="mt-4">
            <Link href="/workspaces">
              <Button size="sm" variant="secondary" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
                Manage Documents
              </Button>
            </Link>
          </div>
        </Card>

        <Card className="glass-card p-6">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <MessageSquareText className="w-5 h-5 text-cyan-400" />
              Grounded Conversational RAG
            </CardTitle>
            <CardDescription>
              Query your indexed documents in real-time with inline citations and document source verification.
            </CardDescription>
          </CardHeader>
          <div className="mt-4">
            <Link href="/chat">
              <Button size="sm" variant="primary" rightIcon={<ArrowUpRight className="w-4 h-4" />}>
                Open RAG Chat Window
              </Button>
            </Link>
          </div>
        </Card>
      </div>
    </div>
  );
}
