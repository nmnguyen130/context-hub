import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { documentsApi } from "@/lib/api/documents";
import { toast } from "sonner";

export function useDocuments(workspaceId: string | null) {
  return useQuery({
    queryKey: ["documents", workspaceId],
    queryFn: () => (workspaceId ? documentsApi.listByWorkspace(workspaceId) : null),
    enabled: Boolean(workspaceId),
    refetchInterval: (query) => {
      // Auto-poll if any document is currently in PENDING or PROCESSING state
      const hasProcessingDocs = query.state.data?.items.some(
        (doc) => doc.status === "PENDING" || doc.status === "PROCESSING"
      );
      return hasProcessingDocs ? 3000 : false;
    },
  });
}

export function useUploadDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (file: File) => {
      if (!workspaceId) throw new Error("No active workspace selected.");
      return documentsApi.upload(workspaceId, file);
    },
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
      toast.success(`Document "${res.document.filename}" uploaded. Processing started!`);
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to upload document.");
    },
  });
}

export function useDeleteDocument(workspaceId: string | null) {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (documentId: string) => documentsApi.delete(documentId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["documents", workspaceId] });
      toast.success("Document deleted.");
    },
    onError: (err: any) => {
      toast.error(err.message || "Failed to delete document.");
    },
  });
}
