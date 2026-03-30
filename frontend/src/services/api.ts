function trimTrailingSlash(value: string): string {
  return value.replace(/\/+$/, "");
}

function deriveApiBaseUrl(): string {
  const explicitBaseUrl = import.meta.env.VITE_API_BASE_URL?.trim();
  if (explicitBaseUrl) {
    return trimTrailingSlash(explicitBaseUrl);
  }

  if (typeof window === "undefined") {
    return "http://127.0.0.1:8010";
  }

  const { protocol, hostname, port, origin } = window.location;
  if (port === "8010") {
    return trimTrailingSlash(origin);
  }

  return `${protocol}//${hostname}:8010`;
}

const API_BASE_URL = deriveApiBaseUrl();

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init
  });

  if (!response.ok) {
    throw new Error(`API ${response.status}: ${await response.text()}`);
  }

  return response.json() as Promise<T>;
}

export const api = {
  baseUrl: API_BASE_URL,
  getHealth: () => request("/health"),
  getStatus: () => request("/status"),
  getSessions: () => request("/sessions"),
  getActiveSession: () => request("/sessions/active"),
  getSession: (sessionId: string) => request(`/sessions/${sessionId}`),
  createSession: (title?: string) => request("/sessions", { method: "POST", body: JSON.stringify({ title }) }),
  deleteSession: (sessionId: string) => request(`/sessions/${sessionId}`, { method: "DELETE" }),
  sendMessage: (payload: { session_id: string | null; message: string; debug_mode: boolean; command_mode: boolean }) =>
    request("/chat", { method: "POST", body: JSON.stringify(payload) }),
  runCommand: (payload: { session_id?: string | null; command: string }) =>
    request("/command", { method: "POST", body: JSON.stringify(payload) }),
  getLife: () => request("/life"),
  getGrowth: () => request("/growth"),
  getDebug: () => request("/debug"),
  getMemories: (params?: URLSearchParams) => request(`/memories${params ? `?${params.toString()}` : ""}`),
  getMemoryHealth: () => request("/memories/health"),
  getShortTermMemories: () => request("/memories/short-term"),
  cleanupShortTermMemories: () => request("/memories/short-term/cleanup", { method: "POST" }),
  clearMemories: () => request("/memories", { method: "DELETE" }),
  getContextFiles: () => request("/context-files"),
  getSettings: () => request("/settings"),
  saveSettings: (payload: Record<string, unknown>) => request("/settings", { method: "POST", body: JSON.stringify(payload) }),
  getEmotionLayerConfig: () => request("/emotion-layer-config"),
  updateEmotionLayerConfig: (payload: Record<string, unknown>) =>
    request("/emotion-layer-config", { method: "POST", body: JSON.stringify(payload) }),
  getTrainingStatus: () => request("/training/status"),
  getTrainingConfig: () => request("/training/config"),
  saveTrainingConfig: (payload: Record<string, unknown>) => request("/training/config", { method: "POST", body: JSON.stringify(payload) }),
  runTrainingAction: (payload: Record<string, unknown>) => request("/training/action", { method: "POST", body: JSON.stringify(payload) }),
  getVisualizer: () => request("/visualizer")
};
