import { useRef, useEffect } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { chatApi } from "@/lib/api/chat";
import { ChatStreamClient } from "@/lib/chat/stream-client";
import { useChatStore } from "@/store/chat-store";
import { toast } from "sonner";

export function useChatSessions(workspaceId: string | null) {
  return useQuery({
    queryKey: ["chat-sessions", workspaceId],
    queryFn: () => (workspaceId ? chatApi.listSessions(workspaceId) : null),
    enabled: Boolean(workspaceId),
  });
}

export function useChatMessages(sessionId: string | null) {
  return useQuery({
    queryKey: ["chat-messages", sessionId],
    queryFn: () => (sessionId ? chatApi.listMessages(sessionId) : null),
    enabled: Boolean(sessionId),
  });
}

export function useCreateChatSession() {
  const queryClient = useQueryClient();
  const { setActiveSessionId } = useChatStore();

  return useMutation({
    mutationFn: ({ workspaceId, title }: { workspaceId: string; title?: string }) =>
      chatApi.createSession(workspaceId, title),
    onSuccess: (session) => {
      queryClient.invalidateQueries({ queryKey: ["chat-sessions", session.workspace_id] });
      setActiveSessionId(session.id);
    },
  });
}

export function useSendChatMessage() {
  const streamClientRef = useRef<ChatStreamClient | null>(null);
  const queryClient = useQueryClient();

  const {
    setActiveSessionId,
    setIsStreaming,
    appendStreamContent,
    addCitation,
    resetStreamState,
  } = useChatStore();

  if (!streamClientRef.current) {
    streamClientRef.current = new ChatStreamClient();
  }

  // Cleanup stream on unmount
  useEffect(() => {
    return () => {
      streamClientRef.current?.stop();
    };
  }, []);

  const sendMessage = async (
    sessionId: string | null,
    workspaceId: string,
    query: string
  ) => {
    resetStreamState();
    setIsStreaming(true);

    await streamClientRef.current?.stream(
      { session_id: sessionId, workspace_id: workspaceId, message: query },
      {
        onSession: (sessionData) => {
          if (sessionData.session_id) {
            setActiveSessionId(sessionData.session_id);
            queryClient.invalidateQueries({ queryKey: ["chat-sessions", workspaceId] });
          }
        },
        onToken: (text) => appendStreamContent(text),
        onCitations: (citations) => {
          citations.forEach((c) => addCitation(c));
        },
        onDone: () => {
          setIsStreaming(false);
          if (sessionId) {
            queryClient.invalidateQueries({ queryKey: ["chat-messages", sessionId] });
          }
        },
        onError: (err) => {
          setIsStreaming(false);
          toast.error(err.message || "Failed to generate AI response");
        },
      }
    );
  };

  const stopStream = () => {
    streamClientRef.current?.stop();
    setIsStreaming(false);
  };

  return { sendMessage, stopStream };
}
