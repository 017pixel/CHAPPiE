import { FormEvent, KeyboardEvent as ReactKeyboardEvent, useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { estimateTextTokens, formatTokenRate } from "../lib/telemetry";
import { MarkdownText } from "../lib/markdown";
import { api } from "../services/api";
import { isSlashCommand } from "../store/ui";
import type { ChatMessage, LivePipelineState } from "../store/ui";
import { useUiStore } from "../store/ui";

type SessionDetail = {
  messages: ChatMessage[];
};

type StatusSnapshot = {
  model?: string;
  provider?: string;
  emotions?: Record<string, number>;
  routing?: string;
};

type QueuedMessage = {
  id: string;
  text: string;
};

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {};
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}

function optionalNumber(value: unknown): number | undefined {
  const parsed = typeof value === "number" ? value : Number(value);
  return Number.isFinite(parsed) ? parsed : undefined;
}

const THINKING_MESSAGES = [
  "CHAPPiE denkt nach...",
  "Kontext wird geladen...",
  "Emotionale Nuancen werden geprüft...",
  "Die Antwort formt sich...",
  "Fast fertig mit der Verarbeitung...",
];

const EMOTION_NAMES = [
  "happiness",
  "trust",
  "energy",
  "curiosity",
  "frustration",
  "motivation",
  "sadness",
  "affection",
  "anxiety",
  "calm",
] as const;

const ALL_COMMANDS = ["/sleep", "/stats", "/help", "/clear", "/new", "/emotion", "/deep think 10", "/life", "/plan", "/debug", "/growth"];

function isPending(message: ChatMessage): boolean {
  return message.metadata?.pending === true;
}

function metadataOf(message: ChatMessage): Record<string, any> {
  return (message.metadata ?? {}) as Record<string, any>;
}

function withDisplayMetadata(message: ChatMessage, previous?: ChatMessage): ChatMessage {
  const metadata = metadataOf(message);
  const command = message.role === "user" && (metadata.is_command === true || metadata.message_kind === "command" || isSlashCommand(message.content));
  const system = message.role === "system" || metadata.is_system === true || metadata.is_system_response === true || metadata.message_kind === "system" || (message.role === "assistant" && previous?.role === "user" && isSlashCommand(previous.content));
  const formatted = message.role === "assistant" ? metadata.formatted_answer : undefined;
  if (!command && !system && !formatted) return message;

  const commandText = command ? message.content.trim() : system && previous?.role === "user" ? previous.content.trim() : metadata.command;
  return {
    ...message,
    content: formatted || message.content,
    metadata: {
      ...metadata,
      ...(command ? { is_command: true, message_kind: "command", command: commandText } : {}),
      ...(system ? { is_system: true, is_system_response: true, message_kind: "system", command: commandText } : {}),
      ...(formatted && !metadata.raw_response ? { raw_response: message.content } : {}),
    },
  };
}

function formatDuration(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "—";
  return numeric < 1000 ? `${Math.round(numeric)}ms` : `${(numeric / 1000).toFixed(2)}s`;
}

function NumberedText({ content, className = "" }: { content: string; className?: string }) {
  const lines = content.split("\n");
  return <div className={className}>{lines.map((line, index) => <div key={`${index}-${line.slice(0, 12)}`} className="flex min-w-0"><span className="mr-2 w-5 shrink-0 select-none text-right text-[9px] text-slate/25">{String(index + 1).padStart(2, "0")}</span><span className="min-w-0 whitespace-pre-wrap break-words">{line || " "}</span></div>)}</div>;
}

function hasError(message: ChatMessage): boolean {
  const meta = metadataOf(message);
  return Boolean(meta.stream_error || meta.error_message || meta.generation_failed || /^fehler[:\s]/i.test(message.content) || /^(?:vllm|ollama|groq|steering-server)\b[^\n]{0,120}\b(?:error|failed|failure|fehler|fehlgeschlagen)\b/i.test(message.content));
}

function TerminalEntry({ message, thinkingEnabled, onSelectTrace }: { message: ChatMessage; thinkingEnabled: boolean; onSelectTrace: (message: ChatMessage) => void }) {
  const meta = metadataOf(message);
  const isReasoning = message.id === "reasoning-live" || Boolean(meta.isReasoning);
  const isThinking = message.id === "thinking";
  const isStreaming = message.id === "streaming";
  const isLive = isReasoning || isThinking || isStreaming;
  const isCommand = message.role === "user" && (meta.is_command === true || meta.message_kind === "command" || isSlashCommand(message.content));
  const isSystem = message.role === "system" || meta.message_kind === "system" || meta.is_system === true || meta.is_system_response === true;
  const cot = meta.formatted_cot || meta.reasoning || "";
  const rawOutput = !isSystem && typeof meta.raw_response === "string" && meta.raw_response.trim() ? meta.raw_response : "";
  const visibleOutput = message.content || rawOutput;
  const error = meta.error_message || (meta.stream_error ? "Stream wurde beendet." : "");
  const timing = (meta.timing ?? {}) as Record<string, any>;

  if (message.role === "user") {
    return <article className={`terminal-log-entry ${isCommand ? "terminal-command-entry" : "terminal-user-entry"}`} data-message-kind={isCommand ? "command" : "input"}><div className="terminal-prompt-line"><span className={isCommand ? "text-terminal-amber" : "text-[#8aa8bd]"}>{isCommand ? "Command" : "Input"}</span><span className="ml-2 min-w-0 break-words text-mist [overflow-wrap:anywhere]">{message.content}</span></div></article>;
  }

  return <article className={`terminal-log-entry ${isSystem ? "terminal-system-entry" : "terminal-assistant-entry"} ${hasError(message) ? "has-error" : ""}`} data-message-kind={isSystem ? "system" : "output"}>
    <div className="terminal-prompt-line mb-1"><span className={hasError(message) ? "text-terminal-red" : isSystem ? "text-terminal-amber" : "text-terminal-green"}>{isSystem ? "System" : "Output"}</span><span className="ml-2 text-slate/45">{isReasoning ? "reasoning" : isThinking ? "processing" : isSystem ? String(meta.command || "command result") : "model response"}</span>{!isLive && <button type="button" className="ml-auto text-[9px] uppercase tracking-widest text-slate/35 hover:text-terminal-green" onClick={() => onSelectTrace(message)}>inspect</button>}</div>
    {error && <div className="terminal-error-line mb-2 border-l-2 border-terminal-red bg-terminal-red/[0.08] px-2 py-1 text-[10px] text-terminal-red">[ERR] {error}</div>}
    {isReasoning ? <details open className="terminal-reasoning"><summary className="cursor-pointer list-none text-[10px] uppercase tracking-widest text-terminal-green">▶ reasoning / CoT — live</summary><NumberedText content={message.content} className="mt-2 text-[10px] leading-relaxed text-slate/60" /></details> : isThinking ? <div className="text-[11px] text-terminal-green/75"><span className="terminal-cursor mr-1">▌</span>{message.content}<span className="ml-2 text-[9px] text-slate/35">{formatDuration(meta.timer_ms)}</span></div> : <>
      {thinkingEnabled && cot && <details className="terminal-reasoning mb-2"><summary className="cursor-pointer list-none text-[10px] uppercase tracking-widest text-terminal-green">▶ reasoning / CoT</summary><NumberedText content={String(cot).length > 4000 ? `${String(cot).slice(0, 4000)}\n... (truncated)` : String(cot)} className={`mt-2 text-[10px] leading-relaxed ${hasError(message) ? "text-terminal-red/70" : "text-slate/55"}`} /></details>}
      {!isSystem && rawOutput && rawOutput !== visibleOutput && <details className="mb-2 text-[9px] text-slate/45"><summary className="cursor-pointer uppercase tracking-widest hover:text-slate/70">raw model output</summary><NumberedText content={rawOutput} className="mt-1 text-[10px] leading-relaxed text-slate/50" /></details>}
      {isSystem ? <NumberedText content={visibleOutput} className={`terminal-output ${hasError(message) ? "text-terminal-red/80" : "text-mist/85"}`} /> : <MarkdownText content={visibleOutput} className={`terminal-output ${hasError(message) ? "text-terminal-red/80" : "text-mist/85"}`} />}
      {!isSystem && (isLive || timing.ttft_ms != null || timing.answer_tokens != null || meta.provider) && <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[9px] uppercase tracking-widest text-slate/35"><span>ttft {formatDuration(timing.ttft_ms)}</span><span>{timing.answer_tokens ?? meta.live_pipeline?.answer_tokens ?? "—"} tk</span><span>{formatTokenRate(timing, meta, message.content)}</span><span>{meta.provider ?? "provider —"}</span></div>}
    </>}
    {isStreaming && <span className="terminal-cursor ml-7 text-terminal-green">▌</span>}
  </article>;
}

export function ChatPage() {
  const currentSessionId = useUiStore((state) => state.currentSessionId);
  const setCurrentSessionId = useUiStore((state) => state.setCurrentSessionId);
  const processingState = useUiStore((state) => state.processingState);
  const setProcessingState = useUiStore((state) => state.setProcessingState);
  const streamingContent = useUiStore((state) => state.streamingContent);
  const setStreamingContent = useUiStore((state) => state.setStreamingContent);
  const reasoningContent = useUiStore((state) => state.reasoningContent);
  const setReasoningContent = useUiStore((state) => state.setReasoningContent);
  const displayMessages = useUiStore((state) => state.displayMessages);
  const setDisplayMessages = useUiStore((state) => state.setDisplayMessages);
  const isProcessing = useUiStore((state) => state.isProcessing);
  const setIsProcessing = useUiStore((state) => state.setIsProcessing);
  const genStartTime = useUiStore((state) => state.genStartTime);
  const setGenStartTime = useUiStore((state) => state.setGenStartTime);
  const elapsedMs = useUiStore((state) => state.elapsedMs);
  const setElapsedMs = useUiStore((state) => state.setElapsedMs);
  const loadedOnce = useUiStore((state) => state.loadedOnce);
  const setLoadedOnce = useUiStore((state) => state.setLoadedOnce);
  const thinkingEnabled = useUiStore((state) => state.thinkingEnabled);
  const setThinkingEnabled = useUiStore((state) => state.setThinkingEnabled);
  const setActiveTraceId = useUiStore((state) => state.setActiveTraceId);
  const setStreamError = useUiStore((state) => state.setStreamError);
  const setLivePipeline = useUiStore((state) => state.setLivePipeline);
  const resetStreamingState = useUiStore((state) => state.resetStreamingState);

  const [message, setMessage] = useState("");
  const [commandsExpanded, setCommandsExpanded] = useState(false);
  const [queue, setQueue] = useState<QueuedMessage[]>([]);
  const [thinkingIndex, setThinkingIndex] = useState(0);
  const [showEmotionPopup, setShowEmotionPopup] = useState(false);
  const [thinkingSaving, setThinkingSaving] = useState(false);
  const [historyIndex, setHistoryIndex] = useState(-1);
  const scrollRef = useRef<HTMLDivElement>(null);
  const emotionPopupRef = useRef<HTMLDivElement>(null);
  const autoScrollRef = useRef(true);
  const processingRef = useRef(false);
  const lastUserMessageRef = useRef("");
  const retryRef = useRef<() => void>(() => undefined);

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: api.getSessions });
  const activeSessionQuery = useQuery({ queryKey: ["active-session"], queryFn: api.getActiveSession });
  const sessionQuery = useQuery({ queryKey: ["session", currentSessionId], queryFn: () => api.getSession(currentSessionId!), enabled: Boolean(currentSessionId) });
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.getStatus, refetchInterval: 3000 });
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.getSettings });
  const status = (statusQuery.data ?? {}) as StatusSnapshot;

  useEffect(() => {
    const settings = (settingsQuery.data ?? {}) as Record<string, any>;
    if (settings.chain_of_thought !== undefined) setThinkingEnabled(Boolean(settings.chain_of_thought));
  }, [settingsQuery.data, setThinkingEnabled]);

  useEffect(() => {
    const storeState = useUiStore.getState();
    if (storeState.processingState !== "idle") {
      setLoadedOnce(true);
      processingRef.current = storeState.isProcessing;
      return;
    }
    if (storeState.loadedOnce) return;
    const rawMessages = (sessionQuery.data as SessionDetail | undefined)?.messages ?? [];
    const cleanMessages = rawMessages.filter((item) => !isPending(item) && !item.content.startsWith("_CHAPPiE"));
    const normalizedMessages = cleanMessages.map((item, index) => withDisplayMetadata(item, cleanMessages[index - 1]));
    if (normalizedMessages.length > 0) {
      setDisplayMessages(normalizedMessages);
      setLoadedOnce(true);
    }
  }, [sessionQuery.data, setDisplayMessages, setLoadedOnce]);

  useEffect(() => {
    if (!currentSessionId && (activeSessionQuery.data as any)?.id) setCurrentSessionId((activeSessionQuery.data as any).id);
    else if (!currentSessionId && Array.isArray(sessionsQuery.data) && (sessionsQuery.data as any[])[0]?.id) setCurrentSessionId((sessionsQuery.data as any[])[0].id);
  }, [activeSessionQuery.data, currentSessionId, sessionsQuery.data, setCurrentSessionId]);

  useEffect(() => {
    setLoadedOnce(false);
  }, [currentSessionId, setLoadedOnce]);

  useEffect(() => {
    const element = scrollRef.current;
    if (!element) return;
    const onScroll = () => { autoScrollRef.current = element.scrollHeight - element.scrollTop - element.clientHeight < 60; };
    element.addEventListener("scroll", onScroll, { passive: true });
    return () => element.removeEventListener("scroll", onScroll);
  }, []);

  useEffect(() => {
    if (autoScrollRef.current && scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [displayMessages, streamingContent, reasoningContent, thinkingIndex]);

  useEffect(() => {
    if (processingState !== "thinking") return;
    const interval = window.setInterval(() => setThinkingIndex((index) => (index + 1) % THINKING_MESSAGES.length), 2200);
    return () => window.clearInterval(interval);
  }, [processingState]);

  useEffect(() => {
    if (processingState !== "thinking" && processingState !== "streaming") {
      setElapsedMs(0);
      return;
    }
    const interval = window.setInterval(() => {
      const start = useUiStore.getState().genStartTime;
      const now = Date.now();
      if (start) {
        const elapsed = now - start;
        setElapsedMs(elapsed);
        setLivePipeline((previous) => previous ? { ...previous, elapsed_ms: elapsed, updated_at: now } : previous);
      }
    }, 100);
    return () => window.clearInterval(interval);
  }, [processingState, setElapsedMs, setLivePipeline]);

  useEffect(() => {
    const onRetry = () => retryRef.current();
    window.addEventListener("chappie:retry-last", onRetry);
    return () => window.removeEventListener("chappie:retry-last", onRetry);
  }, []);

  useEffect(() => {
    const trimmed = message.trimStart();
    setShowEmotionPopup(trimmed.startsWith("/emotion") && !/^\/emotion\s+\w+\s+[+-]?\d+/.test(trimmed));
  }, [message]);

  useEffect(() => {
    if (!showEmotionPopup) return;
    const onClick = (event: MouseEvent) => { if (emotionPopupRef.current && !emotionPopupRef.current.contains(event.target as Node)) setShowEmotionPopup(false); };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, [showEmotionPopup]);

  useEffect(() => {
    if (processingState !== "idle" || queue.length === 0) return;
    const next = queue[0];
    setQueue((items) => items.slice(1));
    const timeout = window.setTimeout(() => { void processMessage(next.text); }, 300);
    return () => window.clearTimeout(timeout);
  }, [processingState, queue.length]);

  function replaceLiveMessage(content: string, metadata: Record<string, any> = {}) {
    const commandText = isSlashCommand(lastUserMessageRef.current) ? lastUserMessageRef.current.trim() : "";
    setDisplayMessages((previous) => {
      const withoutLive = previous.filter((item) => item.id !== "streaming" && item.id !== "thinking");
      return [...withoutLive, { id: "streaming", role: "assistant", content, metadata: { ...metadata, ...(commandText ? { is_system: true, is_system_response: true, message_kind: "system", command: commandText } : {}), live: true } }];
    });
  }

  function commitAssistant(content: string, metadata: Record<string, any>, replacementSessionId?: string) {
    const assistantId = `assistant-${Date.now()}`;
    const commandText = isSlashCommand(lastUserMessageRef.current) ? lastUserMessageRef.current.trim() : "";
    const displayMetadata = commandText ? { ...metadata, is_system: true, is_system_response: true, message_kind: "system", command: commandText } : metadata;
    if (replacementSessionId && replacementSessionId !== currentSessionId) setCurrentSessionId(replacementSessionId);
    setDisplayMessages((previous) => {
      const withoutLive = previous.filter((item) => item.id !== "streaming" && item.id !== "thinking");
      return [...withoutLive, { id: assistantId, role: "assistant", content, metadata: displayMetadata }];
    });
    setActiveTraceId(assistantId);
  }

  async function processMessage(text: string) {
    if (!text.trim() || processingRef.current) return;
    processingRef.current = true;
    lastUserMessageRef.current = text;
    setIsProcessing(true);
    setStreamError(null);
    const isClearCommand = ["/clear", "/new"].includes(text.trim().toLowerCase());
    if (isClearCommand) {
      setDisplayMessages([]);
      setQueue([]);
    }
    const commandText = isSlashCommand(text) ? text.trim() : "";
    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text,
      ...(commandText ? { metadata: { is_command: true, message_kind: "command", command: commandText } } : {}),
    };
    setDisplayMessages((previous) => [...previous, userMessage]);
    // Keep the inspector on the live pipeline from the first processing frame.
    // The final assistant id replaces this when turn_finished arrives.
    setActiveTraceId("streaming");
    setMessage("");
    setHistoryIndex(-1);
    setStreamingContent("");
    setReasoningContent("");
    setThinkingIndex(0);
    setGenStartTime(Date.now());
    setLivePipeline({
      stage: "intent",
      stage_key: "intent",
      step: 1,
      status_text: "Intent-Analyse gestartet",
      started_at: Date.now(),
      updated_at: Date.now(),
      elapsed_ms: 0,
      provider: status.provider,
      model: status.model,
    });
    setProcessingState("thinking");
    autoScrollRef.current = true;

    let streamedContent = "";
    let streamedReasoning = "";
    let finished = false;

    try {
      const stream = api.sendMessageStream({ session_id: currentSessionId, message: text, debug_mode: true, command_mode: text.trim().startsWith("/") });
      for await (const event of stream) {
        if (event.event === "status") {
          const rawData = asRecord(event.data);
          const data = rawData as Partial<LivePipelineState>;
          const now = Date.now();
          setLivePipeline((previous) => {
            const startedAt = previous?.started_at ?? useUiStore.getState().genStartTime ?? now;
            return {
              ...(previous ?? {}),
              stage: data.stage ?? data.stage_key ?? previous?.stage ?? "intent",
              stage_key: data.stage_key ?? data.stage ?? previous?.stage_key ?? "intent",
              status_text: data.status_text ?? optionalString(rawData.status) ?? previous?.status_text,
              started_at: startedAt,
              updated_at: now,
              elapsed_ms: data.elapsed_ms ?? now - startedAt,
              provider: data.provider ?? previous?.provider ?? status.provider,
              model: data.model ?? previous?.model ?? status.model,
            };
          });
          const stage = String(data.stage ?? data.stage_key ?? "").toLowerCase();
          if (stage === "streaming" && useUiStore.getState().processingState === "thinking") setProcessingState("streaming");
        } else if (event.event === "token") {
          const data = asRecord(event.data);
          if (useUiStore.getState().processingState === "thinking") setProcessingState("streaming");
          const content = optionalString(data.content) ?? "";
          if ((optionalString(data.token_type) ?? "answer") === "reasoning") {
            streamedReasoning += content;
            setReasoningContent(streamedReasoning.length > 3000 ? `${streamedReasoning.slice(0, 3000)}...` : streamedReasoning);
          } else {
            streamedContent += content;
            setStreamingContent(streamedContent);
            const now = Date.now();
            setLivePipeline((previous) => {
              const startedAt = previous?.started_at ?? useUiStore.getState().genStartTime ?? now;
              const elapsed = Math.max(0, now - startedAt);
              const answerTokens = estimateTextTokens(streamedContent);
              return {
                ...(previous ?? {}),
                stage: "streaming",
                stage_key: "streaming",
                status_text: "Antwort wird gestreamt",
                updated_at: now,
                elapsed_ms: elapsed,
                token_count: answerTokens,
                answer_tokens: answerTokens,
                answer_time_ms: elapsed,
                tokens_per_second: elapsed > 0 ? answerTokens / (elapsed / 1000) : 0,
                provider: previous?.provider ?? status.provider,
                model: previous?.model ?? status.model,
              };
            });
            const livePipeline = useUiStore.getState().livePipeline;
            replaceLiveMessage(streamedContent, {
              provider: livePipeline?.provider ?? status.provider,
              model: livePipeline?.model ?? status.model,
              live_pipeline: livePipeline,
              timing: {
                answer_tokens: livePipeline?.answer_tokens ?? estimateTextTokens(streamedContent),
                answer_time_ms: livePipeline?.answer_time_ms ?? 0,
                tokens_per_second: livePipeline?.tokens_per_second ?? 0,
              },
            });
          }
        } else if (event.event === "turn_error") {
          const data = asRecord(event.data);
          const errorText = optionalString(data.error) ?? "Unbekannter Fehler";
          setStreamError(errorText);
          setLivePipeline((previous) => ({ ...(previous ?? {}), stage: "done", stage_key: "done", status_text: "Antwort fehlgeschlagen", error: errorText, updated_at: Date.now() }));
          commitAssistant(streamedContent || `[Fehler: ${errorText}]`, { stream_error: true, error_message: errorText, raw_response: streamedContent });
          finished = true;
          break;
        } else if (event.event === "turn_finished") {
          const data = asRecord(event.data);
          const assistantMessage = asRecord(data.assistant_message);
          const finalContent = streamedContent || optionalString(assistantMessage.content) || "";
          const finalMeta = asRecord(assistantMessage.metadata);
          const displayContent = optionalString(finalMeta.formatted_answer) || finalContent;
          const finalTiming = asRecord(finalMeta.timing);
          setLivePipeline((previous) => ({
            ...(previous ?? {}),
            stage: "done",
            stage_key: "done",
            status_text: "Turn abgeschlossen",
            updated_at: Date.now(),
            elapsed_ms: Number(finalTiming.total_gen_ms) || previous?.elapsed_ms,
            answer_tokens: Number(finalTiming.answer_tokens) || previous?.answer_tokens,
            ttft_ms: optionalNumber(finalTiming.ttft_ms) ?? previous?.ttft_ms,
            answer_time_ms: optionalNumber(finalTiming.answer_time_ms) ?? previous?.answer_time_ms,
            total_gen_ms: optionalNumber(finalTiming.total_gen_ms) ?? previous?.total_gen_ms,
            tokens_per_second: optionalNumber(finalTiming.tokens_per_second) ?? previous?.tokens_per_second,
            provider: optionalString(finalMeta.provider) ?? previous?.provider ?? status.provider,
            model: optionalString(finalMeta.model) ?? previous?.model ?? status.model,
          }));
          const mergedMeta = { ...finalMeta, reasoning: streamedReasoning || undefined, formatted_cot: optionalString(finalMeta.formatted_cot), raw_response: optionalString(finalMeta.raw_response) || finalContent || undefined };
          commitAssistant(displayContent || finalContent, mergedMeta, optionalString(data.session_id));
          finished = true;
          break;
        }
      }
      if (!finished && (streamedContent || streamedReasoning)) {
        const errorText = "Stream beendet, bevor turn_finished empfangen wurde.";
        setStreamError(errorText);
        commitAssistant(streamedContent || `[Fehler: ${errorText}]`, { stream_error: true, error_message: errorText, raw_response: streamedContent });
      }
    } catch {
      setDisplayMessages((previous) => previous.filter((item) => item.id !== "streaming" && item.id !== "thinking"));
      try {
        const result = await api.sendMessage({ session_id: currentSessionId, message: text, debug_mode: true, command_mode: text.trim().startsWith("/") });
        const content = result?.assistant_message?.content || result?.response_text || "Keine Antwort erhalten.";
        const metadata = result?.assistant_message?.metadata || result?.metadata || {};
        commitAssistant(optionalString(metadata.formatted_answer) || content, { ...metadata, raw_response: optionalString(metadata.raw_response) || content }, result?.session_id || result?.replacement_session_id);
      } catch (error: unknown) {
        const errorText = error instanceof Error ? error.message : "Unbekannter Fehler";
        setStreamError(errorText);
        commitAssistant(`Fehler: ${errorText}`, { stream_error: true, error_message: errorText });
      }
    } finally {
      processingRef.current = false;
      resetStreamingState();
      void statusQuery.refetch();
    }
  }

  retryRef.current = () => {
    if (!processingRef.current && lastUserMessageRef.current) void processMessage(lastUserMessageRef.current);
  };

  function sendMessage(text: string) {
    if (!text.trim()) return;
    if (processingRef.current) {
      setQueue((items) => [...items, { id: `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`, text }]);
      setMessage("");
      return;
    }
    void processMessage(text);
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    sendMessage(message);
  }

  function handleKeyDown(event: ReactKeyboardEvent<HTMLTextAreaElement>) {
    const history = displayMessages.filter((item) => item.role === "user").map((item) => item.content);
    if (event.key === "ArrowUp" && (message.trim() === "" || message.startsWith("/"))) {
      event.preventDefault();
      if (history.length === 0) return;
      const nextIndex = historyIndex < 0 ? history.length - 1 : Math.max(0, historyIndex - 1);
      setHistoryIndex(nextIndex);
      setMessage(history[nextIndex]);
    } else if (event.key === "ArrowDown" && historyIndex >= 0) {
      event.preventDefault();
      const nextIndex = historyIndex + 1;
      if (nextIndex >= history.length) { setHistoryIndex(-1); setMessage(""); } else { setHistoryIndex(nextIndex); setMessage(history[nextIndex]); }
    } else if (event.key === "Tab" && message.trim().startsWith("/")) {
      const match = ALL_COMMANDS.find((command) => command.startsWith(message.trim().toLowerCase()));
      if (match) { event.preventDefault(); setMessage(match); }
    } else if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault(); sendMessage(message);
    }
  }

  const visibleCommands = commandsExpanded ? ALL_COMMANDS : ALL_COMMANDS.slice(0, 4);
  const finalMessages: ChatMessage[] = [...displayMessages];
  if (processingState === "thinking") finalMessages.push({ id: "thinking", role: "assistant", content: THINKING_MESSAGES[thinkingIndex], metadata: { timer_ms: elapsedMs } });
  if (processingState === "streaming" && reasoningContent) finalMessages.push({ id: "reasoning-live", role: "assistant", content: reasoningContent, metadata: { isReasoning: true } });

  function selectTrace(entry: ChatMessage) {
    setActiveTraceId(entry.id ?? null);
  }

  async function toggleThinking() {
    if (thinkingSaving) return;
    const next = !thinkingEnabled;
    setThinkingEnabled(next);
    setThinkingSaving(true);
    try {
      const saved = await api.saveSettings({ chain_of_thought: next }) as Record<string, unknown>;
      setThinkingEnabled(Boolean(saved.chain_of_thought));
    } catch (error: any) {
      setThinkingEnabled(!next);
      setStreamError(error?.message || "Chain of Thought konnte nicht gespeichert werden.");
    } finally {
      setThinkingSaving(false);
    }
  }

  return <div className="terminal-chat flex h-full min-h-0 flex-col bg-ink">
    <div className="terminal-session-bar flex shrink-0 items-center justify-between gap-3 border-b border-white/10 px-3 py-2"><span className="font-semibold text-[10px] uppercase tracking-[0.28em] text-mist">CHAPPiE</span><button type="button" onClick={() => void toggleThinking()} disabled={thinkingSaving} aria-pressed={thinkingEnabled} className={`terminal-toggle min-h-9 px-3 text-[10px] ${thinkingEnabled ? "is-active" : ""}`} title="Chain of Thought ein- oder ausblenden">{thinkingSaving ? "saving" : thinkingEnabled ? "CoT on" : "CoT off"}</button></div>
    <div ref={scrollRef} className="terminal-log min-h-0 flex-1 overflow-y-auto px-3 py-4 lg:px-5" aria-live="polite">
      {finalMessages.length === 0 ? <div className="flex min-h-full items-center justify-center"><div className="w-full max-w-[34rem] border-l-2 border-terminal-green/35 pl-3 text-[11px] leading-relaxed text-slate/45"><div className="text-terminal-green">User _</div><p className="mt-2">No traces yet. Send a message or run a command to start the workspace.</p><p className="mt-1 text-slate/30">Try /help · /stats · /debug</p></div></div> : <div className="space-y-5">{finalMessages.map((entry, index) => <TerminalEntry key={entry.id ?? index} message={entry} thinkingEnabled={thinkingEnabled} onSelectTrace={selectTrace} />)}</div>}
    </div>
    <div className="terminal-input-area relative shrink-0 border-t border-white/10 bg-night px-3 py-3 lg:px-5">
      {queue.length > 0 && <div className="mb-2 space-y-1">{queue.map((item, index) => <div key={item.id} className="flex items-center gap-2 text-[9px] text-terminal-amber/80"><span>[queue {index + 1}]</span><span className="min-w-0 truncate">{item.text}</span><button type="button" className="ml-auto text-slate/40 hover:text-terminal-red" onClick={() => setQueue((items) => items.filter((queued) => queued.id !== item.id))}>x</button></div>)}</div>}
      <div className="mb-2 flex flex-wrap gap-1">{visibleCommands.map((command) => <button key={command} type="button" className="terminal-command" onClick={() => setMessage(command)}>{command}</button>)}<button type="button" className="terminal-command text-terminal-green" onClick={() => setCommandsExpanded((value) => !value)}>{commandsExpanded ? "less" : "more"}</button></div>
      {showEmotionPopup && <div ref={emotionPopupRef} className="absolute inset-x-3 bottom-[calc(100%-1px)] z-10 border border-terminal-green/30 bg-[#111615] p-3 lg:inset-x-5"><div className="mb-2 text-[9px] uppercase tracking-widest text-slate/45">/emotion &lt;name&gt; [+/-]value</div><div className="grid grid-cols-2 gap-1 sm:grid-cols-5">{EMOTION_NAMES.map((name) => <button key={name} type="button" className="border border-white/10 px-2 py-1 text-left text-[9px] text-slate/65 hover:border-terminal-green/50 hover:text-terminal-green" onClick={() => { setMessage(`/emotion ${name} `); setShowEmotionPopup(false); }}>{name}<span className="ml-1 text-slate/30">{status.emotions?.[name] ?? "—"}</span></button>)}</div></div>}
      <form onSubmit={handleSubmit} className="flex items-end gap-2"><textarea value={message} onChange={(event) => { setMessage(event.target.value); setHistoryIndex(-1); }} onKeyDown={handleKeyDown} rows={2} placeholder={isProcessing ? "_ CHAPPiE antwortet gerade..." : "_ write a message or use /commands..."} className="terminal-input min-h-[3.5rem] flex-1 resize-none border border-white/12 bg-input px-3 py-2 text-[11px] leading-relaxed text-mist outline-none placeholder:text-slate/35 focus:border-terminal-green/55" /><button type="submit" disabled={!message.trim()} className="terminal-send h-[3.5rem] border border-terminal-green/45 px-3 text-[10px] uppercase tracking-widest text-terminal-green hover:bg-terminal-green/10 disabled:cursor-not-allowed disabled:opacity-25">send</button></form>
      <div className="mt-2 flex items-center justify-between text-[8px] uppercase tracking-widest text-slate/25"><span>enter send · shift+enter newline · tab complete</span>{isProcessing && <span>{formatDuration(elapsedMs)} elapsed</span>}</div>
    </div>
  </div>;
}
