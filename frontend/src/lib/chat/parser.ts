export interface ParsedSSEEvent {
  event: string;
  data: any;
}

export function parseSSEBlock(block: string): ParsedSSEEvent | null {
  const lines = block.split("\n");
  let eventType = "message";
  let rawData = "";

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("event:")) {
      eventType = trimmed.slice(6).trim();
    } else if (trimmed.startsWith("data:")) {
      rawData = trimmed.slice(5).trim();
    }
  }

  if (!rawData) return null;
  if (rawData === "[DONE]") return { event: "done", data: null };

  try {
    const parsed = JSON.parse(rawData);
    if (parsed && typeof parsed === "object" && parsed.type) {
      return { event: parsed.type, data: parsed.data ?? parsed };
    }
    return { event: eventType, data: parsed };
  } catch {
    return { event: eventType, data: { text: rawData } };
  }
}
