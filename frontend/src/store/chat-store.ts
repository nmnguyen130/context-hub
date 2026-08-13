import { create } from "zustand";
import { ChatMessage, Citation } from "@/types";

interface ChatState {
  activeSessionId: string | null;
  isStreaming: boolean;
  streamingMessageId: string | null;
  currentStreamContent: string;
  currentCitations: Citation[];
  activeCitation: Citation | null;
  setActiveSessionId: (id: string | null) => void;
  setIsStreaming: (streaming: boolean) => void;
  setStreamingMessageId: (id: string | null) => void;
  appendStreamContent: (chunk: string) => void;
  addCitation: (citation: Citation) => void;
  resetStreamState: () => void;
  setActiveCitation: (citation: Citation | null) => void;
}

export const useChatStore = create<ChatState>((set) => ({
  activeSessionId: null,
  isStreaming: false,
  streamingMessageId: null,
  currentStreamContent: "",
  currentCitations: [],
  activeCitation: null,
  setActiveSessionId: (id) => set({ activeSessionId: id }),
  setIsStreaming: (streaming) => set({ isStreaming: streaming }),
  setStreamingMessageId: (id) => set({ streamingMessageId: id }),
  appendStreamContent: (chunk) =>
    set((state) => ({ currentStreamContent: state.currentStreamContent + chunk })),
  addCitation: (citation) =>
    set((state) => ({
      currentCitations: [...state.currentCitations, citation],
    })),
  resetStreamState: () =>
    set({
      isStreaming: false,
      streamingMessageId: null,
      currentStreamContent: "",
      currentCitations: [],
    }),
  setActiveCitation: (citation) => set({ activeCitation: citation }),
}));
