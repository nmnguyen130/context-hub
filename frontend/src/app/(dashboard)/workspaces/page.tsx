"use client";

import { useState } from "react";
import Link from "next/link";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import {
  FolderKanban,
  Plus,
  ArrowRight,
  Search,
  Shield,
} from "lucide-react";
import { useWorkspaces, useCreateWorkspace } from "@/features/workspace/hooks/use-workspaces";
import { workspaceSchema, WorkspaceFormValues } from "@/features/workspace/schemas";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { PermissionGuard } from "@/features/auth/permission-guard";

export default function WorkspacesDirectoryPage() {
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const { data: workspacesData, isLoading } = useWorkspaces();
  const createWorkspaceMutation = useCreateWorkspace();

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

  const workspaces = workspacesData?.items || [];
  const filteredWorkspaces = workspaces.filter((ws) =>
    ws.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (ws.description && ws.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header Bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-4 border-b border-stroke">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-primary tracking-tight font-heading">
            Workspaces Directory
          </h1>
          <p className="text-xs text-muted mt-0.5">
            Organize institutional knowledge into isolated collections with granular workspace-level access control.
          </p>
        </div>

        <PermissionGuard allowed={["ADMIN", "OWNER"]}>
          <Button
            leftIcon={<Plus className="w-4 h-4" />}
            onClick={() => setShowCreateModal(true)}
            className="bg-accent hover:bg-accent-hover text-white"
          >
            Create Workspace
          </Button>
        </PermissionGuard>
      </div>

      {/* Search & Stats Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-muted absolute left-3 top-3" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search workspaces..."
            className="w-full pl-9 pr-3 py-2 rounded-md bg-surface border border-stroke text-xs text-primary placeholder:text-muted focus:outline-none focus:border-accent"
          />
        </div>

        <div className="text-xs font-mono text-muted self-end sm:self-center">
          Showing {filteredWorkspaces.length} of {workspaces.length} workspaces
        </div>
      </div>

      {/* Workspaces Grid */}
      {isLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <div className="h-40 rounded-lg bg-surface border border-stroke animate-pulse"></div>
          <div className="h-40 rounded-lg bg-surface border border-stroke animate-pulse"></div>
          <div className="h-40 rounded-lg bg-surface border border-stroke animate-pulse"></div>
        </div>
      ) : filteredWorkspaces.length === 0 ? (
        <div className="p-12 rounded-lg bg-surface border border-stroke text-center space-y-3">
          <FolderKanban className="w-8 h-8 text-muted mx-auto opacity-50" />
          <h3 className="text-sm font-bold text-primary font-heading">No Workspaces Found</h3>
          <p className="text-xs text-muted max-w-sm mx-auto">
            {searchQuery
              ? `No workspaces matching "${searchQuery}".`
              : "Create your first workspace to start ingesting documents and managing team ACLs."}
          </p>
          <PermissionGuard allowed={["ADMIN", "OWNER"]}>
            <Button
              size="sm"
              onClick={() => setShowCreateModal(true)}
              leftIcon={<Plus className="w-3.5 h-3.5" />}
              className="bg-accent hover:bg-accent-hover text-white mt-2"
            >
              Create First Workspace
            </Button>
          </PermissionGuard>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredWorkspaces.map((ws) => (
            <Link
              key={ws.id}
              href={`/workspaces/${ws.id}`}
              className="p-5 rounded-lg bg-surface border border-stroke hover:border-accent/50 transition-all flex flex-col justify-between group"
            >
              <div>
                <div className="flex items-center justify-between mb-3">
                  <div className="w-8 h-8 rounded-md bg-surface-elevated border border-stroke flex items-center justify-center text-accent group-hover:border-accent/40 transition-colors">
                    <FolderKanban className="w-4 h-4" />
                  </div>
                  <span className="text-[10px] font-mono text-muted bg-surface-elevated px-2 py-0.5 rounded border border-stroke flex items-center gap-1">
                    <Shield className="w-3 h-3 text-success" />
                    <span>ACL Scoped</span>
                  </span>
                </div>

                <h3 className="text-sm font-bold text-primary group-hover:text-accent transition-colors truncate font-heading">
                  {ws.name}
                </h3>
                <p className="text-xs text-muted mt-1 line-clamp-2 leading-relaxed">
                  {ws.description || "No description provided for this knowledge space."}
                </p>
              </div>

              <div className="mt-5 pt-3 border-t border-stroke flex items-center justify-between text-xs text-muted">
                <span className="text-[11px] font-mono">Workspace Console</span>
                <span className="text-accent flex items-center gap-1 group-hover:translate-x-0.5 transition-transform text-xs font-semibold">
                  Open <ArrowRight className="w-3.5 h-3.5" />
                </span>
              </div>
            </Link>
          ))}
        </div>
      )}

      {/* Create Workspace Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-md w-full p-6 bg-surface border border-stroke rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-stroke pb-2">
              <h3 className="text-sm font-bold text-primary font-heading">Create New Workspace</h3>
              <button
                onClick={() => setShowCreateModal(false)}
                className="text-muted hover:text-primary text-xs cursor-pointer"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleSubmit(onCreateWorkspace)} className="space-y-3">
              <Input
                label="Workspace Name"
                placeholder="Engineering Specs"
                error={errors.name?.message}
                {...register("name")}
              />

              <Input
                label="Description (Optional)"
                placeholder="Central repository of engineering architectural designs and specs"
                error={errors.description?.message}
                {...register("description")}
              />

              <div className="flex justify-end gap-2 pt-2">
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowCreateModal(false)}
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  size="sm"
                  isLoading={createWorkspaceMutation.isPending}
                  className="bg-accent hover:bg-accent-hover text-white"
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
