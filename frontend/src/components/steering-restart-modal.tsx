import { useEffect, useRef, useState } from "react";

type RestartStatus = {
  status: "idle" | "stopping" | "loading" | "calibrating" | "testing" | "ready" | "error" | string;
  progress: number;
  current_step: string;
  estimated_remaining: number;
  error?: string;
};

interface SteeringRestartModalProps {
  isOpen: boolean;
  oldModel: string;
  newModel: string;
  steeringBaseUrl: string;
  quantize?: boolean;
  onComplete: () => void;
  onError: (error: string) => void;
}

const DEFAULT_STATUS: RestartStatus = {
  status: "idle",
  progress: 0,
  current_step: "Warte auf Start...",
  estimated_remaining: 90,
};

export function SteeringRestartModal({
  isOpen,
  oldModel,
  newModel,
  steeringBaseUrl,
  quantize,
  onComplete,
  onError,
}: SteeringRestartModalProps) {
  const [status, setStatus] = useState<RestartStatus>(DEFAULT_STATUS);
  const startedRef = useRef(false);

  useEffect(() => {
    if (!isOpen) {
      startedRef.current = false;
      setStatus(DEFAULT_STATUS);
      return;
    }
    if (startedRef.current) return;
    startedRef.current = true;

    let cancelled = false;
    let pollTimer: ReturnType<typeof setInterval> | null = null;

    const poll = async () => {
      try {
        const response = await fetch(`${steeringBaseUrl}/v1/steering/restart-status`);
        if (!response.ok) throw new Error(await response.text());
        const next = (await response.json()) as RestartStatus;
        if (cancelled) return;
        setStatus(next);
        if (next.status === "ready") {
          if (pollTimer) clearInterval(pollTimer);
          window.setTimeout(onComplete, 800);
        }
        if (next.status === "error") {
          if (pollTimer) clearInterval(pollTimer);
          onError(next.error || next.current_step || "Steering-Restart fehlgeschlagen");
        }
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Steering-Status nicht erreichbar";
        setStatus({ status: "error", progress: 0, current_step: message, estimated_remaining: 0, error: message });
        onError(message);
        if (pollTimer) clearInterval(pollTimer);
      }
    };

    const start = async () => {
      try {
        setStatus({ status: "stopping", progress: 5, current_step: "Restart wird gestartet...", estimated_remaining: 90 });
        const response = await fetch(`${steeringBaseUrl}/v1/steering/restart`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ model: newModel, ...(quantize !== undefined ? { quantize } : {}) }),
        });
        if (!response.ok && response.status !== 409) throw new Error(await response.text());
        await poll();
        pollTimer = window.setInterval(poll, 2000);
      } catch (error) {
        if (cancelled) return;
        const message = error instanceof Error ? error.message : "Steering-Restart konnte nicht gestartet werden";
        setStatus({ status: "error", progress: 0, current_step: message, estimated_remaining: 0, error: message });
        onError(message);
      }
    };

    start();

    return () => {
      cancelled = true;
      if (pollTimer) clearInterval(pollTimer);
    };
  }, [isOpen, newModel, oldModel, onComplete, onError, quantize, steeringBaseUrl]);

  if (!isOpen) return null;

  const progress = Math.max(0, Math.min(100, Number(status.progress || 0)));
  const isError = status.status === "error";
  const isReady = status.status === "ready";

  return (
    <div className="fixed inset-0 z-[80] flex items-center justify-center bg-ink/80 px-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-none border border-white/10 bg-night p-6 shadow-glass">
        <div className="mb-5 flex items-start justify-between gap-4">
          <div>
            <p className="text-[10px] uppercase tracking-[0.28em] text-slate">Steering Server</p>
            <h2 className="mt-2 text-xl font-semibold text-mist">Modell wird neu geladen</h2>
          </div>
          <span className={`rounded-none border px-3 py-1 text-[10px] uppercase tracking-widest ${isError ? "border-red-400/40 text-red-300" : isReady ? "border-pine/40 text-pine" : "border-ember/40 text-ember"}`}>
            {status.status}
          </span>
        </div>

        <div className="mb-5 space-y-2 rounded-none border border-white/5 bg-white/[0.02] p-4 font-mono text-[11px] text-slate">
          <p className="truncate">Alt: {oldModel || "unbekannt"}</p>
          <p className="truncate text-mist">Neu: {newModel}</p>
        </div>

        <div className="h-2 w-full border border-white/10 bg-input">
          <div className={`h-full ${isError ? "bg-red-400" : "bg-ember"}`} style={{ width: `${progress}%` }} />
        </div>

        <div className="mt-4 flex items-center justify-between gap-4 text-xs">
          <p className={isError ? "text-red-300" : "text-mist"}>{status.current_step}</p>
          <p className="shrink-0 font-mono text-slate">{progress}%</p>
        </div>

        {!isError && !isReady && (
          <p className="mt-2 text-[10px] uppercase tracking-widest text-slate/70">
            Restzeit ca. {Number(status.estimated_remaining || 0)}s
          </p>
        )}

        {isError && (
          <div className="mt-4 space-y-3">
            <p className="border border-red-400/20 bg-red-400/10 p-3 text-xs text-red-200">
              {status.error || status.current_step}
            </p>
            <button
              type="button"
              onClick={onComplete}
              className="w-full rounded-none border border-white/10 bg-white/[0.04] px-4 py-2 text-[10px] font-bold uppercase tracking-widest text-mist hover:border-red-300/50"
            >
              Schliessen
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
