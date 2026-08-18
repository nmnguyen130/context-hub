import { parseSSEBlock } from "./parser";
import { StreamCallbacks } from "./types";
import { useTenantStore } from "@/store/tenant-store";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";

export interface ChatStreamRequestPayload {
  workspace_id: string;
  message: string;
  session_id?: string | null;
  model?: string;
  retrieval_policy?: "balanced" | "fast" | "quality" | string;
  scope?: "workspace" | "all" | string;
  document_ids?: string[];
}

export class ChatStreamClient {
  private controller: AbortController | null = null;

  public async stream(
    payload: ChatStreamRequestPayload,
    callbacks: StreamCallbacks
  ): Promise<void> {
    this.stop(); // Cancel previous stream if active

    this.controller = new AbortController();
    const { tenantSlug } = useTenantStore.getState();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
    };
    if (tenantSlug) {
      headers["X-Tenant-Slug"] = tenantSlug;
    }

    try {
      const response = await fetch(`${API_BASE_URL}/chat/stream`, {
        method: "POST",
        headers,
        body: JSON.stringify(payload),
        signal: this.controller.signal,
        credentials: "include",
      });

      if (!response.ok) {
        throw new Error(`Chat stream HTTP error: ${response.statusText}`);
      }

      if (!response.body) {
        throw new Error("Response body is null");
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const blocks = buffer.split("\n\n");
        buffer = blocks.pop() || ""; // Keep leftover partial block

        for (const block of blocks) {
          const sseEvent = parseSSEBlock(block);
          if (!sseEvent) continue;

          switch (sseEvent.event) {
            case "session":
              callbacks.onSession?.(sseEvent.data);
              break;
            case "sources":
              callbacks.onSources?.(Array.isArray(sseEvent.data) ? sseEvent.data : sseEvent.data?.sources || []);
              break;
            case "token":
              callbacks.onToken?.(typeof sseEvent.data === "string" ? sseEvent.data : sseEvent.data?.text || "");
              break;
            case "citations":
            case "citation":
              callbacks.onCitations?.(Array.isArray(sseEvent.data) ? sseEvent.data : sseEvent.data?.citations || [sseEvent.data]);
              break;
            case "done":
              callbacks.onDone?.(sseEvent.data);
              break;
            case "error":
              callbacks.onError?.(
                new Error(sseEvent.data?.message || "Stream error occurred")
              );
              break;
          }
        }
      }

      callbacks.onDone?.();
    } catch (err: any) {
      if (err.name === "AbortError") {
        return; // Stream canceled intentionally
      }
      callbacks.onError?.(err instanceof Error ? err : new Error(String(err)));
    } finally {
      this.controller = null;
    }
  }

  public stop(): void {
    if (this.controller) {
      this.controller.abort();
      this.controller = null;
    }
  }
}
