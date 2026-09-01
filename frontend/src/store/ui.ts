import { create } from "zustand";

export type ChatMessage = {
  id?: string;
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
};

export function isSlashCommand(content: string): boolean {
  return content.trimStart().startsWith("/");
}

export type ProcessingState = "idle" | "thinking" | "streaming" | "error";

export type LivePipelineState = {
  stage?: string;
  stage_key?: string;
  step?: number;
  status_text?: string;
  started_at?: number;
  updated_at?: number;
  elapsed_ms?: number;
  token_count?: number;
  answer_tokens?: number;
  ttft_ms?: number | null;
  answer_time_ms?: number;
  total_gen_ms?: number;
  tokens_per_second?: number;
  provider?: string;
  model?: string;
  error?: string;
};

type UiState = {
  currentSessionId: string | null;
  setCurrentSessionId: (value: string | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (value: boolean) => void;
  closeSidebar: () => void;

  // Streaming state — survives page navigation
  processingState: ProcessingState;
  setProcessingState: (value: ProcessingState) => void;
  streamingContent: string;
  setStreamingContent: (value: string) => void;
  reasoningContent: string;
  setReasoningContent: (value: string) => void;
  displayMessages: ChatMessage[];
  setDisplayMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => void;
  isProcessing: boolean;
  setIsProcessing: (value: boolean) => void;
  genStartTime: number | null;
  setGenStartTime: (value: number | null) => void;
  elapsedMs: number;
  setElapsedMs: (value: number) => void;
  loadedOnce: boolean;
  setLoadedOnce: (value: boolean) => void;
  thinkingEnabled: boolean;
  setThinkingEnabled: (value: boolean) => void;
  activeTraceId: string | null;
  setActiveTraceId: (value: string | null) => void;
  streamError: string | null;
  setStreamError: (value: string | null) => void;
  livePipeline: LivePipelineState | null;
  setLivePipeline: (value: LivePipelineState | null | ((previous: LivePipelineState | null) => LivePipelineState | null)) => void;
  resetStreamingState: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  currentSessionId: null,
  setCurrentSessionId: (value) => set({ currentSessionId: value }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (value) => set({ isSidebarOpen: value }),
  closeSidebar: () => set({ isSidebarOpen: false }),

  processingState: "idle",
  setProcessingState: (value) => set({ processingState: value }),
  streamingContent: "",
  setStreamingContent: (value) => set({ streamingContent: value }),
  reasoningContent: "",
  setReasoningContent: (value) => set({ reasoningContent: value }),
  displayMessages: [],
  setDisplayMessages: (messages: ChatMessage[] | ((prev: ChatMessage[]) => ChatMessage[])) => set((state) => ({
    displayMessages: typeof messages === "function" ? messages(state.displayMessages) : messages,
  })),
  isProcessing: false,
  setIsProcessing: (value) => set({ isProcessing: value }),
  genStartTime: null,
  setGenStartTime: (value) => set({ genStartTime: value }),
  elapsedMs: 0,
  setElapsedMs: (value) => set({ elapsedMs: value }),
  loadedOnce: false,
  setLoadedOnce: (value) => set({ loadedOnce: value }),
  thinkingEnabled: true,
  setThinkingEnabled: (value) => set({ thinkingEnabled: value }),
  activeTraceId: null,
  setActiveTraceId: (value) => set({ activeTraceId: value }),
  streamError: null,
  setStreamError: (value) => set({ streamError: value }),
  livePipeline: null,
  setLivePipeline: (value) => set((state) => ({
    livePipeline: typeof value === "function" ? value(state.livePipeline) : value,
  })),
  resetStreamingState: () => set({
    processingState: "idle",
    streamingContent: "",
    reasoningContent: "",
    streamError: null,
    livePipeline: null,
    isProcessing: false,
    genStartTime: null,
    elapsedMs: 0,
  }),
}));
