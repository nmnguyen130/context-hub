import { apiClient } from "./client";
import { User, Tenant, CursorPage } from "@/types";

export interface LoginPayload {
  tenant_slug: string;
  email: string;
  password: string;
}

export interface RegisterPayload {
  tenant_name: string;
  email: string;
  password: string;
  display_name?: string;
}

export const authApi = {
  login: async (data: LoginPayload) => {
    return apiClient<{ user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  register: async (data: RegisterPayload) => {
    return apiClient<User>("/auth/register", {
      method: "POST",
      body: JSON.stringify(data),
    });
  },

  logout: async () => {
    return apiClient<void>("/api/auth/logout", {
      method: "POST",
    });
  },

  refresh: async () => {
    return apiClient<{ success: boolean }>("/api/auth/refresh", {
      method: "POST",
    });
  },

  getCurrentUser: async () => {
    return apiClient<User>("/api/auth/me");
  },

  getCurrentTenant: async (tenantSlug?: string | null) => {
    return apiClient<Tenant>("/tenant", { tenantSlug });
  },

  resolveTenantSlug: async (slug: string) => {
    return apiClient<{ exists: boolean; name?: string }>(`/tenants/lookup/${slug}`);
  },

  listUsers: async (limit = 20, cursor?: string, tenantSlug?: string | null) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append("cursor", cursor);
    return apiClient<CursorPage<User>>(`/auth/users?${params.toString()}`, { tenantSlug });
  },
};
