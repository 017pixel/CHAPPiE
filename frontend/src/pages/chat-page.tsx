import { FormEvent, useEffect, useState, useRef, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";

import { parseEmotionalText } from "../lib/format";
import { api } from "../services/api";
import { useUiStore } from "../store/ui";

type ChatMessage = {
  id?: string;
  role: string;
  content: string;
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
  "Hmm, warte, ich überlege noch...",
  "Habs gleich, versprochen!",
  "Gib mir noch einen Moment...",
  "Ich durchforste mein Langzeitgedächtnis...",
  "Das ist eine interessante Frage...",
  "Ich analysiere die emotionalen Nuancen...",
  "Fast fertig mit der Verarbeitung...",
  "Bereite die Antwort vor...",
  "Einen kleinen Moment noch...",
  "Ich sortiere gerade meine Gedanken...",
  "Die Antwort formt sich...",
];

export function ChatPage() {
  const currentSessionId = useUiStore((state) => state.currentSessionId);
  const setCurrentSessionId = useUiStore((state) => state.setCurrentSessionId);
  const [message, setMessage] = useState("");
  const [commandsExpanded, setCommandsExpanded] = useState(false);
  const [queue, setQueue] = useState<QueuedMessage[]>([]);
  const [processingState, setProcessingState] = useState<ProcessingState>("idle");
  const [streamingContent, setStreamingContent] = useState("");
  const [thinkingIndex, setThinkingIndex] = useState(0);
  const [serverMessages, setServerMessages] = useState<ChatMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: api.getSessions });
  const activeSessionQuery = useQuery({ queryKey: ["active-session"], queryFn: api.getActiveSession });
  const sessionQuery = useQuery({
    queryKey: ["session", currentSessionId],
    queryFn: () => api.getSession(currentSessionId!),
    enabled: Boolean(currentSessionId)
  });
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.getStatus });

  // Sync server messages (only when idle)
  useEffect(() => {
    if (processingState !== "idle") return;
    const msgs = (sessionQuery.data as SessionDetail | undefined)?.messages ?? [];
    setServerMessages(msgs);
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
  }, [serverMessages, streamingContent, thinkingIndex]);

  // Thinking animation
  useEffect(() => {
    if (processingState !== "thinking") return;
    const interval = setInterval(() => {
      setThinkingIndex(i => (i + 1) % THINKING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [processingState]);

  // Auto-send from queue when idle
  const sendNextFromQueue = useCallback(() => {
    setQueue(prev => {
      if (prev.length === 0) return prev;
      const [next, ...rest] = prev;
      // Use setTimeout to avoid state update during render
      setTimeout(() => {
        processMessage(next.text);
      }, 300);
      return rest;
    });
  }, []);

  useEffect(() => {
    if (processingState === "idle" && queue.length > 0) {
      sendNextFromQueue();
    }
  }, [processingState, queue.length, sendNextFromQueue]);

  async function processMessage(text: string) {
    if (!text.trim() || processingState !== "idle") return;

    // Abort any previous stream
    if (abortRef.current) {
      abortRef.current.abort();
    }

    const abortController = new AbortController();
    abortRef.current = abortController;

    // Add user message to server messages immediately
    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
    };
    setServerMessages(prev => [...prev, userMsg]);
    setStreamingContent("");
    setThinkingIndex(0);
    setProcessingState("thinking");

    try {
      const stream = api.sendMessageStream({
        session_id: currentSessionId,
        message: text,
        debug_mode: false,
        command_mode: text.trim().startsWith("/"),
      });

      let accumulatedContent = "";
      let receivedAnyToken = false;

      for await (const event of stream) {
        if (abortController.signal.aborted) break;

        if (event.event === "token") {
          if (!receivedAnyToken) {
            receivedAnyToken = true;
            setProcessingState("streaming");
          }
          accumulatedContent += event.data.content || "";
          setStreamingContent(accumulatedContent);
        } else if (event.event === "turn_error") {
          accumulatedContent += "\n[Fehler: " + (event.data.error || "Unbekannter Fehler") + "]";
          setStreamingContent(accumulatedContent);
          setProcessingState("error");
          break;
        } else if (event.event === "turn_finished") {
          break;
        }
      }

      if (!abortController.signal.aborted) {
        // If we received tokens, add the streamed message to server messages
        if (receivedAnyToken && accumulatedContent.trim()) {
          setServerMessages(prev => [...prev, {
            id: `assistant-${Date.now()}`,
            role: "assistant",
            content: accumulatedContent,
          }]);
        }
        setProcessingState("idle");
        setStreamingContent("");
        sessionQuery.refetch();
        statusQuery.refetch();
      }
    } catch (err) {
      if (abortController.signal.aborted) return;
      setServerMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Fehler: ${(err as Error).message}`,
      }]);
      setProcessingState("error");
    } finally {
      if (!abortController.signal.aborted) {
        setProcessingState("idle");
        setStreamingContent("");
      }
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (!message.trim() || processingState !== "idle") return;

    if (processingState !== "idle") {
      // Queue the message
      setQueue(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text: message }]);
      setMessage("");
      return;
    }

    const textToSend = message;
    setMessage("");
    processMessage(textToSend);
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!message.trim()) return;

      if (processingState !== "idle") {
        setQueue(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text: message }]);
        setMessage("");
        return;
      }

      const textToSend = message;
      setMessage("");
      processMessage(textToSend);
    }
  }

  function removeFromQueue(id: string) {
    setQueue(prev => prev.filter(q => q.id !== id));
  }

  const status = (statusQuery.data ?? {}) as StatusSnapshot;
  const allCommands = ["/sleep", "/stats", "/help", "/clear", "/deep think 10", "/life", "/plan", "/debug", "/growth"];
  const visibleCommands = commandsExpanded ? allCommands : allCommands.slice(0, 4);

  // Build display messages
  let displayMessages = [...serverMessages];
  if (processingState === "thinking") {
    displayMessages = [...displayMessages, {
      id: "thinking",
      role: "assistant",
      content: THINKING_MESSAGES[thinkingIndex],
    }];
  } else if (processingState === "streaming") {
    displayMessages = [...displayMessages, {
      id: "streaming",
      role: "assistant",
      content: streamingContent,
    }];
  }

  const isInputDisabled = processingState !== "idle";

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
        {displayMessages.length === 0 ? (
          <div className="flex h-full items-center justify-center text-slate">
            <div className="text-center">
              <span className="material-symbols-outlined text-4xl opacity-20 transition-transform duration-700 hover:scale-110">bubble_chart</span>
              <p className="mt-4 text-sm tracking-widest uppercase opacity-40">Waiting for interaction...</p>
            </div>
          </div>
        ) : (
          displayMessages.map((entry, idx) => (
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
            placeholder={isInputDisabled ? "CHAPPiE antwortet gerade..." : "Write a message or use /commands..."}
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
