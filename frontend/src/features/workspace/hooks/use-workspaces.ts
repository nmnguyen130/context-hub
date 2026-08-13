import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { workspaceApi, WorkspaceCreatePayload } from "@/lib/api/workspace";
import { toast } from "sonner";

export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => workspaceApi.list(),
  });
}

export function useCreateWorkspace() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: WorkspaceCreatePayload) => workspaceApi.create(data),
    onSuccess: (newWorkspace) => {
      queryClient.invalidateQueries({ queryKey: ["workspaces"] });
      toast.success(`Workspace "${newWorkspace.name}" created successfully!`);
    },
    onError: (error: any) => {
      toast.error(error.message || "Failed to create workspace.");
    },
  });
}
