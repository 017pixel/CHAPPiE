import { FormEvent, useEffect, useState, useRef } from "react";
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
  const [isProcessing, setIsProcessing] = useState(false);
  const [streamingContent, setStreamingContent] = useState("");
  const [thinkingIndex, setThinkingIndex] = useState(0);
  const [localMessages, setLocalMessages] = useState<ChatMessage[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const processingLock = useRef(false);

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: api.getSessions });
  const activeSessionQuery = useQuery({ queryKey: ["active-session"], queryFn: api.getActiveSession });
  const sessionQuery = useQuery({
    queryKey: ["session", currentSessionId],
    queryFn: () => api.getSession(currentSessionId!),
    enabled: Boolean(currentSessionId)
  });
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.getStatus });

  // Sync local messages with server data (only when not actively processing)
  useEffect(() => {
    if (isProcessing) return;
    const serverMessages = (sessionQuery.data as SessionDetail | undefined)?.messages ?? [];
    setLocalMessages(serverMessages);
  }, [sessionQuery.data, isProcessing]);

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

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [localMessages, streamingContent, thinkingIndex]);

  // Thinking animation - cycles every 2.5s while processing but no tokens yet
  useEffect(() => {
    if (!isProcessing || streamingContent) return;
    const interval = setInterval(() => {
      setThinkingIndex(i => (i + 1) % THINKING_MESSAGES.length);
    }, 2500);
    return () => clearInterval(interval);
  }, [isProcessing, streamingContent]);

  // Auto-send from queue when processing completes
  useEffect(() => {
    if (isProcessing || queue.length === 0 || processingLock.current) return;

    const next = queue[0];
    setQueue(prev => prev.slice(1));
    processingLock.current = true;

    const timer = setTimeout(() => {
      processingLock.current = false;
      sendMessage(next.text);
    }, 400);

    return () => clearTimeout(timer);
  }, [isProcessing, queue]);

  async function sendMessage(text: string) {
    if (!text.trim()) return;

    if (isProcessing) {
      setQueue(prev => [...prev, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text }]);
      setMessage("");
      return;
    }

    const userMsg: ChatMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: text,
    };

    setLocalMessages(prev => [...prev, userMsg]);
    setMessage("");
    setIsProcessing(true);
    setStreamingContent("");
    setThinkingIndex(0);

    try {
      const stream = api.sendMessageStream({
        session_id: currentSessionId,
        message: text,
        debug_mode: false,
        command_mode: text.trim().startsWith("/"),
      });

      let assistantContent = "";

      for await (const event of stream) {
        if (event.event === "token") {
          assistantContent += event.data.content || "";
          setStreamingContent(assistantContent);
        } else if (event.event === "turn_error") {
          assistantContent += "\n[Fehler: " + (event.data.error || "Unbekannter Fehler") + "]";
          setStreamingContent(assistantContent);
        } else if (event.event === "turn_finished") {
          break;
        }
      }
    } catch (err) {
      setLocalMessages(prev => [...prev, {
        id: `error-${Date.now()}`,
        role: "assistant",
        content: `Fehler: ${(err as Error).message}`,
      }]);
    } finally {
      setIsProcessing(false);
      setStreamingContent("");
      sessionQuery.refetch();
      statusQuery.refetch();
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    sendMessage(message);
  }

  function removeFromQueue(id: string) {
    setQueue(prev => prev.filter(q => q.id !== id));
  }

  const status = (statusQuery.data ?? {}) as StatusSnapshot;
  const allCommands = ["/sleep", "/stats", "/help", "/clear", "/deep think 10", "/life", "/plan", "/debug", "/growth"];
  const visibleCommands = commandsExpanded ? allCommands : allCommands.slice(0, 4);

  // Build display messages: server messages + streaming/thinking overlay
  let displayMessages = [...localMessages];
  if (isProcessing) {
    if (streamingContent) {
      displayMessages = [...displayMessages, {
        id: "streaming",
        role: "assistant",
        content: streamingContent,
      }];
    } else {
      displayMessages = [...displayMessages, {
        id: "thinking",
        role: "assistant",
        content: THINKING_MESSAGES[thinkingIndex],
      }];
    }
  }

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
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage(message);
              }
            }}
            placeholder="Write a message or use /commands..."
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
