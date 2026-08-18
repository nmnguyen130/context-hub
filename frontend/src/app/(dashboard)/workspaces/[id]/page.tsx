"use client";

import { useState, use } from "react";
import Link from "next/link";
import {
  FolderKanban,
  FileText,
  Upload,
  Trash2,
  Users,
  Layers,
  ArrowLeft,
  CheckCircle2,
  Loader2,
  AlertCircle,
  Clock,
  Plus,
  Eye,
} from "lucide-react";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/features/documents/hooks/use-documents";
import { Button } from "@/components/ui/button";
import { PermissionGuard } from "@/features/auth/permission-guard";
import { Document } from "@/types";

export default function WorkspaceConsolePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const resolvedParams = use(params);
  const workspaceId = resolvedParams.id;

  const [activeTab, setActiveTab] = useState<"documents" | "queue" | "members" | "retrieval">("documents");
  const [selectedChunkDoc, setSelectedChunkDoc] = useState<Document | null>(null);
  const [docToDelete, setDocToDelete] = useState<Document | null>(null);

  const { data: workspacesData } = useWorkspaces();
  const { data: documentsData, isLoading: loadingDocs } = useDocuments(workspaceId);
  const uploadDocMutation = useUploadDocument(workspaceId);
  const deleteDocMutation = useDeleteDocument(workspaceId);

  const workspace = workspacesData?.items.find((w) => w.id === workspaceId);
  const documents = documentsData?.items || [];

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadDocMutation.mutateAsync(file);
    e.target.value = "";
  };

  const confirmDelete = async () => {
    if (!docToDelete) return;
    await deleteDocMutation.mutateAsync(docToDelete.id);
    setDocToDelete(null);
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Back to Directory & Workspace Header */}
      <div className="space-y-3 pb-4 border-b border-stroke">
        <Link
          href="/workspaces"
          className="inline-flex items-center gap-1.5 text-xs text-muted hover:text-primary font-medium transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" />
          <span>Back to Workspaces Directory</span>
        </Link>

        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-surface border border-stroke flex items-center justify-center text-accent shrink-0">
              <FolderKanban className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-xl font-bold text-primary font-heading">
                  {workspace?.name || "Workspace Console"}
                </h1>
                <span className="text-[10px] font-mono text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">
                  ACL ACTIVE
                </span>
              </div>
              <p className="text-xs text-muted mt-0.5">
                {workspace?.description || "Knowledge collection and document ingestion console."}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/chat">
              <Button size="sm" className="bg-accent hover:bg-accent-hover text-white">
                Launch Chat with Workspace
              </Button>
            </Link>
          </div>
        </div>
      </div>

      {/* Tabs Navigation */}
      <div className="flex items-center gap-2 border-b border-stroke pb-2 overflow-x-auto">
        <button
          onClick={() => setActiveTab("documents")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
            activeTab === "documents"
              ? "bg-surface-elevated text-accent border border-stroke"
              : "text-muted hover:text-primary"
          }`}
        >
          <FileText className="w-3.5 h-3.5" />
          <span>Documents & Versions ({documents.length})</span>
        </button>

        <button
          onClick={() => setActiveTab("queue")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
            activeTab === "queue"
              ? "bg-surface-elevated text-accent border border-stroke"
              : "text-muted hover:text-primary"
          }`}
        >
          <Clock className="w-3.5 h-3.5" />
          <span>Ingestion Queue</span>
        </button>

        <button
          onClick={() => setActiveTab("members")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
            activeTab === "members"
              ? "bg-surface-elevated text-accent border border-stroke"
              : "text-muted hover:text-primary"
          }`}
        >
          <Users className="w-3.5 h-3.5" />
          <span>Workspace Access & ACL</span>
        </button>

        <button
          onClick={() => setActiveTab("retrieval")}
          className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-xs font-semibold transition-all cursor-pointer ${
            activeTab === "retrieval"
              ? "bg-surface-elevated text-accent border border-stroke"
              : "text-muted hover:text-primary"
          }`}
        >
          <Layers className="w-3.5 h-3.5" />
          <span>Retrieval Settings</span>
        </button>
      </div>

      {/* Tab 1: Documents & Ingestion */}
      {activeTab === "documents" && (
        <div className="space-y-6">
          {/* Ingest Uploader Area */}
          <div className="p-6 rounded-lg bg-surface border-2 border-dashed border-stroke hover:border-accent/50 transition-colors text-center space-y-3">
            <div className="w-9 h-9 rounded-md bg-surface-elevated border border-stroke flex items-center justify-center text-accent mx-auto">
              <Upload className="w-4 h-4" />
            </div>
            <div className="space-y-0.5">
              <p className="text-xs font-semibold text-primary">
                Upload documents to {workspace?.name || "this workspace"}
              </p>
              <p className="text-[11px] text-muted">
                Supported: PDF, DOCX, Markdown (.md), Text (.txt), CSV files up to 50MB.
              </p>
            </div>

            <label className="inline-block cursor-pointer">
              <input
                type="file"
                accept=".pdf,.docx,.md,.txt,.csv"
                onChange={handleFileUpload}
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

          {/* Documents Table */}
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-mono text-muted uppercase tracking-wider">
                Ingested Files ({documents.length})
              </h2>
            </div>

            {loadingDocs ? (
              <div className="p-8 text-center text-xs text-muted">Loading documents...</div>
            ) : documents.length === 0 ? (
              <div className="p-10 rounded-lg bg-surface border border-stroke text-center text-xs text-muted space-y-2">
                <FileText className="w-6 h-6 mx-auto opacity-50 text-muted" />
                <p>No documents uploaded yet. Ingest your first document above.</p>
              </div>
            ) : (
              <div className="rounded-lg bg-surface border border-stroke overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-dark text-muted border-b border-stroke font-mono text-[11px]">
                    <tr>
                      <th className="px-4 py-3">Document Name</th>
                      <th className="px-4 py-3">Version</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Size</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-stroke">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-surface-elevated/40 transition-colors">
                        <td className="px-4 py-3 font-medium text-primary flex items-center gap-2.5">
                          <FileText className="w-4 h-4 text-accent shrink-0" />
                          <span className="truncate max-w-xs">{doc.filename}</span>
                        </td>
                        <td className="px-4 py-3 text-secondary font-mono text-[11px]">
                          v1.0
                        </td>
                        <td className="px-4 py-3">
                          {doc.status === "ACTIVE" && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-success bg-success/10 px-2 py-0.5 rounded border border-success/20">
                              <CheckCircle2 className="w-3 h-3" />
                              ACTIVE
                            </span>
                          )}
                          {(doc.status === "PENDING" || doc.status === "PROCESSING") && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-warning bg-warning/10 px-2 py-0.5 rounded border border-warning/20">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              {doc.status}
                            </span>
                          )}
                          {doc.status === "ERROR" && (
                            <span className="inline-flex items-center gap-1 text-[10px] font-mono text-danger bg-danger/10 px-2 py-0.5 rounded border border-danger/20">
                              <AlertCircle className="w-3 h-3" />
                              ERROR
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-muted uppercase font-mono text-[11px]">
                          {doc.mime_type || "bin"}
                        </td>
                        <td className="px-4 py-3 text-muted font-mono text-[11px]">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </td>
                        <td className="px-4 py-3 text-right space-x-1">
                          <button
                            onClick={() => setSelectedChunkDoc(doc)}
                            className="p-1.5 rounded bg-surface-elevated hover:bg-surface-hover text-muted hover:text-accent border border-stroke transition-colors cursor-pointer"
                            title="Inspect Semantic Chunks"
                          >
                            <Eye className="w-3.5 h-3.5" />
                          </button>

                          <PermissionGuard allowed={["ADMIN", "OWNER"]}>
                            <button
                              onClick={() => setDocToDelete(doc)}
                              className="p-1.5 rounded bg-surface-elevated hover:bg-danger/10 hover:text-danger text-muted border border-stroke transition-colors cursor-pointer"
                              title="Delete Document"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          </PermissionGuard>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Ingestion Queue */}
      {activeTab === "queue" && (
        <div className="p-6 rounded-lg bg-surface border border-stroke space-y-4">
          <div className="flex items-center justify-between border-b border-stroke pb-3">
            <div>
              <h3 className="text-sm font-bold text-primary font-heading">Asynchronous Parser Queue</h3>
              <p className="text-xs text-muted">Status of Celery parsing and vectorization workers for this workspace.</p>
            </div>
            <span className="text-xs font-mono text-success flex items-center gap-1">
              <CheckCircle2 className="w-3.5 h-3.5" /> Workers Healthy
            </span>
          </div>

          <div className="space-y-2">
            {documents.filter((d) => d.status === "PENDING" || d.status === "PROCESSING").length === 0 ? (
              <div className="p-8 text-center text-xs text-muted space-y-1">
                <CheckCircle2 className="w-5 h-5 text-success mx-auto mb-2" />
                <p className="text-primary font-semibold">Queue is clear</p>
                <p>All documents in this workspace are indexed and ready for grounded retrieval.</p>
              </div>
            ) : (
              documents
                .filter((d) => d.status === "PENDING" || d.status === "PROCESSING")
                .map((d) => (
                  <div key={d.id} className="p-3 rounded bg-surface-elevated border border-stroke flex items-center justify-between text-xs">
                    <div className="flex items-center gap-2">
                      <Loader2 className="w-3.5 h-3.5 text-accent animate-spin" />
                      <span className="text-primary font-medium">{d.filename}</span>
                    </div>
                    <span className="font-mono text-[10px] text-warning">PROCESSING CHUNKS...</span>
                  </div>
                ))
            )}
          </div>
        </div>
      )}

      {/* Tab 3: Workspace Members & ACL */}
      {activeTab === "members" && (
        <div className="p-6 rounded-lg bg-surface border border-stroke space-y-4">
          <div className="flex items-center justify-between border-b border-stroke pb-3">
            <div>
              <h3 className="text-sm font-bold text-primary font-heading">Workspace Access Control (ACL)</h3>
              <p className="text-xs text-muted">Manage granular permissions for this specific knowledge space.</p>
            </div>
            <Button size="sm" variant="secondary" leftIcon={<Plus className="w-3.5 h-3.5" />}>
              Add Member Access
            </Button>
          </div>

          <div className="rounded-lg bg-surface-dark border border-stroke overflow-hidden">
            <div className="p-3.5 flex items-center justify-between text-xs">
              <div className="flex items-center gap-3">
                <div className="w-7 h-7 rounded bg-accent/20 text-accent flex items-center justify-center font-bold text-xs">
                  A
                </div>
                <div>
                  <span className="font-semibold text-primary block">Workspace Admin Team</span>
                  <span className="text-[11px] text-muted">Full read, write, chunk inspect, and purge capabilities</span>
                </div>
              </div>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-accent/10 text-accent border border-accent/30">
                WORKSPACE_ADMIN
              </span>
            </div>
          </div>
        </div>
      )}

      {/* Tab 4: Retrieval Settings */}
      {activeTab === "retrieval" && (
        <div className="p-6 rounded-lg bg-surface border border-stroke space-y-4">
          <div className="border-b border-stroke pb-3">
            <h3 className="text-sm font-bold text-primary font-heading">Workspace Retrieval Policy</h3>
            <p className="text-xs text-muted">Admin settings for hybrid RAG search defaults in this workspace.</p>
          </div>

          <div className="space-y-4 text-xs max-w-md">
            <div className="space-y-1 text-left">
              <label className="text-xs font-medium text-primary">Search Fusion Strategy</label>
              <select className="w-full p-2 rounded-md bg-surface-elevated border border-stroke text-xs text-primary">
                <option>Hybrid Dense + Sparse (RRF k=60) — Recommended</option>
                <option>Dense Vector Search Only (Cosine Distance)</option>
                <option>Sparse Exact Full-Text Keyword Search</option>
              </select>
            </div>

            <div className="space-y-1 text-left">
              <label className="text-xs font-medium text-primary">Default Top-K Chunk Limit</label>
              <select className="w-full p-2 rounded-md bg-surface-elevated border border-stroke text-xs text-primary">
                <option>5 Chunks (Balanced context)</option>
                <option>3 Chunks (Fast / Low latency)</option>
                <option>8 Chunks (Exhaustive analysis)</option>
              </select>
            </div>
          </div>
        </div>
      )}

      {/* Semantic Chunk Inspector Modal */}
      {selectedChunkDoc && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-2xl w-full p-6 bg-surface border border-stroke rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-stroke pb-2">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-accent" />
                <span className="text-sm font-bold text-primary font-heading">
                  Chunk Inspector: {selectedChunkDoc.filename}
                </span>
              </div>
              <button
                onClick={() => setSelectedChunkDoc(null)}
                className="text-muted hover:text-primary text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-muted">
              Generated semantic chunks stored in <code className="text-accent font-mono">pgvector</code> for grounded hybrid retrieval.
            </p>

            <div className="space-y-3 max-h-80 overflow-y-auto pr-1">
              {/* Chunk 1 */}
              <div className="p-3 rounded-lg bg-surface-dark border border-stroke text-xs space-y-1.5 text-left">
                <div className="flex items-center justify-between font-mono text-[10px] text-muted">
                  <span>CHUNK #1 · Page 1</span>
                  <span>Tokens: ~184 · Coordinates: [0, 42, 612, 792]</span>
                </div>
                <p className="font-mono text-[11px] text-secondary leading-relaxed bg-surface p-2.5 rounded border border-stroke">
                  &quot;ContextHub logical multi-tenancy requirements specify that every relational table must include a tenant_id column with an index.&quot;
                </p>
              </div>

              {/* Chunk 2 */}
              <div className="p-3 rounded-lg bg-surface-dark border border-stroke text-xs space-y-1.5 text-left">
                <div className="flex items-center justify-between font-mono text-[10px] text-muted">
                  <span>CHUNK #2 · Page 2</span>
                  <span>Tokens: ~210 · Coordinates: [0, 84, 612, 792]</span>
                </div>
                <p className="font-mono text-[11px] text-secondary leading-relaxed bg-surface p-2.5 rounded border border-stroke">
                  &quot;All queries (SELECT, UPDATE, DELETE) must explicitly filter by tenant_id using the context variable injected during request processing.&quot;
                </p>
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-stroke">
              <Button size="sm" variant="secondary" onClick={() => setSelectedChunkDoc(null)}>
                Close Inspector
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {docToDelete && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-sm w-full p-6 bg-surface border border-stroke rounded-xl space-y-3 text-xs">
            <h3 className="text-sm font-bold text-danger flex items-center gap-1.5 font-heading">
              <AlertCircle className="w-4 h-4" />
              Confirm Document Purge
            </h3>
            <p className="text-muted">
              Are you sure you want to delete <strong className="text-primary">{docToDelete.filename}</strong>? All associated embeddings will be removed from vector storage immediately.
            </p>
            <div className="flex justify-end gap-2 pt-2">
              <Button size="sm" variant="ghost" onClick={() => setDocToDelete(null)}>
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={confirmDelete}
                isLoading={deleteDocMutation.isPending}
                className="bg-danger hover:bg-danger/90 text-white"
              >
                Delete Document
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
