import { apiClient } from "./client";
import { Workspace, CursorPage } from "@/types";

export interface WorkspaceCreatePayload {
  name: string;
  slug?: string;
  description?: string;
  dlp_rules?: Record<string, unknown>;
}

export interface WorkspaceUpdatePayload {
  name?: string;
  description?: string;
  is_active?: boolean;
  dlp_rules?: Record<string, unknown>;
}

export const workspaceApi = {
  list: async (limit = 50, cursor?: string, tenantSlug?: string | null) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append("cursor", cursor);
    return apiClient<CursorPage<Workspace>>(`/workspaces?${params.toString()}`, { tenantSlug });
  },

  create: async (data: WorkspaceCreatePayload, tenantSlug?: string | null) => {
    return apiClient<Workspace>("/workspaces", {
      method: "POST",
      body: JSON.stringify(data),
      tenantSlug,
    });
  },

  get: async (workspaceId: string, tenantSlug?: string | null) => {
    return apiClient<Workspace>(`/workspaces/${workspaceId}`, { tenantSlug });
  },

  update: async (workspaceId: string, data: WorkspaceUpdatePayload, tenantSlug?: string | null) => {
    return apiClient<Workspace>(`/workspaces/${workspaceId}`, {
      method: "PATCH",
      body: JSON.stringify(data),
      tenantSlug,
    });
  },
};
