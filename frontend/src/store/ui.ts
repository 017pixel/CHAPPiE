import { create } from "zustand";

type ChatMessage = {
  id?: string;
  role: string;
  content: string;
  metadata?: Record<string, unknown>;
};

type ProcessingState = "idle" | "thinking" | "streaming" | "error";

type UiState = {
  currentSessionId: string | null;
  setCurrentSessionId: (value: string | null) => void;
  isSidebarOpen: boolean;
  toggleSidebar: () => void;
  setSidebarOpen: (value: boolean) => void;

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
  resetStreamingState: () => void;
};

export const useUiStore = create<UiState>((set) => ({
  currentSessionId: null,
  setCurrentSessionId: (value) => set({ currentSessionId: value }),
  isSidebarOpen: true,
  toggleSidebar: () => set((state) => ({ isSidebarOpen: !state.isSidebarOpen })),
  setSidebarOpen: (value) => set({ isSidebarOpen: value }),

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
  resetStreamingState: () => set({
    processingState: "idle",
    streamingContent: "",
    reasoningContent: "",
    isProcessing: false,
    genStartTime: null,
    elapsedMs: 0,
  }),
}));
