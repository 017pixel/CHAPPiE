import { FormEvent, useEffect, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";

import { parseEmotionalText } from "../lib/format";
import { api } from "../services/api";
import { useUiStore } from "../store/ui";

type ChatMessage = {
  id?: string;
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
};

type SessionDetail = {
  messages: ChatMessage[];
};

type StatusSnapshot = {
  model?: string;
  provider?: string;
  emotions?: Record<string, number>;
};

type QueuedMessage = {
  id: string;
  text: string;
};

type ProcessingState = "idle" | "thinking" | "streaming" | "error";

const THINKING_MESSAGES = [
  "CHAPPiE denkt nach...",
  "Hmm, warte, ich ueberlege noch...",
  "Habs gleich, versprochen!",
  "Gib mir noch einen Moment...",
  "Ich durchforste mein Langzeitgedaechtnis...",
  "Das ist eine interessante Frage...",
  "Ich analysiere die emotionalen Nuancen...",
  "Fast fertig mit der Verarbeitung...",
  "Bereite die Antwort vor...",
  "Einen kleinen Moment noch...",
  "Ich sortiere gerade meine Gedanken...",
  "Die Antwort formt sich...",
];

function isPending(msg: ChatMessage): boolean {
  return msg.metadata?.pending === true;
}

export function ChatPage() {
  const currentSessionId = useUiStore((state) => state.currentSessionId);
  const setCurrentSessionId = useUiStore((state) => state.setCurrentSessionId);
  const [message, setMessage] = useState("");
  const [commandsExpanded, setCommandsExpanded] = useState(false);
  const [queue, setQueue] = useState<QueuedMessage[]>([]);
  const [processingState, setProcessingState] = useState<ProcessingState>("idle");
  const [streamingContent, setStreamingContent] = useState("");
  const [thinkingIndex, setThinkingIndex] = useState(0);
  const [displayMessages, setDisplayMessages] = useState<ChatMessage[]>([]);
  const [reasoningContent, setReasoningContent] = useState("");
  const [loadedOnce, setLoadedOnce] = useState(false);
  const [popupMsg, setPopupMsg] = useState<ChatMessage | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const processingRef = useRef(false);

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: api.getSessions });
  const activeSessionQuery = useQuery({ queryKey: ["active-session"], queryFn: api.getActiveSession });
  const sessionQuery = useQuery({
    queryKey: ["session", currentSessionId],
    queryFn: () => api.getSession(currentSessionId!),
    enabled: Boolean(currentSessionId)
  });
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.getStatus });

  // Sync display messages from server only on initial load
  useEffect(() => {
    if (processingState !== "idle") return;
    if (loadedOnce) return;
    const rawMessages = (sessionQuery.data as SessionDetail | undefined)?.messages ?? [];
    if (rawMessages.length === 0) return;
    const cleanMessages = rawMessages.filter(msg => !isPending(msg) && !msg.content.startsWith("_CHAPPiE"));
    if (cleanMessages.length > 0) {
      setDisplayMessages(cleanMessages);
      setLoadedOnce(true);
    }
  }, [sessionQuery.data, processingState, loadedOnce]);

  // Initialize session
  useEffect(() => {
    if (!currentSessionId && (activeSessionQuery.data as any)?.id) {
      setCurrentSessionId((activeSessionQuery.data as any).id);
      return;
    }
    if (!currentSessionId && Array.isArray(sessionsQuery.data) && sessionsQuery.data[0]?.id) {
      setCurrentSessionId(sessionsQuery.data[0].id);
    }
  }, [activeSessionQuery.data, currentSessionId, sessionsQuery.data, setCurrentSessionId]);

  // Reset loadedOnce when session changes
  useEffect(() => {
    setLoadedOnce(false);
  }, [currentSessionId]);

  // Auto-scroll
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [displayMessages, streamingContent, thinkingIndex]);

  // Thinking animation
  useEffect(() => {
    if (processingState !== "thinking") return;
    const interval = setInterval(() => {
      setThinkingIndex(i => (i + 1) % THINKING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [processingState]);

  // Auto-send from queue when idle
  useEffect(() => {
    if (processingState !== "idle" || queue.length === 0) return;

    const next = queue[0];
    setQueue(prev => prev.slice(1));

    const timer = setTimeout(() => {
      processMessage(next.text);
    }, 300);

    return () => clearTimeout(timer);
  }, [processingState, queue.length]);

  async function sendMessage(text: string) {
    if (!text.trim()) return;

    if (processingRef.current) {
      setQueue(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text }]);
      setMessage("");
      return;
    }

    await processMessage(text);
  }

  async function processMessage(text: string) {
    if (!text.trim() || processingRef.current) return;

    processingRef.current = true;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };

    setDisplayMessages(prev => [...prev, userMsg]);
    setMessage("");
    setStreamingContent("");
    setReasoningContent("");
    setThinkingIndex(0);
    setProcessingState("thinking");

    let usedStream = false;
    let streamedContent = "";
    let streamedReasoning = "";

    // Try streaming first
    try {
      const stream = api.sendMessageStream({
        session_id: currentSessionId,
        message: text,
        debug_mode: false,
        command_mode: text.trim().startsWith("/"),
      });

      usedStream = true;

      for await (const event of stream) {
        if (event.event === "token") {
          if (processingState === "thinking") {
            setProcessingState("streaming");
          }
          const tokenType = event.data.token_type || "answer";
          if (tokenType === "reasoning") {
            streamedReasoning += event.data.content || "";
            setReasoningContent(streamedReasoning);
          } else {
            streamedContent += event.data.content || "";
            setStreamingContent(streamedContent);
            setDisplayMessages(prev => {
              const updated = [...prev];
              while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "streaming" || updated[updated.length - 1].id === "thinking")) {
                updated.pop();
              }
              updated.push({ id: "streaming", role: "assistant", content: streamedContent });
              return updated;
            });
          }
        } else if (event.event === "turn_error") {
          streamedContent += "\n[Fehler: " + (event.data.error || "Unbekannter Fehler") + "]";
          setDisplayMessages(prev => {
            const updated = [...prev];
            while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "streaming" || updated[updated.length - 1].id === "thinking")) {
              updated.pop();
            }
            updated.push({ id: `error-${Date.now()}`, role: "assistant", content: streamedContent });
            return updated;
          });
          break;
        } else if (event.event === "turn_finished") {
          const finalContent = streamedContent || event.data?.assistant_message?.content || "";
          const finalReasoning = streamedReasoning;
          const finalMeta = event.data?.assistant_message?.metadata || {};
          if (finalContent) {
            setDisplayMessages(prev => {
              const updated = [...prev];
              while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "streaming" || updated[updated.length - 1].id === "thinking")) {
                updated.pop();
              }
              updated.push({ id: `assistant-${Date.now()}`, role: "assistant", content: finalContent, metadata: { ...finalMeta, reasoning: finalReasoning || undefined } });
              return updated;
            });
          }
          break;
        }
      }
    } catch (streamErr) {
      // Streaming failed, fall back to synchronous endpoint
      console.warn("Streaming failed, falling back to synchronous endpoint:", streamErr);

      // Remove the thinking placeholder
      setDisplayMessages(prev => {
        const updated = [...prev];
        while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "thinking")) {
          updated.pop();
        }
        return updated;
      });

      try {
        const result = await api.sendMessage({
          session_id: currentSessionId,
          message: text,
          debug_mode: false,
          command_mode: text.trim().startsWith("/"),
        }) as any;

        const assistantContent = result?.assistant_message?.content || result?.response_text || "Keine Antwort erhalten.";
        const sessionId = result?.session_id || result?.replacement_session_id;
        if (sessionId && sessionId !== currentSessionId) {
          setCurrentSessionId(sessionId);
        }

        setDisplayMessages(prev => [...prev, {
          id: `assistant-${Date.now()}`,
          role: "assistant",
          content: assistantContent,
        }]);
      } catch (syncErr: any) {
        setDisplayMessages(prev => [...prev, {
          id: `error-${Date.now()}`,
          role: "assistant",
          content: `Fehler: ${syncErr.message || "Unbekannter Fehler"}`,
        }]);
      }
    } finally {
      processingRef.current = false;
      setProcessingState("idle");
      setStreamingContent("");
      setReasoningContent("");
      statusQuery.refetch();
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim()) return;
    sendMessage(message);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!message.trim()) return;
      sendMessage(message);
    }
  }

  function removeFromQueue(id: string) {
    setQueue(prev => prev.filter(q => q.id !== id));
  }

  const status = (statusQuery.data ?? {}) as StatusSnapshot;
  const allCommands = ["/sleep", "/stats", "/help", "/clear", "/deep think 10", "/life", "/plan", "/debug", "/growth"];
  const visibleCommands = commandsExpanded ? allCommands : allCommands.slice(0, 4);

  // Build final display messages: add thinking/streaming overlay
  let finalMessages = [...displayMessages];
  if (processingState === "thinking") {
    finalMessages = [...finalMessages, {
      id: "thinking",
      role: "assistant",
      content: THINKING_MESSAGES[thinkingIndex],
    }];
  } else if (processingState === "streaming") {
    // Streaming messages are already in displayMessages, don't double-add
    // Add a reasoning entry if reasoning content is live
    if (reasoningContent) {
      finalMessages = [...finalMessages, {
        id: "reasoning-live",
        role: "assistant",
        content: reasoningContent,
        metadata: { isReasoning: true },
      }];
    }
  }

  const isProcessing = processingRef.current;
  const hasLiveReasoning = processingState === "streaming" && reasoningContent;

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col gap-6">
      {/* Header Info Card */}
      <div className="flex shrink-0 items-center justify-between rounded-none border border-white/5 bg-night p-6 shadow-glass">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat & Intelligence</h1>
          <div className="mt-2 flex gap-4 text-[10px] uppercase tracking-widest text-slate">
            <span>Model: <span className="text-ember">{status.model ?? "Loading..."}</span></span>
            <span>via: <span className="text-mist">{status.provider ?? "---"}</span></span>
            <span>Status: <span className="text-green-500">Active</span></span>
          </div>
        </div>
        <div className="flex gap-2">
          {Object.entries(status.emotions ?? {}).map(([key, value]) => (
            <div key={key} className="flex flex-col items-center rounded-none bg-white/5 px-3 py-1.5 min-w-[60px] border border-white/5">
              <span className="text-[10px] text-slate uppercase">{key}</span>
              <span className="text-xs font-bold text-mist">{value}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Messages Area */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto rounded-none border border-white/5 bg-white/[0.02] p-8 space-y-6 scroll-smooth shadow-inner"
      >
        {finalMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-slate">
            <div className="text-center">
              <span className="material-symbols-outlined text-4xl opacity-20 transition-transform duration-700 hover:scale-110">bubble_chart</span>
              <p className="mt-4 text-sm tracking-widest uppercase opacity-40">Waiting for interaction...</p>
            </div>
          </div>
        ) : (
          finalMessages.map((entry, idx) => (
            <div
              key={entry.id ?? idx}
              className={`flex flex-col gap-2 ${entry.role === "assistant" ? "items-start" : "items-end"}`}
            >
              {/* Reasoning box for assistant messages that have it */}
              {(entry.role === "assistant" && (entry.metadata as any)?.reasoning) && (
                <div className="max-w-[85%] rounded-none border border-white/5 bg-white/[0.04] px-5 py-3">
                  <p className="mb-1.5 text-[10px] uppercase tracking-widest text-slate">Reasoning</p>
                  <div className="text-xs leading-relaxed whitespace-pre-wrap text-slate/70">{(entry.metadata as any).reasoning}</div>
                </div>
              )}
              <div className="flex items-start gap-2 max-w-[85%]">
                <div
                  className={`flex-1 rounded-none px-6 py-4 shadow-glass transition-all duration-300 border-2 ${
                    entry.role === "assistant"
                      ? "bg-night border-white/10 text-mist"
                      : "bg-ember border-ember/20 text-white"
                  } ${entry.id === "thinking" ? "animate-pulse opacity-70" : ""}`}
                >
                  <p className="mb-2 text-[10px] uppercase tracking-widest opacity-50">{entry.role}</p>
                  {entry.id === "streaming" ? (
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {entry.content}
                    </div>
                  ) : entry.id === "reasoning-live" ? (
                    <div className="text-xs leading-relaxed whitespace-pre-wrap text-slate/70">{entry.content}</div>
                  ) : (
                    <div
                      className="text-sm leading-relaxed"
                      dangerouslySetInnerHTML={{ __html: parseEmotionalText(entry.content).replace(/\n/g, "<br/>") }}
                    />
                  )}
                </div>
                {/* Info Button */}
                {entry.role === "assistant" && !["streaming", "thinking", "reasoning-live"].includes(entry.id || "") && entry.metadata && (
                  <div className="relative group shrink-0">
                    <button
                      onClick={() => setPopupMsg(entry)}
                      className="flex h-7 w-7 items-center justify-center rounded-none border border-white/10 bg-white/5 text-[10px] text-slate transition-all hover:bg-ember hover:text-white hover:border-ember/30"
                      title="Details anzeigen"
                    >
                      i
                    </button>
                    {/* Hover-Preview */}
                    <div className="pointer-events-none absolute left-0 bottom-full mb-1 z-50 hidden group-hover:block">
                      <div className="rounded-none border border-white/10 bg-night/95 p-3 shadow-glass w-64">
                        <p className="mb-1.5 text-[9px] uppercase tracking-widest text-ember">Preview</p>
                        {(() => {
                          const meta = entry.metadata as any;
                          const memories = meta.rag_memories || [];
                          const topMem = memories.slice(0, 3);
                          const deltas = meta.emotions_delta || {};
                          const deltaKeys = Object.keys(deltas).filter(k => deltas[k]?.change !== 0);
                          const previewLines: string[] = [];
                          if (memories.length > 0) previewLines.push(`${memories.length} LTM-Erinnerungen (top: ${topMem.length > 0 ? Math.round((topMem[0].relevance_score || 0) * 100) : 0}% Relevanz)`);
                          if (deltaKeys.length > 0) previewLines.push(`Emotionen: ${deltaKeys.slice(0, 2).map(k => `${k} ${deltas[k]?.change > 0 ? "+" : ""}${deltas[k]?.change}`).join(", ")}`);
                          previewLines.push(`Intent: ${meta.intent_type || "casual_chat"}`);
                          if (meta.processing_time_ms) previewLines.push(`Dauer: ${(meta.processing_time_ms / 1000).toFixed(1)}s`);
                          previewLines.push(`Provider: ${meta.provider || "---"} / ${meta.model || "---"}`);
                          return previewLines.slice(0, 5).map((line, i) => (
                            <div key={i} className="text-[10px] leading-relaxed text-slate/60">- {line}</div>
                          ));
                        })()}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>

      {/* Info Popup Modal */}
      {popupMsg && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm" onClick={() => setPopupMsg(null)}>
          <div className="max-h-[80vh] w-[560px] overflow-y-auto rounded-none border border-white/10 bg-night p-6 shadow-glass" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-bold uppercase tracking-widest text-mist">Verarbeitungsdetails</h2>
              <button onClick={() => setPopupMsg(null)} className="text-slate hover:text-white transition-colors">
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>
            {(() => {
              const meta = (popupMsg.metadata || {}) as any;
              const memories = meta.rag_memories || [];
              const deltas = meta.emotions_delta || {};
              const before = meta.emotions_before || {};
              const steering = meta.emotion_steering || {};
              const trace = meta.memory_trace || {};
              const causal = meta.causal_trace || [];
              return (
                <div className="space-y-4 text-xs text-slate">
                  {/* Langzeitgedächtnis */}
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-ember mb-2">Langzeitgedächtnis-Erinnerungen ({memories.length})</p>
                    {memories.length === 0 ? (
                      <p className="text-slate/50 italic">Keine relevanten Erinnerungen gefunden</p>
                    ) : (
                      <div className="space-y-2 max-h-[200px] overflow-y-auto">
                        {memories.map((mem: any, i: number) => (
                          <div key={i} className="border-l-2 border-white/10 pl-3">
                            <div className="flex gap-2 items-baseline">
                              <span className="text-[9px] uppercase text-slate/40">{mem.role}</span>
                              <span className="text-[9px] text-ember font-bold">{Math.round((mem.relevance_score || 0) * 100)}%</span>
                              <span className="text-[9px] text-slate/30">{mem.label}</span>
                            </div>
                            <div className="text-[10px] leading-relaxed text-slate/70 mt-0.5 line-clamp-2">{mem.content}</div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {/* Emotion-Deltas */}
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-ember mb-2">Emotionen vorher → nachher</p>
                    {Object.keys(deltas).length === 0 ? (
                      <p className="text-slate/50 italic">Keine Änderungen</p>
                    ) : (
                      <div className="grid grid-cols-4 gap-1.5">
                        {Object.entries(deltas).map(([key, val]: [string, any]) => {
                          const change = val?.change || 0;
                          const color = change > 0 ? "text-green-400" : change < 0 ? "text-red-400" : "text-slate/50";
                          return (
                            <div key={key} className="border border-white/5 bg-white/[0.02] px-2 py-1.5 text-center">
                              <div className="text-[9px] uppercase text-slate/40">{key}</div>
                              <div className="text-[11px]">
                                <span className="text-slate/60">{val?.before ?? (before[key] ?? "?")}</span>
                                <span className="mx-1 text-slate/30">→</span>
                                <span className="text-slate/70">{val?.after ?? (before[key] ?? "?")}</span>
                                <span className={`ml-1 ${color}`}>{change > 0 ? "+" : ""}{change}</span>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    )}
                  </div>

                  {/* Steering Info */}
                  {steering.steering_active && (
                    <div>
                      <p className="text-[10px] uppercase tracking-widest text-ember mb-2">Emotion-Steering aktiv</p>
                      <div className="grid grid-cols-2 gap-1.5">
                        <div className="text-[10px] text-slate/50">Dominant: <span className="text-slate/70">{steering.dominant_vector}</span></div>
                        <div className="text-[10px] text-slate/50">Stärke: <span className="text-slate/70">{steering.dominant_strength}</span></div>
                        <div className="text-[10px] text-slate/50">Mode: <span className="text-slate/70">{steering.summary}</span></div>
                        <div className="text-[10px] text-slate/50">Vektoren: <span className="text-slate/70">{steering.active_vectors?.length || 0}</span></div>
                      </div>
                    </div>
                  )}

                  {/* Allgemein */}
                  <div>
                    <p className="text-[10px] uppercase tracking-widest text-ember mb-2">Allgemein</p>
                    <div className="grid grid-cols-2 gap-1.5">
                      <div className="text-[10px] text-slate/50">Intent: <span className="text-slate/70">{meta.intent_type || "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Confidence: <span className="text-slate/70">{meta.intent_confidence != null ? Math.round(meta.intent_confidence * 100) + "%" : "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Provider: <span className="text-slate/70">{meta.provider || "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Modell: <span className="text-slate/70">{meta.model || "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Dauer: <span className="text-slate/70">{meta.processing_time_ms ? (meta.processing_time_ms / 1000).toFixed(1) + "s" : "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Tone: <span className="text-slate/70">{meta.tone_decision?.tone || "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Short-Term: <span className="text-slate/70">{meta.short_term_count ?? "?"}</span></div>
                      <div className="text-[10px] text-slate/50">Tool Calls: <span className="text-slate/70">{meta.tool_calls_executed ?? "0"}</span></div>
                    </div>
                  </div>
                </div>
              );
            })()}
          </div>
        </div>
      )}

      {/* Input Section */}
      <div className="shrink-0 space-y-4">
        {/* Message Queue */}
        {queue.length > 0 && (
          <div className="flex flex-wrap gap-2">
            {queue.map((item) => (
              <div
                key={item.id}
                className="flex items-center gap-2 rounded-none bg-ember/10 border border-ember/20 px-3 py-1.5 text-xs text-mist max-w-[280px]"
              >
                <span className="truncate">{item.text}</span>
                <button
                  type="button"
                  onClick={() => removeFromQueue(item.id)}
                  className="text-slate hover:text-white transition-colors flex-shrink-0"
                >
                  <span className="material-symbols-outlined text-sm leading-none">close</span>
                </button>
              </div>
            ))}
          </div>
        )}

        <div className={`flex flex-wrap gap-2 transition-all duration-500`}>
          {visibleCommands.map((command) => (
            <button
              key={command}
              type="button"
              onClick={() => setMessage(command)}
              className="rounded-none bg-white/5 border border-white/5 px-4 py-2 text-xs text-slate transition-all hover:bg-ember hover:text-white"
            >
              {command}
            </button>
          ))}
          <button
            type="button"
            onClick={() => setCommandsExpanded(!commandsExpanded)}
            className={`rounded-none px-4 py-2 text-xs transition-all ${commandsExpanded ? "bg-ember text-white" : "bg-white/5 text-slate hover:bg-white/10"}`}
          >
            <span className="material-symbols-outlined text-sm leading-none">{commandsExpanded ? "close" : "more_horiz"}</span>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="relative">
          <textarea
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={isProcessing ? "CHAPPiE antwortet gerade..." : "Write a message or use /commands..."}
            className="w-full rounded-none border border-white/10 bg-input p-5 pr-32 text-sm text-mist shadow-glass outline-none transition-all placeholder:text-slate focus:border-ember focus:ring-1 focus:ring-ember/20"
            rows={2}
          />
          <button
            type="submit"
            disabled={!message.trim()}
            className="absolute right-3 bottom-3 rounded-none bg-ember px-6 py-2.5 text-sm font-bold text-white shadow-lg transition-all hover:scale-105 active:scale-95 disabled:opacity-30 disabled:grayscale disabled:hover:scale-100"
          >
            Send
          </button>
        </form>
      </div>
    </div>
  );
}