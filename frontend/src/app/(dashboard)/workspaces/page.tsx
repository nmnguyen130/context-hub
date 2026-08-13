"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FolderKanban,
  Plus,
  Upload,
  FileText,
  Trash2,
  Globe,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Clock,
} from "lucide-react";
import { useWorkspaces, useCreateWorkspace } from "@/features/workspace/hooks/use-workspaces";
import { useDocuments, useUploadDocument, useDeleteDocument } from "@/features/documents/hooks/use-documents";
import { useWorkspaceStore } from "@/store/workspace-store";
import { workspaceSchema, WorkspaceFormValues } from "@/features/workspace/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { PermissionGuard } from "@/features/auth/permission-guard";

export default function WorkspacesPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const { data: workspacesData, isLoading: loadingWorkspaces } = useWorkspaces();
  const { activeWorkspaceId, setActiveWorkspaceId } = useWorkspaceStore();
  const { data: documentsData, isLoading: loadingDocs } = useDocuments(activeWorkspaceId);

  const createWorkspaceMutation = useCreateWorkspace();
  const uploadDocMutation = useUploadDocument(activeWorkspaceId);
  const deleteDocMutation = useDeleteDocument(activeWorkspaceId);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<WorkspaceFormValues>({
    resolver: zodResolver(workspaceSchema),
    defaultValues: {
      name: "",
      slug: "",
      description: "",
    },
  });

  const onCreateWorkspace = async (data: WorkspaceFormValues) => {
    await createWorkspaceMutation.mutateAsync(data);
    reset();
    setShowCreateModal(false);
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    await uploadDocMutation.mutateAsync(file);
    e.target.value = "";
  };

  const workspaces = workspacesData?.items || [];
  const documents = documentsData?.items || [];

  return (
    <div className="space-y-8 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white font-outfit">Workspaces & Knowledge Base</h1>
          <p className="text-slate-400 text-xs mt-1">
            Organize documents into dedicated workspaces for grounded RAG ingestion.
          </p>
        </div>

        <PermissionGuard allowed={["ADMIN", "OWNER"]}>
          <Button
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setShowCreateModal(true)}
          >
            Create Workspace
          </Button>
        </PermissionGuard>
      </div>

      {/* Workspaces Selector Grid */}
      <div>
        <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Select Workspace
        </h2>

        {loadingWorkspaces ? (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
            <Skeleton className="h-24" />
          </div>
        ) : workspaces.length === 0 ? (
          <div className="glass-panel p-8 rounded-xl text-center border border-slate-800">
            <FolderKanban className="w-10 h-10 text-slate-500 mx-auto mb-2" />
            <p className="text-sm font-semibold text-slate-300">No Workspaces Found</p>
            <p className="text-xs text-slate-500 mt-1">Create your first workspace to begin uploading documents.</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {workspaces.map((ws) => {
              const isSelected = activeWorkspaceId === ws.id;

              return (
                <div
                  key={ws.id}
                  onClick={() => setActiveWorkspaceId(ws.id)}
                  className={`glass-card p-4 rounded-xl cursor-pointer transition-all border ${
                    isSelected
                      ? "border-indigo-500 bg-indigo-950/30 ring-1 ring-indigo-500/50 shadow-lg shadow-indigo-500/10"
                      : "border-slate-800 hover:border-slate-700"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <FolderKanban
                        className={`w-4 h-4 ${isSelected ? "text-indigo-400" : "text-slate-400"}`}
                      />
                      <h3 className="text-sm font-bold text-white truncate">{ws.name}</h3>
                    </div>
                    <span title="Active Workspace">
                      <Globe className="w-3.5 h-3.5 text-slate-500" />
                    </span>
                  </div>
                  {ws.description && (
                    <p className="text-xs text-slate-400 mt-2 line-clamp-1">{ws.description}</p>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Document Upload & File List Section */}
      {activeWorkspaceId ? (
        <div className="space-y-6">
          {/* File Upload Box */}
          <Card className="glass-panel p-6 border-dashed border-2 border-slate-700 hover:border-indigo-500/60 transition-colors">
            <div className="flex flex-col items-center justify-center text-center">
              <div className="w-12 h-12 rounded-xl bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mb-3">
                <Upload className="w-6 h-6" />
              </div>
              <h3 className="text-sm font-bold text-slate-100">
                Upload Document to Active Workspace
              </h3>
              <p className="text-xs text-slate-400 mt-1 max-w-sm">
                Supports <span className="text-slate-200 font-semibold">PDF, Markdown (.md), Text (.txt)</span> files up to 50MB.
              </p>

              <label className="mt-4 cursor-pointer">
                <input
                  type="file"
                  accept=".pdf,.md,.txt,.docx"
                  onChange={handleFileUpload}
                  disabled={uploadDocMutation.isPending}
                  className="hidden"
                />
                <Button
                  variant="primary"
                  size="sm"
                  isLoading={uploadDocMutation.isPending}
                  leftIcon={<Upload className="w-4 h-4" />}
                >
                  Select File from Computer
                </Button>
              </label>
            </div>
          </Card>

          {/* Document Table */}
          <div>
            <h2 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
              Ingested Documents ({documents.length})
            </h2>

            {loadingDocs ? (
              <div className="space-y-2">
                <Skeleton className="h-14" />
                <Skeleton className="h-14" />
              </div>
            ) : documents.length === 0 ? (
              <div className="glass-panel p-8 rounded-xl text-center border border-slate-800 text-slate-400 text-xs">
                No documents uploaded to this workspace yet.
              </div>
            ) : (
              <div className="glass-panel rounded-xl border border-slate-800 overflow-hidden">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-900/90 text-slate-400 border-b border-slate-800 font-semibold uppercase tracking-wider">
                    <tr>
                      <th className="px-4 py-3">Document Name</th>
                      <th className="px-4 py-3">Status</th>
                      <th className="px-4 py-3">Type</th>
                      <th className="px-4 py-3">Size</th>
                      <th className="px-4 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/80">
                    {documents.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-900/40 transition-colors">
                        <td className="px-4 py-3 flex items-center gap-2.5 font-medium text-slate-200">
                          <FileText className="w-4 h-4 text-indigo-400 shrink-0" />
                          <span className="truncate max-w-xs">{doc.filename}</span>
                        </td>
                        <td className="px-4 py-3">
                          {doc.status === "ACTIVE" && (
                            <Badge variant="success" size="sm">
                              <CheckCircle2 className="w-3 h-3" />
                              <span>ACTIVE</span>
                            </Badge>
                          )}
                          {(doc.status === "PENDING" || doc.status === "PROCESSING") && (
                            <Badge variant="warning" size="sm">
                              <Loader2 className="w-3 h-3 animate-spin" />
                              <span>{doc.status}</span>
                            </Badge>
                          )}
                          {doc.status === "ERROR" && (
                            <Badge variant="error" size="sm">
                              <AlertCircle className="w-3 h-3" />
                              <span>ERROR</span>
                            </Badge>
                          )}
                        </td>
                        <td className="px-4 py-3 text-slate-400 uppercase">{doc.mime_type || "bin"}</td>
                        <td className="px-4 py-3 text-slate-400">
                          {(doc.file_size / 1024).toFixed(1)} KB
                        </td>
                        <td className="px-4 py-3 text-right">
                          <PermissionGuard allowed={["ADMIN", "OWNER"]}>
                            <button
                              onClick={() => deleteDocMutation.mutate(doc.id)}
                              disabled={deleteDocMutation.isPending}
                              className="p-1.5 rounded bg-slate-900 hover:bg-rose-950/80 hover:text-rose-400 text-slate-400 border border-slate-800 transition-colors"
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
      ) : (
        <div className="glass-panel p-12 rounded-xl text-center border border-slate-800 text-slate-400">
          <Clock className="w-8 h-8 mx-auto mb-2 text-slate-500" />
          <p className="text-sm font-medium">Please select a workspace above to view and upload documents.</p>
        </div>
      )}

      {/* Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="glass-panel max-w-md w-full rounded-2xl p-6 border border-slate-800 shadow-2xl bg-slate-950">
            <h3 className="text-lg font-bold text-white font-outfit mb-4">Create New Workspace</h3>

            <form onSubmit={handleSubmit(onCreateWorkspace)} className="space-y-4">
              <Input
                label="Workspace Name"
                placeholder="Engineering Specs"
                error={errors.name?.message}
                {...register("name")}
              />

              <Input
                label="Description (Optional)"
                placeholder="Repository of engineering design specs and architecture notes"
                error={errors.description?.message}
                {...register("description")}
              />

              <div className="flex items-center justify-end gap-3 mt-6">
                <Button
                  type="button"
                  variant="ghost"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  isLoading={createWorkspaceMutation.isPending}
                >
                  Create Workspace
                </Button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
