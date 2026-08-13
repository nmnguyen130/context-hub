import { apiClient } from "./client";
import { ChatSession, ChatMessage, CursorPage } from "@/types";

export const chatApi = {
  createSession: async (workspaceId: string, title?: string, tenantSlug?: string | null) => {
    return apiClient<ChatSession>("/chat/sessions", {
      method: "POST",
      body: JSON.stringify({ workspace_id: workspaceId, title }),
      tenantSlug,
    });
  },

  listSessions: async (workspaceId: string, limit = 50, cursor?: string, tenantSlug?: string | null) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append("cursor", cursor);
    return apiClient<CursorPage<ChatSession>>(
      `/chat/sessions/workspace/${workspaceId}?${params.toString()}`,
      { tenantSlug }
    );
  },

  getSession: async (sessionId: string, tenantSlug?: string | null) => {
    return apiClient<ChatSession>(`/chat/sessions/${sessionId}`, { tenantSlug });
  },

  deleteSession: async (sessionId: string, tenantSlug?: string | null) => {
    return apiClient<void>(`/chat/sessions/${sessionId}`, {
      method: "DELETE",
      tenantSlug,
    });
  },

  listMessages: async (sessionId: string, limit = 50, cursor?: string, tenantSlug?: string | null) => {
    const params = new URLSearchParams({ limit: limit.toString() });
    if (cursor) params.append("cursor", cursor);
    return apiClient<CursorPage<ChatMessage>>(
      `/chat/sessions/${sessionId}/messages?${params.toString()}`,
      { tenantSlug }
    );
  },

  submitFeedback: async (
    messageId: string,
    rating: "up" | "down",
    feedback_note?: string,
    tenantSlug?: string | null
  ) => {
    return apiClient<ChatMessage>(`/chat/messages/${messageId}/feedback`, {
      method: "POST",
      body: JSON.stringify({ rating, feedback_note }),
      tenantSlug,
    });
  },
};
