import { apiClient } from "./client";
import { Document, CursorPage } from "@/types";

export const documentsApi = {
  listByWorkspace: async (workspaceId: string, limit = 50, cursor?: string, tenantSlug?: string | null) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append("cursor", cursor);
    return apiClient<CursorPage<Document>>(
      `/documents/workspace/${workspaceId}?${params.toString()}`,
      { tenantSlug }
    );
  },

  upload: async (workspaceId: string, file: File, tenantSlug?: string | null) => {
    const formData = new FormData();
    formData.append("file", file);

    return apiClient<{ document: Document }>(`/documents/upload/${workspaceId}`, {
      method: "POST",
      body: formData,
      tenantSlug,
    });
  },

  get: async (documentId: string, tenantSlug?: string | null) => {
    return apiClient<Document>(`/documents/${documentId}`, { tenantSlug });
  },

  reingest: async (documentId: string, file: File, tenantSlug?: string | null) => {
    const formData = new FormData();
    formData.append("file", file);

    return apiClient<{ document: Document; message: string }>(
      `/documents/${documentId}/reingest`,
      {
        method: "POST",
        body: formData,
        tenantSlug,
      }
    );
  },

  delete: async (documentId: string, tenantSlug?: string | null) => {
    return apiClient<void>(`/documents/${documentId}`, {
      method: "DELETE",
      tenantSlug,
    });
  },
};
