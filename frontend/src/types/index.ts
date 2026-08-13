export type UserRole = "SUPER_ADMIN" | "OWNER" | "ADMIN" | "MEMBER" | "VIEWER";
export type PlanTier = "FREE" | "PRO" | "ENTERPRISE";

export interface User {
  id: string;
  email: string;
  role: UserRole;
  is_active: boolean;
  display_name: string | null;
  avatar_url: string | null;
  created_at: string;
  updated_at: string;
}

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  plan_tier: PlanTier;
  settings: Record<string, unknown>;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  dlp_rules: Record<string, unknown> | null;
  created_at: string;
  updated_at: string;
}

export type DocumentStatus = "PENDING" | "PROCESSING" | "ACTIVE" | "ERROR";

export interface Document {
  id: string;
  workspace_id: string;
  filename: string;
  mime_type: string;
  file_size: number;
  content_hash: string;
  version: number;
  status: DocumentStatus;
  error_message: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  index: number;
  document_id: string;
  document_name: string;
  chunk_id: string;
  content_excerpt: string;
  page_numbers: number[];
  confidence: number;
}

export interface ChatSession {
  id: string;
  workspace_id: string;
  user_id: string;
  title: string | null;
  running_summary: string | null;
  message_count: number;
  total_tokens: number;
  total_cost_usd: number;
  created_at: string;
  updated_at: string;
}

export interface ChatMessage {
  id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[] | Record<string, unknown>[] | null;
  confidence_score: number | null;
  token_count: number;
  cost_usd: number;
  feedback: "up" | "down" | null;
  feedback_note: string | null;
  created_at: string;
}

export interface CursorPage<T> {
  items: T[];
  next_cursor?: string | null;
  has_more: boolean;
}

export interface TenantStats {
  user_count: number;
  document_count: number;
  storage_used_bytes: number;
}
