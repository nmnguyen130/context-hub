import { Citation } from "@/types";

export type SSEEventType =
  | "session"
  | "sources"
  | "token"
  | "citations"
  | "done"
  | "error";

export interface SSESessionData {
  session_id: string;
  title?: string;
  workspace_id?: string;
}

export interface SSETokenData {
  text: string;
}

export interface SSEDoneData {
  full_text?: string;
  citation_count?: number;
  usage?: Record<string, unknown>;
}

export interface StreamCallbacks {
  onSession?: (data: SSESessionData) => void;
  onSources?: (sources: Record<string, unknown>[]) => void;
  onToken?: (text: string) => void;
  onCitations?: (citations: Citation[]) => void;
  onDone?: (data?: SSEDoneData) => void;
  onError?: (error: Error) => void;
}
