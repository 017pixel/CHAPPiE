import { useEffect, useRef, useState } from "react";

import { InspectorPane } from "./inspector-pane";
import { ChatPage } from "../pages/chat-page";

const DEFAULT_SPLIT = 35;
const MIN_SPLIT = 25;
const MAX_SPLIT = 75;
const MIN_PANEL_WIDTH = 320;
const SPLIT_STORAGE_KEY = "chappie-split-ratio";

function clamp(value: number, lower: number, upper: number): number {
  return Math.min(upper, Math.max(lower, value));
}

function readStoredSplit(): number {
  if (typeof window === "undefined") return DEFAULT_SPLIT;
  try {
    const stored = Number(window.localStorage.getItem(SPLIT_STORAGE_KEY));
    return Number.isFinite(stored) ? clamp(stored, MIN_SPLIT, MAX_SPLIT) : DEFAULT_SPLIT;
  } catch {
    return DEFAULT_SPLIT;
  }
}

export function AppShell() {
  const [splitRatio, setSplitRatio] = useState(readStoredSplit);
  const [dragging, setDragging] = useState(false);
  const [mobilePane, setMobilePane] = useState<"terminal" | "inspector">("terminal");
  const workspaceRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    try {
      window.localStorage.setItem(SPLIT_STORAGE_KEY, String(splitRatio));
    } catch {
      // Storage can be disabled in a private or embedded browser context.
    }
  }, [splitRatio]);

  function setRatioFromPointer(clientX: number) {
    const bounds = workspaceRef.current?.getBoundingClientRect();
    if (!bounds || bounds.width <= 0) return;
    const availableWidth = bounds.width - 4;
    const minimumRatio = Math.max(MIN_SPLIT, (MIN_PANEL_WIDTH / availableWidth) * 100);
    const maximumRatio = Math.min(MAX_SPLIT, 100 - (MIN_PANEL_WIDTH / availableWidth) * 100);
    setSplitRatio(clamp(((clientX - bounds.left) / availableWidth) * 100, minimumRatio, maximumRatio));
  }

  function handleDividerPointerDown(event: React.PointerEvent<HTMLDivElement>) {
    event.preventDefault();
    setDragging(true);
    document.body.style.cursor = "col-resize";
    document.body.style.userSelect = "none";

    const onMove = (moveEvent: PointerEvent) => setRatioFromPointer(moveEvent.clientX);
    const onUp = () => {
      setDragging(false);
      document.body.style.cursor = "";
      document.body.style.userSelect = "";
      window.removeEventListener("pointermove", onMove);
    };

    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp, { once: true });
  }

  function resetSplit() {
    setSplitRatio(DEFAULT_SPLIT);
  }

  function handleDividerDoubleClick() {
    resetSplit();
  }

  function handleDividerKeyDown(event: React.KeyboardEvent<HTMLDivElement>) {
    if (event.key === "ArrowLeft") {
      event.preventDefault();
      setSplitRatio((ratio) => clamp(ratio - 2, MIN_SPLIT, MAX_SPLIT));
    } else if (event.key === "ArrowRight") {
      event.preventDefault();
      setSplitRatio((ratio) => clamp(ratio + 2, MIN_SPLIT, MAX_SPLIT));
    } else if (event.key === "Home") {
      event.preventDefault();
      resetSplit();
    }
  }

  return (
    <div className="terminal-app flex h-screen w-screen flex-col overflow-hidden bg-ink font-sans text-mist">
      <div className="terminal-mobile-tabs flex shrink-0 border-b border-white/10 bg-night lg:hidden" role="tablist" aria-label="Workspace panes">
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "terminal"}
          className={`flex-1 border-r border-white/10 px-3 py-2 text-left text-[10px] uppercase tracking-widest ${mobilePane === "terminal" ? "text-terminal-green" : "text-slate/50"}`}
          onClick={() => setMobilePane("terminal")}
        >
          01 terminal
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={mobilePane === "inspector"}
          className={`flex-1 px-3 py-2 text-left text-[10px] uppercase tracking-widest ${mobilePane === "inspector" ? "text-terminal-green" : "text-slate/50"}`}
          onClick={() => setMobilePane("inspector")}
        >
          02 inspector
        </button>
      </div>

      <main ref={workspaceRef} className={`terminal-split-layout flex min-h-0 flex-1 ${dragging ? "is-dragging" : ""}`}>
        <section
          className={`terminal-split-pane terminal-pane-wrapper min-w-0 ${mobilePane === "terminal" ? "mobile-pane-visible" : "mobile-pane-hidden"}`}
          style={{ flex: `0 0 ${splitRatio}%` }}
          aria-label="Ubuntu terminal chat"
        >
          <ChatPage />
        </section>

        <div
          className="terminal-divider"
          onPointerDown={handleDividerPointerDown}
          onDoubleClick={handleDividerDoubleClick}
          onKeyDown={handleDividerKeyDown}
          tabIndex={0}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize terminal and inspector"
          title="Drag to resize · double-click to reset"
        >
          <span className="terminal-divider-handle" />
        </div>

        <section
          className={`terminal-split-pane inspector-pane-wrapper min-w-0 flex-1 ${mobilePane === "inspector" ? "mobile-pane-visible" : "mobile-pane-hidden"}`}
          aria-label="Research tracing inspector"
        >
          <InspectorPane />
        </section>
      </main>
    </div>
  );
}
