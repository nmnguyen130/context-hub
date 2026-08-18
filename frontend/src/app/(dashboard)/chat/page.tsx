"use client";

import { useState, useEffect, useRef } from "react";
import {
  Send,
  Plus,
  FileText,
  Square,
  X,
  MessageSquareText,
  ShieldCheck,
  ChevronDown,
  ChevronUp,
  Sparkles,
  SlidersHorizontal,
} from "lucide-react";
import { useWorkspaceStore } from "@/store/workspace-store";
import { useChatStore } from "@/store/chat-store";
import {
  useChatSessions,
  useChatMessages,
  useCreateChatSession,
  useSendChatMessage,
} from "@/features/chat/hooks/use-chat";
import { useWorkspaces } from "@/features/workspace/hooks/use-workspaces";
import { Citation } from "@/types";
import { Button } from "@/components/ui/button";

export default function ChatPage() {
  const [inputQuery, setInputQuery] = useState("");
  const [showControls, setShowControls] = useState(false);
  const [retrievalPolicy, setRetrievalPolicy] = useState("balanced");
  const [scopeAll, setScopeAll] = useState(false);

  const { activeWorkspaceId } = useWorkspaceStore();
  const { data: workspacesData } = useWorkspaces();
  const activeWorkspace = workspacesData?.items.find((w) => w.id === activeWorkspaceId);

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
    await sendMessage(targetSessionId, activeWorkspaceId, query, {
      retrieval_policy: retrievalPolicy,
      scope: scopeAll ? "all" : "workspace",
    });
  };

  return (
    <div className="h-[calc(100vh-6.5rem)] flex gap-4 max-w-7xl mx-auto">
      {/* Session History Sidebar (Desktop) */}
      <div className="w-60 bg-surface rounded-lg p-3 border border-stroke flex flex-col justify-between hidden md:flex shrink-0">
        <div>
          <div className="flex items-center justify-between mb-3 px-1">
            <span className="text-[11px] font-mono text-muted uppercase">
              Chat History
            </span>
            <button
              onClick={handleStartNewSession}
              disabled={!activeWorkspaceId}
              className="p-1 rounded bg-surface-elevated hover:bg-surface-hover text-muted hover:text-accent border border-stroke transition-colors cursor-pointer"
              title="New Session"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>

          <div className="space-y-1 overflow-y-auto max-h-[calc(100vh-14rem)] pr-1">
            {loadingSessions ? (
              <div className="space-y-2">
                <div className="h-8 rounded bg-surface-elevated animate-pulse"></div>
                <div className="h-8 rounded bg-surface-elevated animate-pulse"></div>
              </div>
            ) : sessions.length === 0 ? (
              <p className="text-xs text-muted text-center py-6">No previous chat sessions.</p>
            ) : (
              sessions.map((s) => {
                const isSelected = activeSessionId === s.id;
                return (
                  <button
                    key={s.id}
                    onClick={() => setActiveSessionId(s.id)}
                    className={`w-full flex items-center gap-2 p-2 rounded-md text-xs transition-colors text-left truncate cursor-pointer ${
                      isSelected
                        ? "bg-surface-elevated text-accent border border-stroke font-semibold"
                        : "text-muted hover:bg-surface-elevated/60 hover:text-primary"
                    }`}
                  >
                    <MessageSquareText className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">{s.title || "Untitled Conversation"}</span>
                  </button>
                );
              })
            )}
          </div>
        </div>

        <div className="pt-2 border-t border-stroke text-[10px] font-mono text-muted flex items-center gap-1">
          <ShieldCheck className="w-3 h-3 text-success" />
          <span className="truncate">ACL Verified Grounding</span>
        </div>
      </div>

      {/* Main Conversational Window */}
      <div className="flex-1 bg-surface rounded-lg border border-stroke flex flex-col justify-between overflow-hidden">
        {/* Top Scope & Collapsible Retrieval Controls Header */}
        <div className="border-b border-stroke bg-surface-dark p-3 text-xs space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <span className="font-semibold text-primary">
                {activeWorkspace ? `Grounded in ${activeWorkspace.name}` : "Select a Workspace above"}
              </span>
              <span className="text-[10px] font-mono text-muted">
                · Policy: {retrievalPolicy.toUpperCase()}
              </span>
            </div>

            <button
              onClick={() => setShowControls(!showControls)}
              className="inline-flex items-center gap-1 text-[11px] text-muted hover:text-primary cursor-pointer"
            >
              <SlidersHorizontal className="w-3 h-3" />
              <span>{showControls ? "Hide Controls" : "Retrieval Policy"}</span>
              {showControls ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
            </button>
          </div>

          {/* Collapsible Retrieval Policy Bar */}
          {showControls && (
            <div className="pt-2 border-t border-stroke grid grid-cols-1 sm:grid-cols-2 gap-3 text-[11px]">
              <div>
                <label className="text-muted block mb-1">Retrieval Policy</label>
                <select
                  value={retrievalPolicy}
                  onChange={(e) => setRetrievalPolicy(e.target.value)}
                  className="w-full p-1.5 rounded bg-surface-elevated border border-stroke text-primary text-xs"
                >
                  <option value="balanced">Balanced (Hybrid Search + RRF)</option>
                  <option value="fast">Fast (Low latency dense search)</option>
                  <option value="quality">Exhaustive (Deep cross-document context)</option>
                </select>
              </div>

              <div>
                <label className="text-muted block mb-1">Knowledge Scope</label>
                <select
                  value={scopeAll ? "all" : "workspace"}
                  onChange={(e) => setScopeAll(e.target.value === "all")}
                  className="w-full p-1.5 rounded bg-surface-elevated border border-stroke text-primary text-xs"
                >
                  <option value="workspace">Active Workspace Only (Strict Boundary)</option>
                  <option value="all">All Accessible Workspaces</option>
                </select>
              </div>
            </div>
          )}
        </div>

        {/* Messages Scroll Area */}
        <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-4">
          {loadingMessages ? (
            <div className="space-y-3">
              <div className="h-14 w-2/3 ml-auto rounded-lg bg-surface-elevated animate-pulse"></div>
              <div className="h-20 w-3/4 rounded-lg bg-surface-elevated animate-pulse"></div>
            </div>
          ) : messages.length === 0 && !isStreaming ? (
            <div className="h-full flex flex-col items-center justify-center text-center text-muted my-auto space-y-2 py-12">
              <div className="w-10 h-10 rounded-md bg-surface-elevated border border-stroke flex items-center justify-center text-accent mx-auto">
                <Sparkles className="w-5 h-5" />
              </div>
              <h3 className="text-sm font-bold text-primary font-heading">Grounded Knowledge Assistant</h3>
              <p className="text-xs max-w-sm">
                Ask questions about documents in this workspace. Answers are strictly synthesized with verified inline citations.
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex gap-3 ${msg.role === "user" ? "justify-end" : "justify-start"}`}
                >
                  <div
                    className={`p-3.5 rounded-lg max-w-2xl text-xs leading-relaxed ${
                      msg.role === "user"
                        ? "bg-accent text-white rounded-tr-none"
                        : "bg-surface-dark border border-stroke text-primary rounded-tl-none space-y-2"
                    }`}
                  >
                    <p className="whitespace-pre-wrap">{msg.content}</p>

                    {/* Citations */}
                    {msg.citations && msg.citations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2 border-t border-stroke">
                        {msg.citations.map((c: any, cIdx: number) => (
                          <button
                            key={cIdx}
                            onClick={() => setSelectedCitation(c as Citation)}
                            className="inline-flex items-center gap-1 bg-surface hover:bg-surface-elevated text-accent border border-accent/40 text-[10px] font-mono px-2 py-0.5 rounded transition-colors cursor-pointer"
                          >
                            <FileText className="w-3 h-3" />
                            <span>
                              [^{cIdx + 1}] {c.document_name || "Source"}
                              {c.page_numbers?.length ? `: p.${c.page_numbers.join(",")}` : ""}
                            </span>
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {/* Streaming Output */}
              {isStreaming && (
                <div className="flex gap-3 justify-start">
                  <div className="bg-surface-dark border border-stroke p-3.5 rounded-lg rounded-tl-none max-w-2xl text-xs text-primary space-y-2">
                    <p className="whitespace-pre-wrap">
                      {currentStreamContent}
                      <span className="inline-block w-1.5 h-3.5 bg-accent ml-1 animate-pulse" />
                    </p>

                    {currentCitations.length > 0 && (
                      <div className="flex flex-wrap gap-1.5 pt-2 border-t border-stroke">
                        {currentCitations.map((c, cIdx) => (
                          <button
                            key={cIdx}
                            onClick={() => setSelectedCitation(c)}
                            className="inline-flex items-center gap-1 bg-surface text-accent border border-accent/40 text-[10px] font-mono px-2 py-0.5 rounded cursor-pointer"
                          >
                            <FileText className="w-3 h-3" />
                            <span>[^{cIdx + 1}] {c.document_name}</span>
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
        <form onSubmit={handleSend} className="p-3 bg-surface-dark border-t border-stroke flex items-center gap-2">
          <input
            type="text"
            value={inputQuery}
            onChange={(e) => setInputQuery(e.target.value)}
            placeholder={
              activeWorkspaceId
                ? "Ask a question about documents in this workspace..."
                : "Select a workspace above to begin..."
            }
            disabled={!activeWorkspaceId || isStreaming}
            className="flex-1 bg-surface border border-stroke rounded-md px-3 py-2.5 text-xs text-primary placeholder:text-muted focus:outline-none focus:border-accent"
          />

          {isStreaming ? (
            <Button
              type="button"
              variant="danger"
              size="sm"
              onClick={stopStream}
              leftIcon={<Square className="w-3.5 h-3.5 fill-white" />}
            >
              Stop
            </Button>
          ) : (
            <Button
              type="submit"
              size="sm"
              disabled={!inputQuery.trim() || !activeWorkspaceId}
              className="bg-accent hover:bg-accent-hover text-white"
              leftIcon={<Send className="w-3.5 h-3.5" />}
            >
              Send
            </Button>
          )}
        </form>
      </div>

      {/* Citation Inspector Drawer Modal */}
      {selectedCitation && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-xs p-4">
          <div className="surface-card max-w-lg w-full p-5 bg-surface border border-stroke rounded-xl space-y-3">
            <div className="flex items-center justify-between border-b border-stroke pb-2">
              <div className="flex items-center gap-2 text-xs font-bold text-primary font-heading">
                <FileText className="w-3.5 h-3.5 text-accent" />
                <span>Citation Inspector: {selectedCitation.document_name}</span>
              </div>
              <button
                onClick={() => setSelectedCitation(null)}
                className="text-muted hover:text-primary text-xs cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="flex items-center justify-between text-[11px]">
              <span className="font-mono text-muted">
                {selectedCitation.page_numbers?.length ? `Page ${selectedCitation.page_numbers.join(", ")}` : "Full Document"}
              </span>
              <span className="text-success font-mono text-[10px] flex items-center gap-1">
                <ShieldCheck className="w-3 h-3" /> Server-Verified ACL
              </span>
            </div>

            <div className="space-y-1 text-left">
              <span className="text-[10px] font-mono text-muted uppercase">Matched Source Text Excerpt:</span>
              <div className="p-3 rounded bg-surface-dark border border-stroke font-mono text-[11px] text-secondary leading-relaxed">
                &quot;{selectedCitation.content_excerpt}&quot;
              </div>
            </div>

            <div className="flex justify-end pt-2 border-t border-stroke">
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
