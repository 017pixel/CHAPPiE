import { KeyboardEvent as ReactKeyboardEvent, PointerEvent as ReactPointerEvent, useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties, ReactNode } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useLocation, useNavigate } from "react-router-dom";

import { api } from "../services/api";
import frontendPackage from "../../package.json";
import { estimateTextTokens, formatTokenRate } from "../lib/telemetry";
import { isSlashCommand } from "../store/ui";
import type { ChatMessage, LivePipelineState } from "../store/ui";
import { useUiStore } from "../store/ui";

type InspectorSection =
  | "trace"
  | "context"
  | "memories"
  | "life"
  | "growth"
  | "settings"
  | "steering"
  | "training"
  | "debug";

type ExplorerMode = "message" | "category";
type TraceStatus = "ok" | "warn" | "error" | "live";
type TraceMessageKind = "input" | "output" | "command" | "system";
type TraceView = "overview" | "input" | "command" | "result" | "memory" | "steering" | "timing" | "raw" | "causal";

type TraceEntry = {
  id: string;
  index: number;
  turn: number;
  label: string;
  message: ChatMessage;
  metadata: Record<string, any>;
  messageKind: TraceMessageKind;
  commandText?: string;
  status: TraceStatus;
  categoryIds: InspectorSection[];
  searchable: string;
};

type TimelineStep = {
  key: string;
  label: string;
  offset: string;
  detail: string;
  status: "done" | "active" | "inactive" | "warn" | "error";
};

type QuerySnapshot = {
  data: unknown;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
  refetch: () => unknown;
};

const CATEGORY_DEFS: Array<{ id: InspectorSection; label: string; icon: string; path?: string }> = [
  { id: "memories", label: "Memory", icon: "memory", path: "/memories" },
  { id: "life", label: "Life", icon: "favorite", path: "/life" },
  { id: "steering", label: "Steering", icon: "tune", path: "/settings" },
  { id: "training", label: "Training", icon: "model_training", path: "/training" },
  { id: "debug", label: "Debug", icon: "bug_report", path: "/debug" },
  { id: "context", label: "Context", icon: "folder_open", path: "/context" },
];

const SECTION_PATHS: Record<string, InspectorSection> = {
  "/context": "context",
  "/memories": "memories",
  "/life": "life",
  "/growth": "growth",
  "/settings": "settings",
  "/training": "training",
  "/debug": "debug",
};

const TRACE_CHILDREN: Record<TraceMessageKind, Array<{ label: string; icon: string; view: TraceView }>> = {
  input: [
    { label: "Input", icon: "input", view: "input" },
    { label: "Raw", icon: "code", view: "raw" },
  ],
  command: [
    { label: "Command", icon: "terminal", view: "command" },
    { label: "Raw", icon: "code", view: "raw" },
  ],
  system: [
    { label: "Result", icon: "receipt_long", view: "result" },
    { label: "Raw", icon: "code", view: "raw" },
  ],
  output: [
    { label: "Memory", icon: "memory", view: "memory" },
    { label: "Steering", icon: "tune", view: "steering" },
    { label: "Timing", icon: "schedule", view: "timing" },
    { label: "Raw", icon: "code", view: "raw" },
    { label: "Causal", icon: "account_tree", view: "causal" },
  ],
};

const MAX_RENDERED_TRACE_ROWS = 200;
const DEFAULT_TREE_SPLIT = 34;
const MIN_TREE_SPLIT = 20;
const MAX_TREE_SPLIT = 55;
const MIN_TREE_WIDTH = 180;
const MIN_DETAIL_WIDTH = 320;
const TREE_DIVIDER_WIDTH = 4;
const TREE_SPLIT_STORAGE_KEY = "chappie-inspector-tree-ratio";
const APP_VERSION = frontendPackage.version;

function clamp(value: number, lower: number, upper: number): number {
  return Math.min(upper, Math.max(lower, value));
}

function readStoredTreeSplit(): number {
  if (typeof window === "undefined") return DEFAULT_TREE_SPLIT;
  try {
    const stored = Number(window.localStorage.getItem(TREE_SPLIT_STORAGE_KEY));
    return Number.isFinite(stored) ? clamp(stored, MIN_TREE_SPLIT, MAX_TREE_SPLIT) : DEFAULT_TREE_SPLIT;
  } catch {
    return DEFAULT_TREE_SPLIT;
  }
}

function asRecord(value: unknown): Record<string, any> {
  return value && typeof value === "object" && !Array.isArray(value) ? (value as Record<string, any>) : {};
}

function asArray(value: unknown): any[] {
  return Array.isArray(value) ? value : [];
}

function textValue(value: unknown, fallback = "—"): string {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);
  return fallback;
}

function formatDuration(value: unknown, fallback = "—"): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return fallback;
  if (numeric < 1000) return `${Math.round(numeric)}ms`;
  return `${(numeric / 1000).toFixed(numeric >= 10000 ? 1 : 2)}s`;
}

function formatOffset(value: unknown): string {
  const numeric = Number(value);
  if (!Number.isFinite(numeric)) return "+—";
  return `+${formatDuration(numeric, "0ms")}`;
}

function formatTimestamp(value: unknown): string {
  if (!value) return "—";
  const date = new Date(String(value));
  return Number.isNaN(date.getTime()) ? textValue(value) : date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
}

function safeJson(value: unknown, spacing = 2): string {
  try {
    return JSON.stringify(value, null, spacing) ?? "—";
  } catch {
    return String(value);
  }
}

function errorMessage(value: unknown): string {
  return value instanceof Error ? value.message : textValue(value, "unknown error");
}

function activeSignal(value: unknown): boolean {
  if (typeof value === "boolean") return value;
  if (typeof value === "number") return Number.isFinite(value) && value !== 0;
  if (typeof value === "string") {
    return !["", "false", "0", "no", "none", "null", "undefined", "inactive", "ok"].includes(value.trim().toLowerCase());
  }
  if (Array.isArray(value)) return value.length > 0;
  return Boolean(value && typeof value === "object" && Object.keys(value as object).length > 0);
}

function contextWasTrimmed(metadata: Record<string, any>): boolean {
  const budget = asRecord(metadata.context_budget || metadata.budget);
  return [
    metadata.was_trimmed,
    metadata.context_trimmed,
    metadata.trimmed,
    budget.was_trimmed,
    budget.context_trimmed,
    budget.truncated,
    budget.trimmed,
  ].some(activeSignal) || [
    budget.removed_messages,
    budget.messages_removed,
    budget.removed_tokens,
    budget.tokens_removed,
    budget.trimmed_tokens,
  ].some((value) => Number(value) > 0) || (
    Number(budget.original_message_count) > 0 &&
    Number(budget.final_message_count) >= 0 &&
    Number(budget.original_message_count) > Number(budget.final_message_count)
  );
}

function metadataHasError(metadata: Record<string, any>, content: string): boolean {
  const status = String(metadata.status || metadata.status_text || "").toLowerCase();
  return [
    metadata.stream_error,
    metadata.turn_error,
    metadata.error,
    metadata.error_message,
    metadata.error_details,
    metadata.status_error,
    metadata.formatting_failed,
    metadata.cot_leak?.is_unexpected_cot,
  ].some(activeSignal) || metadata.status === "error" || /\b(error|failed|failure|fehler|fehlgeschlagen)\b/.test(status) || /^fehler[:\s]/i.test(content) || /^(?:vllm|ollama|groq|steering-server)\b[^\n]{0,120}\b(?:error|failed|failure|fehler|fehlgeschlagen)\b/i.test(content);
}

function hasRepetition(metadata: Record<string, any>): boolean {
  return [
    metadata.repetition_events,
    metadata.repetition,
    metadata.repetition_detected,
    metadata.repetition_loop,
    metadata.content_loop,
    metadata.post_repetition_cut,
    metadata.quality?.repetition,
  ].some(activeSignal);
}

function categoryIdsFor(metadata: Record<string, any>, status: TraceStatus): InspectorSection[] {
  const ids: InspectorSection[] = [];
  if (metadata.rag_memories || metadata.memory_trace || metadata.memory_consolidation) ids.push("memories");
  if (metadata.global_workspace || metadata.homeostasis || metadata.temporal_state || metadata.life_snapshot) ids.push("life");
  if (metadata.emotion_steering || metadata.steering || metadata.prompt_emotion_mode) ids.push("steering");
  if (metadata.training || metadata.training_state) ids.push("training");
  if (metadata.context_budget || metadata.context_files) ids.push("context");
  if (metadata.causal_trace || metadata.debug || status === "error") ids.push("debug");
  if (ids.length === 0) ids.push("debug");
  return ids;
}

function traceMessageKind(message: ChatMessage, previous?: ChatMessage): { kind: TraceMessageKind; commandText?: string } {
  const metadata = asRecord(message.metadata);
  const isCommand = message.role === "user" && (metadata.is_command === true || metadata.message_kind === "command" || isSlashCommand(message.content));
  if (isCommand) return { kind: "command", commandText: message.content.trim() };

  const isSystem = message.role === "system" || metadata.is_system === true || metadata.is_system_response === true || metadata.message_kind === "system" || (message.role === "assistant" && previous?.role === "user" && isSlashCommand(previous.content));
  if (isSystem) {
    const commandText = metadata.command || (previous?.role === "user" && isSlashCommand(previous.content) ? previous.content.trim() : undefined);
    return { kind: "system", commandText };
  }

  return { kind: message.role === "user" ? "input" : "output" };
}

function traceKindLabel(kind: TraceMessageKind): string {
  if (kind === "command") return "command";
  if (kind === "system") return "system";
  if (kind === "input") return "input";
  return "model output";
}

function buildTraceEntries(messages: ChatMessage[], isLive: boolean, liveContent: string, streamError: string | null, livePipeline: LivePipelineState | null): TraceEntry[] {
  const entries = messages.map((message, index) => {
    const ownMetadata = asRecord(message.metadata);
    const content = message.content ?? "";
    const { kind: messageKind, commandText } = traceMessageKind(message, messages[index - 1]);
    const nextMessage = messages[index + 1];
    const nextMetadata = asRecord(nextMessage?.metadata);
    const nextKind = nextMessage ? traceMessageKind(nextMessage, message).kind : undefined;
    const relatedCommandTrace = messageKind === "command" && nextKind === "system"
      ? asRecord(nextMetadata.command_trace)
      : {};
    const metadata = Object.keys(relatedCommandTrace).length > 0
      ? { ...ownMetadata, command_trace: relatedCommandTrace, command_response: messages[index + 1]?.content }
      : ownMetadata;
    const live = message.id === "streaming" || Boolean(metadata.live);
    const status: TraceStatus = live ? "live" : metadataHasError(metadata, content) ? "error" : contextWasTrimmed(metadata) || hasRepetition(metadata) ? "warn" : "ok";
    const turn = Math.floor(index / 2) + 1;
    const label = messageKind === "command" ? `Command #${turn}` : messageKind === "system" ? `System #${turn}` : messageKind === "input" ? `Input #${turn}` : `Chat #${turn}`;
    const searchable = `${label} ${messageKind} ${message.role} ${content} ${commandText ?? ""} ${safeJson(metadata, 0)}`.toLowerCase();
    return {
      id: message.id ?? `message-${index}`,
      index,
      turn,
      label,
      message,
      metadata,
      messageKind,
      commandText,
      status,
      categoryIds: categoryIdsFor(metadata, status),
      searchable,
    };
  });

  const liveEntryIndex = entries.findIndex((entry) => entry.id === "streaming");
  if (isLive && liveEntryIndex >= 0) {
    const current = entries[liveEntryIndex];
    entries[liveEntryIndex] = {
      ...current,
      message: { ...current.message, content: liveContent || current.message.content },
      metadata: { ...current.metadata, live: true, live_pipeline: livePipeline ?? current.metadata.live_pipeline, error_message: streamError ?? current.metadata.error_message },
      status: streamError ? "error" : "live",
      searchable: `${current.searchable} ${liveContent} ${streamError ?? ""}`.toLowerCase(),
    };
  } else if (isLive) {
    const index = entries.length;
    const metadata = { live: true, live_pipeline: livePipeline ?? undefined, error_message: streamError ?? undefined };
    const previous = messages[messages.length - 1];
    const followsCommand = previous?.role === "user" && isSlashCommand(previous.content);
    const messageKind: TraceMessageKind = followsCommand ? "system" : "output";
    const commandText = followsCommand ? previous.content.trim() : undefined;
    entries.push({
      id: "streaming",
      index,
      turn: Math.floor(index / 2) + 1,
      label: messageKind === "system" ? `System #${Math.floor(index / 2) + 1}` : `Chat #${Math.floor(index / 2) + 1}`,
      message: { id: "streaming", role: "assistant", content: liveContent || "processing" },
      metadata,
      messageKind,
      commandText,
      status: streamError ? "error" : "live",
      categoryIds: categoryIdsFor(metadata, streamError ? "error" : "live"),
      searchable: `chat streaming ${liveContent} ${streamError ?? ""}`.toLowerCase(),
    });
  }
  return entries;
}

function statusColor(status: TraceStatus): string {
  if (status === "error") return "text-terminal-red";
  if (status === "warn") return "text-terminal-amber";
  if (status === "live") return "text-terminal-green";
  return "text-slate/50";
}

function statusMark(status: TraceStatus): string {
  if (status === "error") return "!";
  if (status === "warn") return "~";
  if (status === "live") return "*";
  return "+";
}

function entryMatches(entry: TraceEntry, query: string): boolean {
  return !query.trim() || entry.searchable.includes(query.trim().toLowerCase());
}

function rawResponse(entry: TraceEntry): string {
  return textValue(entry.metadata.raw_response, entry.message.content === "—" ? "" : entry.message.content);
}

async function copyText(value: string): Promise<boolean> {
  if (!value) return false;
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(value);
      return true;
    }
  } catch {
    // Fall back to the legacy copy path for embedded or insecure previews.
  }

  const textarea = document.createElement("textarea");
  textarea.value = value;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.top = "-9999px";
  textarea.style.opacity = "0";
  document.body.appendChild(textarea);
  try {
    textarea.focus();
    textarea.select();
    textarea.setSelectionRange(0, value.length);
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

function Field({ label, value, valueClass = "text-slate/75" }: { label: string; value: ReactNode; valueClass?: string }) {
  return (
    <div className="min-w-0">
      <div className="text-[9px] uppercase tracking-widest text-slate/35">{label}</div>
      <div className={`mt-0.5 break-words text-[11px] ${valueClass}`}>{value}</div>
    </div>
  );
}

function DetailCard({ title, status, defaultOpen = true, open: controlledOpen, onToggle, children }: { title: string; status?: TraceStatus; defaultOpen?: boolean; open?: boolean; onToggle?: () => void; children: ReactNode }) {
  const [open, setOpen] = useState(defaultOpen);
  const isOpen = controlledOpen ?? open;
  return (
    <section className={`trace-card min-w-0 border ${status === "error" ? "border-terminal-red/35 bg-terminal-red/[0.035]" : status === "warn" ? "border-terminal-amber/25 bg-terminal-amber/[0.025]" : "border-white/10 bg-white/[0.018]"}`}>
      <button type="button" className="flex w-full items-center justify-between border-b border-white/8 px-3 py-2 text-left" onClick={() => onToggle ? onToggle() : setOpen((value) => !value)}>
        <span className="flex items-center gap-2 text-[10px] font-semibold uppercase tracking-widest text-slate/75">
          <span className="text-terminal-green">{isOpen ? "▾" : "▸"}</span>
          {title}
        </span>
        {status && <span className={`text-[9px] uppercase tracking-widest ${statusColor(status)}`}>{status === "error" ? "error" : status === "warn" ? "warn" : status === "live" ? "live" : "ok"}</span>}
      </button>
      {isOpen && <div className="p-3">{children}</div>}
    </section>
  );
}

function EmptyTrace({ message = "> _ No traces yet. Send a message to start." }: { message?: string }) {
  return (
    <div className="flex min-h-[18rem] items-center justify-center border border-dashed border-white/10 px-6 text-center text-[11px] text-slate/45">
      <div>
        <div className="mb-3 text-2xl text-terminal-green/40">›_</div>
        <p>{message}</p>
      </div>
    </div>
  );
}

const LIVE_STAGE_ORDER = ["intent", "memory", "steering", "ttft", "streaming", "format", "done"];

function normalizeLiveStage(value: unknown): string {
  const pipeline = asRecord(value);
  const raw = `${pipeline.stage ?? pipeline.stage_key ?? pipeline.phase ?? pipeline.status_text ?? ""}`.toLowerCase();
  const step = Number(pipeline.step);
  if (/intent|analyse|classif|step\s*1/.test(raw)) return "intent";
  if (/memory|context|retriev|life|workspace/.test(raw)) return "memory";
  if (/steer|emotion|vector/.test(raw)) return "steering";
  if (/ttft|first\s+token|prompt|generation\s+start|waiting/.test(raw)) return "ttft";
  if (/stream|token/.test(raw)) return "streaming";
  if (/format|sanit/.test(raw)) return "format";
  if (/done|finish|complete|abgeschlossen/.test(raw)) return "done";
  if (step === 1) return "intent";
  return "ttft";
}

function timelineFor(entry: TraceEntry, isLive: boolean, elapsedMs: number, streamError: string | null, providerFallback = "provider —"): TimelineStep[] {
  const meta = entry.metadata;
  if (entry.messageKind !== "output") {
    const kindDetail = entry.messageKind === "command" ? "command input" : "system response";
    return [
      { key: "intent", label: "intent", offset: "+—", detail: "—", status: "inactive" },
      { key: "memory", label: "memory", offset: "+—", detail: "inactive", status: "inactive" },
      { key: "steering", label: "steering", offset: "+—", detail: "inactive", status: "inactive" },
      { key: "ttft", label: "TTFT", offset: "+—", detail: "—", status: "inactive" },
      { key: "streaming", label: "streaming", offset: "+—", detail: "—", status: "inactive" },
      { key: "format", label: "format", offset: "+—", detail: "inactive", status: "inactive" },
      { key: "done", label: "done", offset: "+—", detail: streamError ?? (isLive ? "processing" : kindDetail), status: streamError ? "error" : isLive ? "active" : "inactive" },
    ];
  }
  const timing = asRecord(meta.timing);
  const pipeline = asRecord(meta.live_pipeline || meta.pipeline);
  const tokenCount = Number(timing.answer_tokens) || Number(pipeline.answer_tokens) || estimateTextTokens(entry.message.content);
  const answerTime = Number(timing.answer_time_ms) || Number(pipeline.answer_time_ms) || (isLive ? elapsedMs : 0);
  const ttft = timing.ttft_ms ?? pipeline.ttft_ms;
  const formattingFailed = Boolean(meta.formatting_failed);
  const hasError = Boolean(streamError || metadataHasError(meta, entry.message.content));
  const activeStage = normalizeLiveStage(pipeline);
  const activeIndex = Math.max(0, LIVE_STAGE_ORDER.indexOf(activeStage));
  const liveStatus = (key: string): TimelineStep["status"] => {
    if (!isLive) {
      if (hasError && key === "done") return "error";
      return key === "format" && formattingFailed ? "error" : "done";
    }
    const index = LIVE_STAGE_ORDER.indexOf(key);
    if (hasError && index === activeIndex) return "error";
    if (hasError && key === "done") return "error";
    if (index < activeIndex) return "done";
    if (index === activeIndex) return "active";
    return "inactive";
  };
  const liveText = textValue(pipeline.status_text, "processing");
  const steering = asRecord(meta.emotion_steering || meta.steering);
  const rate = formatTokenRate(timing, meta, entry.message.content, elapsedMs);
  return [
    { key: "intent", label: "intent", offset: formatOffset(meta.intent_time_ms ?? 0), detail: isLive && activeStage === "intent" ? liveText : `${textValue(meta.intent_type, "casual_chat")} · confidence ${meta.intent_confidence != null ? `${Math.round(Number(meta.intent_confidence) * 100)}%` : "—"}`, status: liveStatus("intent") },
    { key: "memory", label: "memory", offset: formatOffset(meta.memory_time_ms ?? 0), detail: isLive && activeStage === "memory" ? liveText : `${asArray(meta.rag_memories).length} matches · top-k ${textValue(meta.memory_top_k, "—")}`, status: liveStatus("memory") },
    { key: "steering", label: "steering", offset: formatOffset(meta.steering_time_ms ?? 0), detail: isLive && activeStage === "steering" ? `${liveText} · ${steering.steering_active ? "active vectors" : "preparing"}` : steering.steering_active ? "active vectors" : "inactive", status: liveStatus("steering") },
    { key: "ttft", label: "TTFT", offset: formatOffset(ttft), detail: isLive && activeStage === "ttft" && ttft == null ? `${liveText} · ${textValue(meta.provider || pipeline.provider, providerFallback)}` : `first token ${formatDuration(ttft)} · ${textValue(meta.provider || pipeline.provider, providerFallback)}`, status: liveStatus("ttft") },
    { key: "streaming", label: "streaming", offset: formatOffset(answerTime), detail: isLive && activeStage === "streaming" ? `${tokenCount} tokens · ${rate} · ${liveText}` : `${tokenCount} tokens · ${rate}`, status: liveStatus("streaming") },
    { key: "format", label: "format", offset: formatOffset(meta.formatting_time_ms ?? 0), detail: isLive && activeStage === "format" ? liveText : formattingFailed ? "formatting failed · raw response" : textValue(meta.formatting_source, "local"), status: liveStatus("format") },
    { key: "done", label: "done", offset: formatOffset(timing.total_gen_ms ?? pipeline.total_gen_ms ?? meta.processing_time_ms), detail: streamError ?? (hasError ? textValue(meta.error_message || meta.error, "turn error") : isLive ? "waiting for turn_finished" : "turn finished"), status: liveStatus("done") },
  ];
}

function Timeline({ entry, isLive, elapsedMs, streamError, providerFallback }: { entry: TraceEntry; isLive: boolean; elapsedMs: number; streamError: string | null; providerFallback?: string }) {
  const steps = timelineFor(entry, isLive, elapsedMs, streamError, providerFallback);
  const switches = asArray(entry.metadata.provider_switches);
  return (
    <div className="timeline-wrap overflow-x-auto pb-1">
      <div className="flex min-w-[760px] items-start">
        {steps.map((step, index) => (
          <div key={step.key} className="flex min-w-[105px] flex-1 items-start">
            <div className="flex min-w-0 flex-1 flex-col gap-1">
              <div className="flex items-center">
                <span className={`timeline-dot ${step.status === "error" ? "bg-terminal-red" : step.status === "active" ? "bg-terminal-green animate-pulse" : step.status === "warn" ? "bg-terminal-amber" : step.status === "inactive" ? "bg-slate/25" : "bg-slate/55"}`} />
                {index < steps.length - 1 && <span className="h-px flex-1 bg-white/15" />}
              </div>
              <span className={`text-[9px] uppercase tracking-widest ${step.status === "error" ? "text-terminal-red" : step.status === "active" ? "text-terminal-green" : step.status === "inactive" ? "text-slate/40" : "text-slate/70"}`}>{step.label}</span>
              <span className="text-[9px] text-slate/35">{step.offset}</span>
              <span className="max-w-[110px] text-[9px] leading-relaxed text-slate/45">{step.detail}</span>
            </div>
          </div>
        ))}
      </div>
      {entry.messageKind === "output" && switches.length > 0 && (
        <div className="mt-3 border-l-2 border-terminal-amber/50 pl-2 text-[9px] text-terminal-amber/80">
          provider switches: {switches.map((item, index) => `${textValue(item.from, "?")} → ${textValue(item.to, "?")}${item.at_ms != null ? ` @ ${formatDuration(item.at_ms)}` : ""}`).join(" · ")}
        </div>
      )}
    </div>
  );
}

function TraceHeader({ entry }: { entry: TraceEntry }) {
  const meta = entry.metadata;
  return <div className="border-b border-white/10 pb-3">
    <div className={`mb-1 text-[9px] uppercase tracking-[0.22em] ${statusColor(entry.status)}`}>
      {statusMark(entry.status)} trace {entry.turn.toString().padStart(2, "0")} <span className={entry.messageKind === "command" ? "text-terminal-amber" : entry.messageKind === "system" ? "text-slate/60" : "text-slate/45"}>· {traceKindLabel(entry.messageKind)}</span>
    </div>
    <h2 className="truncate text-sm font-semibold tracking-tight text-mist">{entry.label}</h2>
    <p className="mt-1 truncate text-[10px] text-slate/40">{entry.id} · {formatTimestamp(meta.created_at || meta.timestamp)}</p>
  </div>;
}

function InputDetail({ entry, view, onCopy }: { entry: TraceEntry; view: TraceView; onCopy: (value: string) => void }) {
  const content = entry.message.content;
  const lines = content.split("\n").length;
  const words = content.trim() ? content.trim().split(/\s+/).length : 0;
  const rawOnly = view === "raw";
  return <div className="min-w-0 space-y-3">
    <TraceHeader entry={entry} />
    {!rawOnly && <DetailCard title="Input details">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
        <Field label="role" value="user input" />
        <Field label="characters" value={content.length} />
        <Field label="words" value={words} />
        <Field label="lines" value={lines} />
        <Field label="estimated tokens" value={estimateTextTokens(content)} />
        <Field label="timestamp" value={formatTimestamp(entry.metadata.created_at || entry.metadata.timestamp)} />
      </div>
    </DetailCard>}
    <DetailCard title={rawOnly ? "Raw input" : "Input content"}>
      <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words border-l-2 border-[#6f8fa8]/60 pl-3 text-[10px] leading-relaxed text-slate/75">{content}</pre>
      <button type="button" className="inspector-action mt-3" onClick={() => onCopy(content)}>copy input</button>
    </DetailCard>
    {rawOnly && Object.keys(entry.metadata).length > 0 && <DetailCard title="Input metadata" defaultOpen={false}><pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/55">{safeJson(entry.metadata)}</pre></DetailCard>}
  </div>;
}

function CommandDetail({ entry, view, onCopy }: { entry: TraceEntry; view: TraceView; onCopy: (value: string) => void }) {
  const trace = asRecord(entry.metadata.command_trace);
  const actions = asArray(trace.actions);
  const details = asRecord(trace.details);
  const command = textValue(trace.command || entry.commandText, entry.message.content);
  const result = entry.messageKind === "command"
    ? textValue(entry.metadata.command_response, "Noch keine Systemantwort verknüpft.")
    : entry.message.content;
  const rawOnly = view === "raw";
  const resultOnly = view === "result";
  return <div className="min-w-0 space-y-3">
    <TraceHeader entry={entry} />
    {!rawOnly && !resultOnly && <>
      <DetailCard title="Command request">
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <Field label="command" value={command} valueClass="font-mono text-terminal-amber" />
          <Field label="handler" value={textValue(trace.handler, "command router")} />
          <Field label="arguments" value={asArray(trace.arguments).join(" ") || "none"} />
          <Field label="status" value={textValue(trace.status, "submitted")} valueClass={trace.status === "completed" ? "text-terminal-green" : "text-terminal-amber"} />
          <Field label="duration" value={trace.duration_ms != null ? formatDuration(trace.duration_ms) : "—"} />
          <Field label="type" value={entry.messageKind === "command" ? "command input" : "system response"} />
        </div>
      </DetailCard>
      <DetailCard title="Executed actions">
        {actions.length === 0 ? <p className="text-[10px] text-slate/40">No action trace attached.</p> : <ol className="space-y-2">{actions.map((action, index) => <li key={`${index}-${String(action)}`} className="flex gap-3 border-l-2 border-terminal-green/45 pl-3 text-[10px] text-slate/70"><span className="text-terminal-green">{String(index + 1).padStart(2, "0")}</span><span>{textValue(action)}</span></li>)}</ol>}
      </DetailCard>
      {Object.keys(details).length > 0 && <DetailCard title="Command data" defaultOpen={false}><pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/55">{safeJson(details)}</pre></DetailCard>}
    </>}
    {(resultOnly || view === "overview" || rawOnly) && <DetailCard title={rawOnly ? "Raw command record" : "Command result"}>
      {rawOnly ? <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/60">{safeJson({ command, trace, result })}</pre> : <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words border-l-2 border-terminal-amber/45 pl-3 text-[10px] leading-relaxed text-slate/75">{result}</pre>}
      <button type="button" className="inspector-action mt-3" onClick={() => onCopy(rawOnly ? safeJson({ command, trace, result }) : result)}>copy</button>
    </DetailCard>}
  </div>;
}

function TraceDetail({ entry, activeView, isLive, elapsedMs, streamError, showRaw, reasoningExpanded, providerFallback, onToggleRaw, onToggleReasoning, onCopy, onRetry }: { entry: TraceEntry; activeView: TraceView; isLive: boolean; elapsedMs: number; streamError: string | null; showRaw: boolean; reasoningExpanded: boolean; providerFallback?: string; onToggleRaw: () => void; onToggleReasoning: () => void; onCopy: (value: string) => void; onRetry: () => void }) {
  if (entry.messageKind === "input") return <InputDetail entry={entry} view={activeView} onCopy={onCopy} />;
  if (entry.messageKind === "command" || entry.messageKind === "system") return <CommandDetail entry={entry} view={activeView} onCopy={onCopy} />;

  const meta = entry.metadata;
  const timing = asRecord(meta.timing);
  const budget = asRecord(meta.context_budget || meta.budget);
  const memories = asArray(meta.rag_memories);
  const deltas = asRecord(meta.emotions_delta);
  const before = asRecord(meta.emotions_before);
  const steering = asRecord(meta.emotion_steering || meta.steering);
  const focus = asRecord(meta.global_workspace).dominant_focus || {};
  const causal = asArray(meta.causal_trace);
  const repetitions = asRecord(meta.repetition_events || meta.repetition);
  const raw = rawResponse(entry);
  const reasoning = textValue(meta.formatted_cot || meta.reasoning, "No reasoning payload");
  const tokenRate = formatTokenRate(timing, meta, entry.message.content, isLive ? elapsedMs : 0);
  const errorText = streamError || textValue(meta.error_message || meta.error, "");
  const overview = activeView === "overview";

  return (
    <div className="min-w-0 space-y-3">
      <TraceHeader entry={entry} />

      {(overview || activeView === "timing") && <DetailCard title="Pipeline timeline" status={entry.status}>
        <Timeline entry={entry} isLive={isLive} elapsedMs={elapsedMs} streamError={streamError} providerFallback={providerFallback} />
      </DetailCard>}

      {overview && errorText && (
        <div className="flex items-start justify-between gap-3 border border-terminal-red/35 bg-terminal-red/[0.06] p-3 text-[10px] text-terminal-red">
          <div><span className="font-semibold uppercase tracking-widest">turn_error</span><p className="mt-1 text-terminal-red/80">{errorText}</p></div>
          <button type="button" className="shrink-0 border border-terminal-red/40 px-2 py-1 text-[9px] uppercase tracking-widest hover:bg-terminal-red/10" onClick={onRetry}>retry</button>
        </div>
      )}

      {overview && <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        <DetailCard title="Overview">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            <Field label="intent" value={`${textValue(meta.intent_type, "casual_chat")} ${meta.intent_confidence != null ? `${Math.round(Number(meta.intent_confidence) * 100)}%` : ""}`} />
            <Field label="tone" value={textValue(meta.tone_decision?.tone)} />
            <Field label="tools" value={textValue(meta.tool_calls_executed, "0")} />
            <Field label="timestamp" value={formatTimestamp(meta.created_at || meta.timestamp)} />
          </div>
        </DetailCard>

        <DetailCard title="Emotionen">
          {Object.keys(deltas).length === 0 ? <p className="text-[10px] italic text-slate/40">No emotion deltas.</p> : <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">{Object.entries(deltas).map(([name, value]) => { const item = asRecord(value); const change = Number(item.change) || 0; return <div key={name} className="border border-white/8 px-2 py-1.5 text-[10px]"><span className="text-slate/40">{name}</span><div className="mt-1"><span className="text-slate/55">{textValue(item.before ?? before[name])}</span><span className="px-1 text-slate/25">→</span><span className="text-slate/75">{textValue(item.after)}</span><span className={`ml-1 ${change > 0 ? "text-terminal-green" : change < 0 ? "text-terminal-red" : "text-slate/40"}`}>{change > 0 ? "+" : ""}{change}</span></div></div>; })}</div>}
        </DetailCard>
      </div>}

      {(overview || activeView === "memory") && <>
        <DetailCard title="Memory" status={memories.length === 0 ? undefined : "ok"}>
          {memories.length === 0 ? <p className="text-[10px] italic text-slate/40">&gt; _ no matches (try broader query)</p> : <div className="min-w-0 space-y-2">{memories.slice(0, 12).map((memory, index) => { const item = asRecord(memory); return <div key={`${index}-${textValue(item.content, "memory")}`} className="min-w-0 border-l-2 border-terminal-green/35 pl-2"><div className="flex min-w-0 flex-wrap gap-2 text-[9px] uppercase tracking-widest text-slate/40"><span>{textValue(item.role, "memory")}</span><span className="text-terminal-green">{item.relevance_score != null ? `${Math.round(Number(item.relevance_score) * 100)}%` : "—"}</span><span className="min-w-0 break-words [overflow-wrap:anywhere]">{textValue(item.label)}</span></div><p className="mt-1 min-w-0 whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/65 [overflow-wrap:anywhere]">{textValue(item.content)}</p></div>; })}</div>}
          {meta.memory_consolidation && <div className="mt-3 border-t border-white/8 pt-2 text-[10px] text-slate/45">consolidation: {safeJson(meta.memory_consolidation, 0)}</div>}
        </DetailCard>
        <DetailCard title="Context budget" status={contextWasTrimmed(meta) ? "error" : budget.near_limit ? "warn" : undefined}>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4"><Field label="estimated" value={textValue(budget.estimated_tokens, "—")} /><Field label="limit" value={textValue(budget.token_limit, "7000")} /><Field label="status" value={contextWasTrimmed(meta) ? "GETRIMMT" : budget.near_limit ? "NEAR LIMIT" : "OK"} valueClass={contextWasTrimmed(meta) ? "text-terminal-red" : budget.near_limit ? "text-terminal-amber" : "text-terminal-green"} /><Field label="removed" value={textValue(budget.removed_messages, "0")} /></div>
          {contextWasTrimmed(meta) && <p className="mt-3 border-l-2 border-terminal-red/50 pl-2 text-[10px] text-terminal-red/80">{textValue(budget.removed_messages, "older")} messages removed from the context window.</p>}
        </DetailCard>
        {Object.keys(focus).length > 0 || meta.memory_trace ? <DetailCard title="Focus + global workspace"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Field label="dominant focus" value={textValue(focus.label)} /><Field label="salience" value={textValue(focus.salience)} /><Field label="broadcast" value={textValue(asRecord(meta.global_workspace).broadcast)} /><Field label="memories found" value={textValue(asRecord(meta.memory_trace).merged?.memories_found)} /><Field label="top relevance" value={textValue(asRecord(meta.memory_trace).merged?.top_relevance)} /><Field label="query" value={textValue(asRecord(meta.memory_trace).merged?.query)} /></div></DetailCard> : null}
      </>}

      {(overview || activeView === "steering" || activeView === "timing") && <div className="grid grid-cols-1 gap-3 xl:grid-cols-2">
        {(overview || activeView === "steering") &&
        <DetailCard title="Steering">
          {Object.keys(steering).length === 0 ? <p className="text-[10px] italic text-slate/40">Steering inactive.</p> : <div className="grid grid-cols-2 gap-3"><Field label="mode" value={textValue(steering.summary || meta.prompt_emotion_mode, "vector")} /><Field label="dominant" value={`${textValue(steering.dominant_vector, "neutral")} (${textValue(steering.dominant_strength, "0")})`} /><Field label="active vectors" value={asArray(steering.active_vectors || steering.base_vectors).map((item) => textValue(asRecord(item).name || item)).filter(Boolean).join(", ") || "none"} /><Field label="steering active" value={steering.steering_active ? "yes" : "no"} valueClass={steering.steering_active ? "text-terminal-green" : "text-slate/45"} /></div>}
        </DetailCard>}
        {(overview || activeView === "timing") &&
        <DetailCard title="Timing">
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Field label="TTFT" value={formatDuration(timing.ttft_ms)} /><Field label="generation" value={formatDuration(timing.total_gen_ms || meta.processing_time_ms)} /><Field label="output stream" value={`${formatDuration(timing.answer_time_ms)} · ${textValue(timing.answer_tokens, "0")} tk`} /><Field label="reasoning" value={`${formatDuration(timing.reasoning_time_ms)} · ${textValue(timing.reasoning_tokens, "0")} tk`} /><Field label="effective rate" value={tokenRate} valueClass="text-terminal-green" /><Field label="total tokens" value={textValue(timing.total_tokens, "—")} /></div>
          <p className="mt-3 border-l-2 border-white/15 pl-2 text-[9px] leading-relaxed text-slate/40">Rate basis: answer tokens over complete measured generation time.</p>
        </DetailCard>}
      </div>}

      {(overview || activeView === "causal") && <DetailCard title="Causal trace">
        {causal.length === 0 ? <p className="text-[10px] italic text-slate/40">No causal trace attached.</p> : <div className="space-y-2">{causal.map((step, index) => { const item = asRecord(step); return <div key={index} className="border-l-2 border-white/15 pl-2 text-[10px] text-slate/60"><span className="text-slate/80">{textValue(item.phase, "phase")}:</span> {textValue(item.driver)}{item.effect && <span className="text-slate/40"> — {textValue(item.effect)}</span>}{item.evidence && <span className="text-slate/35"> [{Array.isArray(item.evidence) ? item.evidence.join(", ") : textValue(item.evidence)}]</span>}</div>; })}</div>}
      </DetailCard>}

      {overview && Object.keys(repetitions).length > 0 && <DetailCard title="Repetition" status="warn">
        <div className="space-y-1">{Object.entries(repetitions).map(([key, value]) => <div key={key} className="border-l-2 border-terminal-amber/50 pl-2 text-[10px] text-terminal-amber/75"><span className="font-semibold">{key}</span> <span className="text-slate/45">{typeof value === "object" ? safeJson(value, 0) : String(value)}</span></div>)}</div>
      </DetailCard>}

      {(overview || activeView === "raw") && <DetailCard title="Reasoning / CoT" open={activeView === "raw" ? true : reasoningExpanded} onToggle={onToggleReasoning}>
        <div className="border-l-2 border-terminal-green/35 pl-2"><pre className="max-h-60 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/60">{reasoning}</pre></div>
      </DetailCard>}

      {(overview || activeView === "raw") && <DetailCard title="Raw / formatted output">
        <div className="mb-2 flex items-center justify-between gap-2 text-[9px] uppercase tracking-widest text-slate/40"><span>{showRaw ? "raw response" : "formatted response"}</span><button type="button" className="border border-white/10 px-2 py-1 text-terminal-green hover:bg-terminal-green/10" onClick={onToggleRaw}>{showRaw ? "show formatted" : "show raw"}</button></div>
        <pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words border-l-2 border-white/15 pl-2 text-[10px] leading-relaxed text-slate/65">{showRaw ? raw : entry.message.content}</pre>
        <button type="button" className="mt-2 border border-white/10 px-2 py-1 text-[9px] uppercase tracking-widest text-slate/55 hover:border-terminal-green/40 hover:text-terminal-green" onClick={() => onCopy(raw)}>copy raw</button>
      </DetailCard>}
    </div>
  );
}

function diffLines(left: string, right: string): { left: Array<{ text: string; changed: boolean }>; right: Array<{ text: string; changed: boolean }> } {
  const leftLines = left.split("\n");
  const rightLines = right.split("\n");
  const rightSet = new Set(rightLines);
  const leftSet = new Set(leftLines);
  return {
    left: leftLines.map((text) => ({ text, changed: !rightSet.has(text) })),
    right: rightLines.map((text) => ({ text, changed: !leftSet.has(text) })),
  };
}

function DiffColumn({ title, lines }: { title: string; lines: Array<{ text: string; changed: boolean }> }) {
  return <div className="min-w-0 border border-white/10"><div className="border-b border-white/10 px-3 py-2 text-[9px] uppercase tracking-widest text-slate/55">{title}</div><pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed">{lines.map((line, index) => <div key={index} className={`flex gap-2 px-3 ${line.changed ? title === "A" ? "bg-terminal-red/10 text-terminal-red/80" : "bg-terminal-green/10 text-terminal-green/80" : "text-slate/55"}`}><span className="w-5 shrink-0 select-none text-right text-slate/25">{String(index + 1).padStart(2, "0")}</span><span>{line.text || " "}</span></div>)}</pre></div>;
}

function CompareDetail({ left, right }: { left: TraceEntry; right: TraceEntry }) {
  const diff = diffLines(left.message.content, right.message.content);
  const leftMeta = left.metadata;
  const rightMeta = right.metadata;
  const changedKeys = Array.from(new Set([...Object.keys(leftMeta), ...Object.keys(rightMeta)])).filter((key) => safeJson(leftMeta[key], 0) !== safeJson(rightMeta[key], 0));
  return <div className="space-y-3"><div className="border-b border-white/10 pb-3"><div className="text-[9px] uppercase tracking-[0.22em] text-terminal-amber">compare mode · cmd/click to replace</div><h2 className="mt-1 text-sm text-mist">{left.label} ⇄ {right.label}</h2></div><div className="grid grid-cols-1 gap-3 xl:grid-cols-2"><DiffColumn title="A" lines={diff.left} /><DiffColumn title="B" lines={diff.right} /></div><DetailCard title="Metadata diff"><div className="space-y-2">{changedKeys.length === 0 ? <p className="text-[10px] text-slate/45">No metadata differences.</p> : changedKeys.map((key) => <div key={key} className="grid grid-cols-1 gap-1 border-l-2 border-terminal-amber/45 pl-2 text-[10px] md:grid-cols-2"><div><span className="text-terminal-red">- {key}</span><pre className="mt-1 whitespace-pre-wrap break-words text-slate/50">{safeJson(leftMeta[key], 0)}</pre></div><div><span className="text-terminal-green">+ {key}</span><pre className="mt-1 whitespace-pre-wrap break-words text-slate/50">{safeJson(rightMeta[key], 0)}</pre></div></div>)}</div></DetailCard></div>;
}

function SectionSnapshot({ section, snapshot, isLoading, isError, error, onRetry }: { section: InspectorSection; snapshot: unknown; isLoading: boolean; isError: boolean; error: unknown; onRetry: () => void }) {
  const [editingFile, setEditingFile] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const contextMutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) => api.updateContextFile(name, content),
    onSuccess: () => { setEditingFile(null); onRetry(); },
  });
  const title = section === "context" ? "Context files" : section === "memories" ? "Memory index" : section === "life" ? "Life snapshot" : section === "growth" ? "Growth" : section === "settings" || section === "steering" ? "Settings / steering" : section === "training" ? "Training daemon" : "Debug feed";
  const record = asRecord(snapshot);
  const memoryItems = asArray(record.items ?? snapshot);
  const debugEntries = asArray(record.entries);
  const contextFiles = Object.entries(record).filter(([, value]) => typeof value === "string");
  const primitiveFields = Object.entries(record).filter(([, value]) => value === null || ["string", "number", "boolean"].includes(typeof value)).slice(0, 12);

  function sectionBody() {
    if (section === "context") {
      if (contextFiles.length === 0) return <EmptyTrace message="> _ no context files returned" />;
      return <div className="min-w-0 grid grid-cols-1 gap-3 xl:grid-cols-2">{contextFiles.map(([name, value]) => <article key={name} className="min-w-0 border border-white/10 bg-black/15 p-3"><div className="mb-2 flex min-w-0 items-center justify-between gap-2 border-b border-white/8 pb-2"><span className="min-w-0 break-words text-[10px] uppercase tracking-widest text-terminal-green [overflow-wrap:anywhere]">{name}.md</span>{editingFile !== name && <button type="button" className="inspector-action shrink-0" onClick={() => { setEditingFile(name); setDraft(String(value)); }}>edit</button>}</div>{editingFile === name ? <><textarea value={draft} onChange={(event) => setDraft(event.target.value)} className="min-h-[12rem] w-full resize-y border border-white/10 bg-input p-2 text-[10px] leading-relaxed text-mist outline-none focus:border-terminal-green/50" spellCheck={false} /><div className="mt-2 flex gap-1"><button type="button" className="inspector-action text-terminal-green" disabled={contextMutation.isPending} onClick={() => contextMutation.mutate({ name, content: draft })}>{contextMutation.isPending ? "saving" : "save"}</button><button type="button" className="inspector-action" onClick={() => setEditingFile(null)}>cancel</button></div></> : <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/60 [overflow-wrap:anywhere]">{value}</pre>}</article>)}</div>;
    }
    if (section === "memories") {
      return memoryItems.length === 0 ? <EmptyTrace message="> _ no matches (try broader query)" /> : <div className="min-w-0 space-y-2"><div className="grid grid-cols-2 gap-2 sm:grid-cols-3"><Field label="visible" value={memoryItems.length} /><Field label="total" value={textValue(record.total, String(memoryItems.length))} /><Field label="query" value={textValue(record.query, "all")} /></div>{memoryItems.slice(0, 30).map((item, index) => { const memory = asRecord(item); return <article key={index} className="min-w-0 border-l-2 border-terminal-green/35 pl-2"><div className="flex min-w-0 flex-wrap gap-2 text-[9px] uppercase tracking-widest text-slate/40"><span>{textValue(memory.role, "memory")}</span><span className="text-terminal-green">{memory.relevance_score != null ? `${Math.round(Number(memory.relevance_score) * 100)}%` : "—"}</span><span className="min-w-0 break-words [overflow-wrap:anywhere]">{textValue(memory.type || memory.label)}</span></div><p className="mt-1 min-w-0 whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/65 [overflow-wrap:anywhere]">{textValue(memory.content, safeJson(item, 0))}</p></article>; })}</div>;
    }
    if (section === "life") {
      const clock = asRecord(record.clock);
      const temporal = asRecord(record.temporal_state);
      const goal = asRecord(record.active_goal);
      const development = asRecord(record.development);
      const homeostasis = asRecord(record.homeostasis);
      const needs = asArray(homeostasis.active_needs);
      return <div className="space-y-3"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Field label="phase" value={textValue(clock.phase_label || clock.phase)} /><Field label="activity" value={textValue(record.current_activity)} /><Field label="mode" value={textValue(record.current_mode)} /><Field label="goal" value={textValue(goal.title)} /><Field label="goal progress" value={goal.progress != null ? `${Math.round(Number(goal.progress) * 100)}%` : "—"} valueClass="text-terminal-green" /><Field label="development" value={textValue(development.stage)} /><Field label="rhythm" value={textValue(temporal.interaction_rhythm)} /><Field label="silence" value={textValue(temporal.silence_bucket)} /><Field label="session turns" value={textValue(temporal.session_turn_count)} /></div><DetailCard title="Homeostasis"><div className="space-y-2">{needs.length === 0 ? <p className="text-[10px] text-slate/40">No active needs.</p> : needs.map((need, index) => { const item = asRecord(need); const value = Math.max(0, Math.min(100, Number(item.value) || 0)); return <div key={index}><div className="mb-1 flex justify-between text-[9px] uppercase tracking-widest text-slate/50"><span>{textValue(item.name, "need")}</span><span className="text-terminal-green">{Math.round(value)}%</span></div><div className="h-1 bg-white/10"><div className="h-1 bg-terminal-green" style={{ width: `${value}%` }} /></div></div>; })}</div></DetailCard></div>;
    }
    if (section === "growth") {
      const planning = asRecord(record.planning_state);
      const forecast = asRecord(record.forecast_state);
      const social = asRecord(record.social_arc);
      const development = asRecord(record.development);
      const timeline = asArray(record.timeline_history);
      return <div className="space-y-3"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Field label="horizon" value={textValue(planning.planning_horizon)} /><Field label="plan confidence" value={planning.plan_confidence != null ? `${Math.round(Number(planning.plan_confidence) * 100)}%` : "—"} valueClass="text-terminal-green" /><Field label="risk" value={textValue(forecast.risk_level)} valueClass={String(forecast.risk_level).toLowerCase() === "high" ? "text-terminal-red" : "text-terminal-amber"} /><Field label="next outlook" value={textValue(forecast.next_turn_outlook)} /><Field label="social arc" value={textValue(social.arc_name)} /><Field label="arc score" value={social.arc_score != null ? `${Math.round(Number(social.arc_score) * 100)}%` : "—"} valueClass="text-terminal-green" /><Field label="development" value={textValue(development.stage)} /><Field label="timeline entries" value={textValue(record.timeline_summary?.entries, String(timeline.length))} /></div><DetailCard title="Next milestone"><p className="text-[10px] leading-relaxed text-slate/65">{textValue(planning.next_milestone || forecast.guidance || social.guidance, "No milestone supplied.")}</p></DetailCard><DetailCard title="Timeline history" defaultOpen={false}><div className="space-y-2">{timeline.slice(-12).reverse().map((item, index) => { const event = asRecord(item); return <div key={index} className="border-l-2 border-white/15 pl-2 text-[10px]"><div className="text-slate/45">{formatTimestamp(event.timestamp)} · {textValue(event.source, "event")}</div><div className="mt-0.5 text-slate/65">{textValue(event.phase_label || event.activity || event.goal)}</div></div>; })}</div></DetailCard></div>;
    }
    if (section === "training") {
      return <div className="space-y-3"><div className="grid grid-cols-2 gap-3 sm:grid-cols-3"><Field label="status" value={textValue(record.status_label || (record.running ? "running" : "stopped"))} valueClass={record.running ? "text-terminal-green" : "text-terminal-amber"} /><Field label="pid" value={textValue(record.pid)} /><Field label="loops" value={textValue(record.loops)} /><Field label="memories" value={textValue(record.memory_count)} /><Field label="provider" value={textValue(record.provider)} /><Field label="model" value={textValue(record.model)} /></div>{record.errors && <DetailCard title="Errors" status="error"><pre className="whitespace-pre-wrap text-[10px] text-terminal-red/75">{safeJson(record.errors)}</pre></DetailCard>}{record.log && <DetailCard title="Daemon log"><pre className="max-h-64 overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/60">{textValue(record.log)}</pre></DetailCard>}</div>;
    }
    if (section === "debug" && debugEntries.length > 0) {
      return <div className="space-y-2">{debugEntries.slice(0, 50).map((item, index) => { const debug = asRecord(item); const failed = textValue(debug.category).toLowerCase().includes("error"); return <article key={index} className={`border-l-2 pl-2 ${failed ? "border-terminal-red/60" : "border-terminal-green/35"}`}><div className="flex justify-between gap-2 text-[9px] uppercase tracking-widest"><span className={failed ? "text-terminal-red" : "text-terminal-green"}>{textValue(debug.category, "event")}</span><span className="text-slate/30">#{index + 1}</span></div><p className="mt-1 text-[10px] text-slate/60">{textValue(debug.message, safeJson(item, 0))}</p></article>; })}</div>;
    }
    if (primitiveFields.length > 0) return <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">{primitiveFields.map(([key, value]) => <Field key={key} label={key.replace(/_/g, " ")} value={textValue(value)} />)}</div>;
    return <EmptyTrace message="> _ section payload contains no scalar fields" />;
  }

  return <div className="min-w-0 space-y-3"><div className="border-b border-white/10 pb-3"><h2 className="mt-1 text-sm text-mist">{title}</h2><p className="mt-1 text-[10px] text-slate/40">Lazy-loaded from the existing CHAPPiE endpoint.</p></div>{isLoading && <div className="border border-white/10 p-4 text-[10px] text-terminal-green">&gt; _ loading {section}...</div>}{isError && <div className="border border-terminal-red/35 bg-terminal-red/[0.05] p-3 text-[10px] text-terminal-red">&gt; _ endpoint error: {errorMessage(error)}<button type="button" className="ml-3 border border-terminal-red/40 px-2 py-1 uppercase tracking-widest hover:bg-terminal-red/10" onClick={onRetry}>retry</button></div>}{!isLoading && !isError && snapshot === undefined && <EmptyTrace message="> _ no section payload yet" />}{!isLoading && !isError && snapshot !== undefined && sectionBody()}{!isLoading && !isError && snapshot !== undefined && <DetailCard title="Raw section payload" defaultOpen={false}><pre className="max-h-80 overflow-auto whitespace-pre-wrap break-words text-[10px] leading-relaxed text-slate/55 [overflow-wrap:anywhere]">{safeJson(snapshot)}</pre></DetailCard>}{(section === "settings" || section === "steering") && <div className="border-t border-white/8 pt-2 text-[9px] text-slate/30">v{APP_VERSION}</div>}</div>;
}

export function InspectorPane() {
  const displayMessages = useUiStore((state) => state.displayMessages);
  const processingState = useUiStore((state) => state.processingState);
  const streamingContent = useUiStore((state) => state.streamingContent);
  const reasoningContent = useUiStore((state) => state.reasoningContent);
  const elapsedMs = useUiStore((state) => state.elapsedMs);
  const livePipeline = useUiStore((state) => state.livePipeline);
  const activeTraceId = useUiStore((state) => state.activeTraceId);
  const streamError = useUiStore((state) => state.streamError);
  const setActiveTraceId = useUiStore((state) => state.setActiveTraceId);
  const location = useLocation();
  const navigate = useNavigate();
  const [mode, setMode] = useState<ExplorerMode>("message");
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set(["streaming"]));
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [activeTraceView, setActiveTraceView] = useState<TraceView>("overview");
  const [compareId, setCompareId] = useState<string | null>(null);
  const [activeSection, setActiveSection] = useState<InspectorSection | null>(SECTION_PATHS[location.pathname] ?? null);
  const [showRaw, setShowRaw] = useState(false);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<"success" | "error" | null>(null);
  const [treeSplitRatio, setTreeSplitRatio] = useState(readStoredTreeSplit);
  const [treeDragging, setTreeDragging] = useState(false);
  const treeRef = useRef<HTMLDivElement>(null);
  const inspectorContentRef = useRef<HTMLDivElement>(null);
  const copyFeedbackTimerRef = useRef<number | null>(null);
  const handledActiveTraceRef = useRef<string | null>(null);
  const statusQuery = useQuery({ queryKey: ["status"], queryFn: api.getStatus, refetchInterval: 3000 });
  const runtimeStatus = (statusQuery.data ?? {}) as Record<string, unknown>;
  const runtimeModel = textValue(runtimeStatus.model, "loading");
  const runtimeProvider = textValue(runtimeStatus.provider, "—");

  const isLive = processingState === "thinking" || processingState === "streaming";
  const entries = useMemo(() => buildTraceEntries(displayMessages, isLive, streamingContent || reasoningContent, streamError, livePipeline), [displayMessages, isLive, streamingContent, reasoningContent, streamError, livePipeline]);
  const filteredEntries = useMemo(() => entries.filter((entry) => entryMatches(entry, query)), [entries, query]);
  const renderedEntries = useMemo(() => filteredEntries.length > MAX_RENDERED_TRACE_ROWS ? filteredEntries.slice(-MAX_RENDERED_TRACE_ROWS) : filteredEntries, [filteredEntries]);
  const selectedEntry = entries.find((entry) => entry.id === selectedId) ?? null;
  const compareEntry = entries.find((entry) => entry.id === compareId) ?? null;

  const contextQuery = useQuery({ queryKey: ["inspector", "context-files"], queryFn: api.getContextFiles, enabled: activeSection === "context" });
  const memoriesQuery = useQuery({ queryKey: ["inspector", "memories"], queryFn: () => api.getMemories(), enabled: activeSection === "memories" });
  const lifeQuery = useQuery({ queryKey: ["inspector", "life"], queryFn: api.getLife, enabled: activeSection === "life", refetchInterval: activeSection === "life" ? 3000 : false });
  const growthQuery = useQuery({ queryKey: ["inspector", "growth"], queryFn: api.getGrowth, enabled: activeSection === "growth", refetchInterval: activeSection === "growth" ? 3000 : false });
  const settingsQuery = useQuery({ queryKey: ["inspector", "settings"], queryFn: api.getSettings, enabled: activeSection === "settings" || activeSection === "steering" });
  const trainingQuery = useQuery({ queryKey: ["inspector", "training"], queryFn: api.getTrainingStatus, enabled: activeSection === "training", refetchInterval: activeSection === "training" ? 5000 : false });
  const debugQuery = useQuery({ queryKey: ["inspector", "debug"], queryFn: api.getDebug, enabled: activeSection === "debug", refetchInterval: activeSection === "debug" ? 2000 : false });

  const sectionQueries: Partial<Record<InspectorSection, QuerySnapshot>> = {
    context: contextQuery,
    memories: memoriesQuery,
    life: lifeQuery,
    growth: growthQuery,
    settings: settingsQuery,
    steering: settingsQuery,
    training: trainingQuery,
    debug: debugQuery,
  };
  const activeQuery = activeSection ? sectionQueries[activeSection] : undefined;

  useEffect(() => {
    const timeout = window.setTimeout(() => setQuery(searchInput), 120);
    return () => window.clearTimeout(timeout);
  }, [searchInput]);

  useEffect(() => {
    try {
      window.localStorage.setItem(TREE_SPLIT_STORAGE_KEY, String(treeSplitRatio));
    } catch {
      // Storage can be disabled in a private or embedded browser context.
    }
  }, [treeSplitRatio]);

  useEffect(() => {
    const routeSection = SECTION_PATHS[location.pathname];
    if (routeSection) setActiveSection(routeSection);
    else if (location.pathname === "/") setActiveSection((current) => current === "trace" ? current : null);
  }, [location.pathname]);

  useEffect(() => {
    if (!selectedId && entries.length > 0) setSelectedId(entries[entries.length - 1].id);
    if (selectedId && !entries.some((entry) => entry.id === selectedId)) setSelectedId(entries.length > 0 ? entries[entries.length - 1].id : null);
  }, [entries, selectedId]);

  useEffect(() => {
    if (activeTraceId && activeTraceId !== handledActiveTraceRef.current && entries.some((entry) => entry.id === activeTraceId)) {
      handledActiveTraceRef.current = activeTraceId;
      setSelectedId(activeTraceId);
      setActiveTraceView("overview");
      setActiveSection("trace");
    }
  }, [activeTraceId, entries]);

  useEffect(() => {
    return () => {
      if (copyFeedbackTimerRef.current !== null) window.clearTimeout(copyFeedbackTimerRef.current);
    };
  }, []);

  const visibleTreeEntries = mode === "message" ? filteredEntries : CATEGORY_DEFS.flatMap((category) => filteredEntries.filter((entry) => entry.categoryIds.includes(category.id)));

  function setTreeRatioFromPointer(clientX: number) {
    const bounds = inspectorContentRef.current?.getBoundingClientRect();
    if (!bounds || bounds.width <= TREE_DIVIDER_WIDTH) return;
    const availableWidth = bounds.width - TREE_DIVIDER_WIDTH;
    const minimumRatio = Math.min(MAX_TREE_SPLIT, Math.max(MIN_TREE_SPLIT, (MIN_TREE_WIDTH / availableWidth) * 100));
    const maximumRatio = Math.max(MIN_TREE_SPLIT, Math.min(MAX_TREE_SPLIT, 100 - (MIN_DETAIL_WIDTH / availableWidth) * 100));
    const ratio = ((clientX - bounds.left - TREE_DIVIDER_WIDTH / 2) / availableWidth) * 100;
    setTreeSplitRatio(clamp(ratio, minimumRatio, maximumRatio));
  }

  function handleTreeDividerPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    event.preventDefault();
    setTreeDragging(true);
    const previousCursor = document.body.style.cursor;
    const previousUserSelect = document.body.style.userSelect;
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (moveEvent: PointerEvent) => setTreeRatioFromPointer(moveEvent.clientX);
    const onFinish = () => {
      setTreeDragging(false);
      document.body.style.cursor = previousCursor;
      document.body.style.userSelect = previousUserSelect;
      window.removeEventListener("pointermove", onMove);
      window.removeEventListener("pointerup", onFinish);
      window.removeEventListener("pointercancel", onFinish);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onFinish, { once: true });
    window.addEventListener("pointercancel", onFinish, { once: true });
  }

  function resetTreeSplit() {
    setTreeSplitRatio(DEFAULT_TREE_SPLIT);
  }

  function handleTreeDividerDoubleClick() {
    resetTreeSplit();
  }

  function handleTreeDividerKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setTreeSplitRatio((ratio) => clamp(ratio - 2, MIN_TREE_SPLIT, MAX_TREE_SPLIT));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setTreeSplitRatio((ratio) => clamp(ratio + 2, MIN_TREE_SPLIT, MAX_TREE_SPLIT));
    } else if (event.key === "Home") {
      event.preventDefault();
      resetTreeSplit();
    } else if (event.key === "End") {
      event.preventDefault();
      setTreeSplitRatio(MAX_TREE_SPLIT);
    }
  }

  function openSection(section: InspectorSection) {
    setActiveSection(section);
    setCompareId(null);
    const definition = CATEGORY_DEFS.find((category) => category.id === section);
    const targetPath = definition?.path ?? (section === "growth" ? "/growth" : section === "settings" ? "/settings" : section === "trace" ? "/" : undefined);
    if (targetPath && location.pathname !== targetPath) navigate(targetPath);
  }

  function selectEntry(entry: TraceEntry, event?: ReactMouseEventLike) {
    if (event?.metaKey || event?.ctrlKey) {
      setCompareId((current) => current === entry.id ? null : entry.id);
      setSelectedId((current) => current ?? entry.id);
    } else {
      setSelectedId(entry.id);
      setCompareId(null);
    }
    setActiveTraceView("overview");
    setActiveTraceId(entry.id);
    setActiveSection("trace");
    if (location.pathname !== "/") navigate("/");
  }

  function selectTraceView(entry: TraceEntry, view: TraceView) {
    setSelectedId(entry.id);
    setCompareId(null);
    setActiveTraceView(view);
    setActiveSection("trace");
    if (location.pathname !== "/") navigate("/");
  }

  function toggleExpanded(id: string) {
    setExpanded((current) => {
      const next = new Set(current);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  }

  async function handleCopy(value: string) {
    const copied = await copyText(value);
    setCopyFeedback(copied ? "success" : "error");
    if (copyFeedbackTimerRef.current !== null) window.clearTimeout(copyFeedbackTimerRef.current);
    copyFeedbackTimerRef.current = window.setTimeout(() => {
      setCopyFeedback(null);
      copyFeedbackTimerRef.current = null;
    }, 2000);
  }

  function handleTreeKeyDown(event: ReactKeyboardEvent<HTMLDivElement>) {
    if (visibleTreeEntries.length === 0) return;
    const currentIndex = Math.max(0, visibleTreeEntries.findIndex((entry) => entry.id === selectedId));
    if (event.key === "ArrowDown") {
      event.preventDefault();
      const next = visibleTreeEntries[Math.min(visibleTreeEntries.length - 1, currentIndex + 1)];
      selectEntry(next);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      const next = visibleTreeEntries[Math.max(0, currentIndex - 1)];
      selectEntry(next);
    } else if (event.key.toLowerCase() === "c") {
      event.preventDefault();
      if (selectedEntry) void handleCopy(rawResponse(selectedEntry));
    } else if (event.key.toLowerCase() === "r") {
      event.preventDefault();
      setShowRaw((value) => !value);
    } else if (event.key.toLowerCase() === "e") {
      event.preventDefault();
      setReasoningExpanded((value) => !value);
    }
  }

  function renderTraceNode(entry: TraceEntry) {
    const isExpanded = expanded.has(entry.id);
    const isSelected = selectedId === entry.id || compareId === entry.id;
    const treeTiming = asRecord(entry.metadata.timing);
    const treeRate = entry.messageKind === "output" ? formatTokenRate(treeTiming, entry.metadata, entry.message.content, entry.id === "streaming" ? elapsedMs : 0) : "";
    const kindLabel = entry.messageKind === "output" ? "output" : entry.messageKind;
    return <div key={entry.id} className="tree-entry"><div className={`flex items-center border-l ${isSelected ? "border-terminal-green bg-terminal-green/[0.07]" : "border-transparent hover:bg-white/[0.035]"}`}><button type="button" className="w-7 shrink-0 px-1 py-2 text-[11px] text-slate/45 hover:text-terminal-green" aria-label={`${isExpanded ? "Collapse" : "Expand"} ${entry.label}`} onClick={(event) => { event.stopPropagation(); toggleExpanded(entry.id); }}>{isExpanded ? "▾" : "▸"}</button><button type="button" className="flex min-w-0 flex-1 items-center gap-2 py-2 pr-2 text-left text-[10px]" onClick={(event) => selectEntry(entry, event)}><span className={statusColor(entry.status)}>{statusMark(entry.status)}</span><span className={`truncate ${isSelected ? "text-mist" : "text-slate/75"}`}>{entry.label}</span><span className={`ml-auto shrink-0 text-[8px] uppercase tracking-widest ${entry.messageKind === "command" ? "text-terminal-amber" : entry.messageKind === "input" ? "text-[#8aa8bd]" : "text-slate/35"}`}>{kindLabel}</span>{treeRate !== "— tok/s" && treeRate && <span className="hidden shrink-0 text-[8px] text-terminal-green/65 xl:inline">{treeRate}</span>}</button></div>{isExpanded && <div className="ml-7 border-l border-white/10">{TRACE_CHILDREN[entry.messageKind].map((child) => <button key={child.view} type="button" className={`flex min-h-9 w-full items-center gap-2 px-3 py-2 text-left text-[9px] transition-colors hover:bg-white/[0.035] hover:text-mist ${isSelected && activeTraceView === child.view ? "bg-white/[0.04] text-terminal-green" : "text-slate/50"}`} onClick={() => selectTraceView(entry, child.view)}><span className="material-symbols-outlined text-[13px] text-slate/40">{child.icon}</span><span>{child.label}</span></button>)}</div>}</div>;
  }

  return <div className="inspector-shell relative flex h-full min-h-0 flex-col bg-[#101312] text-slate">
    <header className="inspector-header flex shrink-0 items-center gap-3 border-b border-white/10 px-3 py-2">
      <div className="flex min-w-0 items-center gap-3 text-[9px] uppercase tracking-widest">
        <span className="min-w-0 truncate text-slate/55">model <span className="text-terminal-green">{runtimeModel}</span></span>
        <span className="shrink-0 text-slate/55">provider <span className="text-mist">{runtimeProvider}</span></span>
      </div>
    </header>

    <div className="inspector-toolbar shrink-0 border-b border-white/10 px-3 py-2">
      <label className="flex min-h-10 items-center gap-2 border border-white/10 bg-black/20 px-3 py-2 text-[10px] text-slate/45"><span className="text-terminal-green">/</span><input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="search traces" className="min-w-0 flex-1 bg-transparent font-mono text-[10px] text-mist outline-none placeholder:text-slate/35" aria-label="Search traces" /></label>
      <div className="mt-2 flex items-center gap-1"><button type="button" className={`mode-toggle ${mode === "message" ? "is-active" : ""}`} onClick={() => setMode("message")}>messages</button><button type="button" className={`mode-toggle ${mode === "category" ? "is-active" : ""}`} onClick={() => setMode("category")}>systems</button></div>
    </div>

    <div ref={inspectorContentRef} className="inspector-content grid min-h-0 flex-1" style={{ "--inspector-tree-split": `${treeSplitRatio}%` } as CSSProperties}>
      <div ref={treeRef} tabIndex={0} className="trace-tree min-w-0 min-h-0 overflow-y-auto py-2 outline-none" role="tree" aria-label="Trace tree" onKeyDown={handleTreeKeyDown}>
        {mode === "message" ? renderedEntries.map(renderTraceNode) : CATEGORY_DEFS.map((category) => { const categoryEntries = renderedEntries.filter((entry) => entry.categoryIds.includes(category.id)); const expandedCategory = expanded.has(`category-${category.id}`); return <div key={category.id} className="tree-category"><div className="flex items-center border-l border-transparent hover:bg-white/[0.035]"><button type="button" className="w-6 shrink-0 px-1 py-2 text-[11px] text-slate/45 hover:text-terminal-green" onClick={() => toggleExpanded(`category-${category.id}`)}>{expandedCategory ? "▾" : "▸"}</button><button type="button" className="flex min-w-0 flex-1 items-center gap-2 py-2 pr-2 text-left text-[10px] text-slate/75" onClick={() => openSection(category.id)}><span className="material-symbols-outlined text-[13px] text-terminal-green/70">{category.icon}</span><span className="truncate">{category.label}</span><span className="ml-auto text-[9px] text-slate/30">{categoryEntries.length}</span></button></div>{expandedCategory && <div className="ml-6 border-l border-white/10">{categoryEntries.length === 0 ? <div className="px-2 py-1.5 text-[9px] text-slate/30">no matching traces</div> : categoryEntries.map(renderTraceNode)}</div>}</div>; })}
        {filteredEntries.length === 0 && <div className="px-3 py-8 text-[10px] leading-relaxed text-slate/40">&gt; _ no traces match.<br />try a broader query.</div>}
        {filteredEntries.length > MAX_RENDERED_TRACE_ROWS && <div className="border-t border-white/8 px-3 py-2 text-[9px] leading-relaxed text-terminal-amber/70">virtual window: latest {MAX_RENDERED_TRACE_ROWS} of {filteredEntries.length} rows</div>}
        <div className="mt-3 border-t border-white/8 px-3 pt-2 text-[9px] leading-relaxed text-slate/30">keys: ↑ ↓ navigate · c copy raw · r raw · e CoT</div>
        {copyFeedback && <div className={`px-3 pt-1 text-[9px] ${copyFeedback === "success" ? "text-terminal-green" : "text-terminal-red"}`}>{copyFeedback === "success" ? "erfolgreich kopiert" : "kopieren fehlgeschlagen"}</div>}
      </div>

      <div className="inspector-tree-divider group relative z-10 hidden w-1 min-w-0 cursor-col-resize touch-none bg-[#1c2821] transition-colors hover:bg-terminal-green lg:block" onPointerDown={handleTreeDividerPointerDown} onDoubleClick={handleTreeDividerDoubleClick} onKeyDown={handleTreeDividerKeyDown} tabIndex={0} role="separator" aria-orientation="vertical" aria-valuemin={MIN_TREE_SPLIT} aria-valuemax={MAX_TREE_SPLIT} aria-valuenow={Math.round(treeSplitRatio)} aria-label="Resize trace tree and detail" title="Drag to resize tree and detail · double-click to reset"><span className={`pointer-events-none absolute -left-[3px] top-1/2 h-[42px] w-[10px] -translate-y-1/2 border border-terminal-green/45 bg-[#101312] transition-opacity ${treeDragging ? "opacity-100" : "opacity-0 group-hover:opacity-100"}`} /></div>

      <div className="inspector-detail min-w-0 min-h-0 overflow-y-auto p-3 lg:p-4">
        {activeSection && activeSection !== "trace" ? <SectionSnapshot section={activeSection} snapshot={activeQuery?.data} isLoading={Boolean(activeQuery?.isLoading)} isError={Boolean(activeQuery?.isError)} error={activeQuery?.error} onRetry={() => void activeQuery?.refetch()} /> : compareEntry && selectedEntry ? <CompareDetail left={selectedEntry} right={compareEntry} /> : selectedEntry ? <TraceDetail entry={selectedEntry} activeView={activeTraceView} isLive={isLive && selectedEntry.id === "streaming"} elapsedMs={elapsedMs} streamError={streamError} showRaw={showRaw} reasoningExpanded={reasoningExpanded} providerFallback={textValue((statusQuery.data as any)?.provider, "provider —")} onToggleRaw={() => setShowRaw((value) => !value)} onToggleReasoning={() => setReasoningExpanded((value) => !value)} onCopy={(value) => void handleCopy(value)} onRetry={() => window.dispatchEvent(new Event("chappie:retry-last"))} /> : <EmptyTrace />}
      </div>
    </div>
  </div>;
}

type ReactMouseEventLike = { metaKey?: boolean; ctrlKey?: boolean };
