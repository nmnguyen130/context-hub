"use client";

import { useState, useEffect, useRef } from "react";
import {
  Sparkles,
  Send,
  Plus,
  FileText,
  Square,
  Clock,
  X,
  MessageSquareText,
} from "lucide-react";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useChatStore } from "@/store/chat-store";
import {
  useChatSessions,
  useChatMessages,
  useCreateChatSession,
  useSendChatMessage,
} from "@/features/chat/hooks/use-chat";
import { Citation } from "@/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";

export default function ChatPage() {
  const [inputQuery, setInputQuery] = useState("");
  const { activeWorkspaceId } = useWorkspaceStore();
  const {
    activeSessionId,
    setActiveSessionId,
    isStreaming,
    currentStreamContent,
    currentCitations,
  } = useChatStore();

  const { data: sessionsData, isLoading: loadingSessions } = useChatSessions(activeWorkspaceId);
  const { data: messagesData, isLoading: loadingMessages } = useChatMessages(activeSessionId);
  const createSessionMutation = useCreateChatSession();
  const { sendMessage, stopStream } = useSendChatMessage();

  const [selectedCitation, setSelectedCitation] = useState<Citation | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const sessions = sessionsData?.items || [];
  const messages = messagesData?.items || [];

  // Scroll to bottom on new stream content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [currentStreamContent, messages.length]);

  const handleStartNewSession = async () => {
    if (!activeWorkspaceId) return;
    await createSessionMutation.mutateAsync({ workspaceId: activeWorkspaceId });
  };

  const handleSend = async (e?: React.FormEvent) => {
    e?.preventDefault();
    if (!inputQuery.trim() || !activeWorkspaceId) return;

    let targetSessionId = activeSessionId;
    if (!targetSessionId) {
      const newSession = await createSessionMutation.mutateAsync({
        workspaceId: activeWorkspaceId,
        title: inputQuery.slice(0, 30),
      });
      targetSessionId = newSession.id;
    }

    const query = inputQuery;
    setInputQuery("");
    await sendMessage(targetSessionId, activeWorkspaceId, query);
  };

  return (
    <div className="h-[calc(100vh-7rem)] flex gap-4 max-w-7xl mx-auto">
      {/* Session History Sidebar */}
      <div className="w-64 glass-panel rounded-2xl p-4 border border-slate-800 flex flex-col justify-between hidden md:flex">
        <div>
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Chat History
            </span>
            <button
              onClick={handleStartNewSession}
              disabled={!activeWorkspaceId}
              className="p-1.5 rounded-lg bg-indigo-600/20 hover:bg-indigo-600/40 text-indigo-300 border border-indigo-500/30 transition-colors"
              title="New Session"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>

          <div className="space-y-1.5 overflow-y-auto max-h-[calc(100vh-14rem)] pr-1">
            {loadingSessions ? (
              <div className="space-y-2">
                <Skeleton className="h-10" />
                <Skeleton className="h-10" />
              </div>
            ) : sessions.length === 0 ? (
              <p className="text-xs text-slate-500 text-center py-4">No chat sessions yet.</p>
            ) : (
              sessions.map((s) => {
                const isSelected = activeSessionId === s.id;
                return (
                  <div
                    key={s.id}
                    onClick={() => setActiveSessionId(s.id)}
                    className={`flex items-center justify-between p-2.5 rounded-xl cursor-pointer text-xs transition-all ${
                      isSelected
                        ? "bg-indigo-950/60 text-indigo-200 border border-indigo-500/40 font-medium"
                        : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
                    }`}
                  >
                    <div className="flex items-center gap-2 truncate">
                      <MessageSquareText className="w-3.5 h-3.5 shrink-0 text-indigo-400" />
                      <span className="truncate">{s.title || "Untitled Chat"}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        <div className="pt-3 border-t border-slate-800 text-[11px] text-slate-500 flex items-center gap-1.5">
          <Clock className="w-3.5 h-3.5 text-slate-400" />
          <span>Grounded in Active Workspace</span>
        </div>
      </div>

      {/* Main Chat Conversation Window */}
      <div className="flex-1 glass-panel rounded-2xl border border-slate-800 flex flex-col justify-between overflow-hidden bg-slate-950/70">
        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loadingMessages ? (
            <div className="space-y-4">
              <Skeleton className="h-16 w-3/4 ml-auto" />
              <Skeleton className="h-24 w-3/4" />
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-slate-400 my-auto">
              <div className="w-12 h-12 rounded-2xl bg-indigo-950/80 text-indigo-400 border border-indigo-500/30 flex items-center justify-center mb-3">
                <Sparkles className="w-6 h-6" />
              </div>
              <h3 className="text-base font-bold text-white font-outfit">
                Grounded Hybrid RAG Assistant
              </h3>
              <p className="text-xs text-slate-400 max-w-md mt-1">
                Ask questions about documents in your active workspace. Answers will be synthesized strictly with inline citations.
              </p>
            </div>
          ) : (
            <>
              {/* Existing Message History */}
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shrink-0 shadow-md">
                      <Sparkles className="w-4 h-4 text-white" />
                    </div>
                  )}

                  <div
                    className={`p-4 rounded-2xl max-w-2xl text-sm leading-relaxed ${
                      msg.role === "user"
                        ? "bg-indigo-600/90 text-white rounded-tr-none shadow-md"
                        : "bg-slate-900/80 border border-slate-800 text-slate-200 rounded-tl-none space-y-3"
                    }`}
                  >
                    <p>{msg.content}</p>

                    {/* Citations List if present */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800">
                        {msg.citations.map((c: any, cIdx: number) => (
                          <button
                            key={cIdx}
                            onClick={() => setSelectedCitation(c as Citation)}
                            className="inline-flex items-center gap-1 bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 border border-indigo-500/40 text-[11px] font-semibold px-2 py-0.5 rounded-full transition-all"
                          >
                            <FileText className="w-3 h-3 text-indigo-400" />
                            <span>
                              [^{cIdx + 1}] {c.document_name || "Source"}
                              {c.page_numbers && c.page_numbers.length > 0
                                ? `: p.${c.page_numbers.join(", ")}`
                                : ""}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Streaming Active Chunk */}
              {isStreaming && (
                <div className="flex gap-3 justify-start">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-tr from-indigo-600 to-purple-600 flex items-center justify-center shrink-0 shadow-md animate-pulse">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="bg-slate-900/80 border border-slate-800 p-4 rounded-2xl rounded-tl-none max-w-2xl text-sm text-slate-200 leading-relaxed space-y-3">
                    <p>
                      {currentStreamContent}
                      <span className="inline-block w-2 h-4 bg-indigo-400 ml-1 animate-pulse" />
                    </p>

                    {currentCitations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2 border-t border-slate-800">
                        {currentCitations.map((c, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => setSelectedCitation(c)}
                            className="inline-flex items-center gap-1 bg-indigo-950/80 hover:bg-indigo-900 text-indigo-300 border border-indigo-500/40 text-[11px] font-semibold px-2 py-0.5 rounded-full transition-all"
                          >
                            <FileText className="w-3 h-3 text-indigo-400" />
                            <span>
                              [^{cIdx + 1}] {c.document_name}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-4 bg-slate-900/90 border-t border-slate-800 flex items-center gap-3">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={
              activeWorkspaceId
                ? "Ask anything about documents in this workspace..."
                : "Please select a workspace in top header first..."
            }
            disabled={!activeWorkspaceId || isStreaming}
            className="flex-1 bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          />

          {isStreaming ? (
            <Button
              type="button"
              variant="danger"
              onClick={stopStream}
              leftIcon={<Square className="w-4 h-4 fill-white" />}
            >
              Stop
            </Button>
          ) : (
            <Button
              type="submit"
              disabled={!inputQuery.trim() || !activeWorkspaceId}
              leftIcon={<Send className="w-4 h-4" />}
            >
              Send Query
            </Button>
          )}
        </form>
      </div>

      {/* Citation Detail Modal Drawer */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-sm p-4">
          <div className="glass-panel max-w-lg w-full rounded-2xl p-6 border border-slate-800 bg-slate-950 shadow-2xl">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-indigo-400" />
                <h3 className="text-sm font-bold text-white font-outfit">
                  {selectedCitation.document_name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {selectedCitation.page_numbers && selectedCitation.page_numbers.length > 0 && (
              <Badge variant="purple" size="sm" className="mb-3">
                Page {selectedCitation.page_numbers.join(", ")}
              </Badge>
            )}

            <div className="mt-3">
              <p className="text-xs text-slate-400 mb-1 font-semibold uppercase">Source Excerpt:</p>
              <div className="bg-slate-900 p-3.5 rounded-xl border border-slate-800 text-xs text-slate-200 italic leading-relaxed">
                &quot;{selectedCitation.content_excerpt}&quot;
              </div>
            </div>

            <div className="mt-6 flex justify-end">
              <Button size="sm" variant="secondary" onClick={() => setSelectedCitation(null)}>
                Close Preview
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
