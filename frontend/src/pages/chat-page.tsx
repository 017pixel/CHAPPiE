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

  // Sync display messages from server, filtering out pending messages
  useEffect(() => {
    if (processingState !== "idle") return;
    const rawMessages = (sessionQuery.data as SessionDetail | undefined)?.messages ?? [];
    const cleanMessages = rawMessages.filter(msg => !isPending(msg) && !msg.content.startsWith("_CHAPPiE"));
    setDisplayMessages(cleanMessages);
  }, [sessionQuery.data, processingState]);

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
    setThinkingIndex(0);
    setProcessingState("thinking");

    let usedStream = false;
    let streamedContent = "";

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
          streamedContent += event.data.content || "";
          setStreamingContent(streamedContent);
          // Also update display messages with streaming content
          setDisplayMessages(prev => {
            const updated = [...prev];
            // Remove any existing assistant message at the end that's a placeholder
            while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "streaming" || updated[updated.length - 1].id === "thinking")) {
              updated.pop();
            }
            updated.push({ id: "streaming", role: "assistant", content: streamedContent });
            return updated;
          });
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
          if (finalContent) {
            setDisplayMessages(prev => {
              const updated = [...prev];
              while (updated.length > 0 && updated[updated.length - 1].role === "assistant" && (updated[updated.length - 1].id === "streaming" || updated[updated.length - 1].id === "thinking")) {
                updated.pop();
              }
              updated.push({ id: `assistant-${Date.now()}`, role: "assistant", content: finalContent });
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
      // Refetch server data to ensure consistency
      sessionQuery.refetch();
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
  }

  const isProcessing = processingRef.current;

  return (
    <div className="flex h-[calc(100vh-10rem)] flex-col gap-6">
      {/* Header Info Card */}
      <div className="flex shrink-0 items-center justify-between rounded-none border border-white/5 bg-night p-6 shadow-glass">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat & Intelligence</h1>
          <div className="mt-2 flex gap-4 text-[10px] uppercase tracking-widest text-slate">
            <span>Model: <span className="text-ember">{status.model ?? "Loading..."}</span></span>
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
              className={`flex flex-col ${entry.role === "assistant" ? "items-start" : "items-end"}`}
            >
              <div
                className={`max-w-[85%] rounded-none px-6 py-4 shadow-glass transition-all duration-300 border-2 ${
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
                ) : (
                  <div
                    className="text-sm leading-relaxed"
                    dangerouslySetInnerHTML={{ __html: parseEmotionalText(entry.content).replace(/\n/g, "<br/>") }}
                  />
                )}
              </div>
            </div>
          ))
        )}
      </div>

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