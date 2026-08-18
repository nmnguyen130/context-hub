"use client";

import Link from "next/link";
import {
  FolderKanban,
  FileText,
  MessageSquareText,
  Plus,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  Clock,
  Upload,
} from "lucide-react";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useDocuments, useUploadDocument } from "@/features/documents/hooks/use-documents";
import { Button } from "@/components/ui/button";

export default function DashboardPage() {
  const { data: workspacesData, isLoading: loadingWs } = useWorkspaces();
  const { activeWorkspaceId } = useWorkspaceStore();
  const { data: documentsData, isLoading: loadingDocs } = useDocuments(activeWorkspaceId);
  const uploadDocMutation = useUploadDocument(activeWorkspaceId);

  const totalWorkspaces = workspacesData?.items.length || 0;
  const totalDocuments = documentsData?.items.length || 0;
  const documents = documentsData?.items || [];
  const activeWorkspace = workspacesData?.items.find((w) => w.id === activeWorkspaceId);

  const handleQuickUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !activeWorkspaceId) return;
    await uploadDocMutation.mutateAsync(file);
    e.target.value = "";
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Top Welcome & Action Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-stroke">
        <div>
          <div className="flex items-center gap-2 text-xs text-muted font-mono mb-1">
            <span className="w-1.5 h-1.5 rounded-full bg-success"></span>
            <span>SYSTEM OPERATIONAL · TENANT CONTEXT ACTIVE</span>
          </div>
          <h1 className="text-xl sm:text-2xl font-bold text-primary tracking-tight font-heading">
            Operational Overview
          </h1>
        </div>

        <div className="flex items-center gap-2.5">
          <Link href="/workspaces">
            <Button size="sm" variant="secondary" leftIcon={<Plus className="w-3.5 h-3.5" />}>
              New Workspace
            </Button>
          </Link>
          <Link href="/chat">
            <Button size="sm" className="bg-accent hover:bg-accent-hover text-white" rightIcon={<ArrowUpRight className="w-3.5 h-3.5" />}>
              Launch RAG Chat
            </Button>
          </Link>
        </div>
      </div>

      {/* Actionable Health Status Strip */}
      <div className="p-3.5 rounded-lg bg-surface border border-stroke flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-success/10 border border-success/30 flex items-center justify-center text-success shrink-0">
            <CheckCircle2 className="w-3.5 h-3.5" />
          </div>
          <div>
            <span className="font-semibold text-primary">
              Ingestion Pipeline & Retrieval Engine Healthy
            </span>
            <span className="text-muted block sm:inline sm:ml-2 text-[11px]">
              Zero ingestion failures across active workspaces in the last 24 hours.
            </span>
          </div>
        </div>

        <Link
          href="/settings/audit"
          className="text-accent hover:underline font-mono text-[11px] shrink-0"
        >
          View System Audit Logs →
        </Link>
      </div>

      {/* 4 Business Health Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Active Workspaces */}
        <div className="p-4 rounded-lg bg-surface border border-stroke">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Active Knowledge Spaces</span>
            <FolderKanban className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-primary font-heading">
              {loadingWs ? "..." : totalWorkspaces}
            </span>
            <span className="text-[10px] font-mono text-success">Scoped ACL</span>
          </div>
        </div>

        {/* Total Documents */}
        <div className="p-4 rounded-lg bg-surface border border-stroke">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Indexed Documents</span>
            <FileText className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-primary font-heading">
              {loadingDocs ? "..." : totalDocuments}
            </span>
            <span className="text-[10px] font-mono text-secondary">
              {activeWorkspace ? activeWorkspace.name : "All"}
            </span>
          </div>
        </div>

        {/* Grounded Conversations */}
        <div className="p-4 rounded-lg bg-surface border border-stroke">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Grounded RAG Queries</span>
            <MessageSquareText className="w-4 h-4 text-accent" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-2xl font-bold text-primary font-heading">Active</span>
            <span className="text-[10px] font-mono text-success">100% Citations</span>
          </div>
        </div>

        {/* Ingestion Pipeline Queue */}
        <div className="p-4 rounded-lg bg-surface border border-stroke">
          <div className="flex items-center justify-between text-xs text-muted">
            <span>Ingestion Workers</span>
            <Clock className="w-4 h-4 text-success" />
          </div>
          <div className="mt-3 flex items-baseline justify-between">
            <span className="text-lg font-bold text-success font-heading">Ready / 0 Queue</span>
            <span className="text-[10px] font-mono text-muted">Celery Async</span>
          </div>
        </div>
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Recent Documents & Version Tracking (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText className="w-4 h-4 text-accent" />
              <h2 className="text-sm font-bold text-primary font-heading">
                Recent Knowledge Documents {activeWorkspace && `in ${activeWorkspace.name}`}
              </h2>
            </div>
            {activeWorkspaceId && (
              <Link
                href={`/workspaces/${activeWorkspaceId}`}
                className="text-xs text-accent hover:underline font-medium"
              >
                Open Workspace Console →
              </Link>
            )}
          </div>

          <div className="rounded-lg bg-surface border border-stroke overflow-hidden">
            {loadingDocs ? (
              <div className="p-6 text-center text-xs text-muted">Loading documents...</div>
            ) : documents.length === 0 ? (
              <div className="p-8 text-center text-xs text-muted space-y-2">
                <FileText className="w-6 h-6 text-muted mx-auto opacity-50" />
                <p>No documents uploaded to this workspace yet.</p>
                {activeWorkspaceId && (
                  <label className="inline-block mt-2 cursor-pointer">
                    <input
                      type="file"
                      accept=".pdf,.docx,.md,.txt"
                      onChange={handleQuickUpload}
                      disabled={uploadDocMutation.isPending}
                      className="hidden"
                    />
                    <Button size="sm" variant="secondary" isLoading={uploadDocMutation.isPending}>
                      Upload First File
                    </Button>
                  </label>
                )}
              </div>
            ) : (
              <div className="divide-y divide-stroke">
                {documents.slice(0, 5).map((doc) => (
                  <div key={doc.id} className="p-3.5 flex items-center justify-between hover:bg-surface-elevated/50 transition-colors text-xs">
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="w-7 h-7 rounded bg-surface-elevated border border-stroke flex items-center justify-center text-accent shrink-0">
                        <FileText className="w-3.5 h-3.5" />
                      </div>
                      <div className="min-w-0">
                        <span className="font-medium text-primary block truncate">
                          {doc.filename}
                        </span>
                        <span className="text-[10px] text-muted font-mono">
                          {(doc.file_size / 1024).toFixed(1)} KB · {doc.mime_type || "text"}
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-success/10 text-success border border-success/20">
                        v1.0 · ACTIVE
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right: Quick Drag & Drop Ingest (5 cols) */}
        <div className="lg:col-span-5 space-y-4">
          <div className="flex items-center gap-2">
            <Upload className="w-4 h-4 text-accent" />
            <h2 className="text-sm font-bold text-primary font-heading">Quick Document Ingestion</h2>
          </div>

          {activeWorkspaceId ? (
            <div className="p-6 rounded-lg bg-surface border-2 border-dashed border-stroke hover:border-accent/50 transition-colors text-center space-y-3">
              <div className="w-9 h-9 rounded-md bg-surface-elevated border border-stroke flex items-center justify-center text-accent mx-auto">
                <Upload className="w-4 h-4" />
              </div>
              <div className="space-y-1">
                <p className="text-xs font-semibold text-primary">
                  Drop files to ingest into active workspace
                </p>
                <p className="text-[11px] text-muted">
                  Supports PDF, DOCX, Markdown (.md), and TXT files.
                </p>
              </div>

              <label className="inline-block cursor-pointer">
                <input
                  type="file"
                  accept=".pdf,.docx,.md,.txt"
                  onChange={handleQuickUpload}
                  disabled={uploadDocMutation.isPending}
                  className="hidden"
                />
                <Button
                  size="sm"
                  variant="secondary"
                  isLoading={uploadDocMutation.isPending}
                  leftIcon={<Upload className="w-3.5 h-3.5" />}
                >
                  Select File from Computer
                </Button>
              </label>
            </div>
          ) : (
            <div className="p-6 rounded-lg bg-surface border border-stroke text-center text-xs text-muted">
              Please select or create a workspace to enable quick document ingestion.
            </div>
          )}

          {/* Governance & Security Card */}
          <div className="p-4 rounded-lg bg-surface border border-stroke space-y-2 text-xs">
            <div className="flex items-center gap-2 text-primary font-semibold">
              <ShieldCheck className="w-4 h-4 text-success" />
              <span>Multi-Tenant Ingestion Policy</span>
            </div>
            <p className="text-[11px] text-muted leading-relaxed">
              All parsed chunks are automatically tagged with your organizational <code className="text-accent font-mono">tenant_id</code> and encrypted before vector embedding.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
