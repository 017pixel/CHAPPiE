import { useMutation, useQuery } from "@tanstack/react-query";
import { startTransition, useState } from "react";

import { api } from "../services/api";
import { useUiStore } from "../store/ui";

const longTermMemoryTypes = [
  { value: "", label: "All LTM Types" },
  { value: "interaction", label: "Interaction" },
  { value: "summary", label: "Summary" },
  { value: "short_term_migration", label: "STM Migration" }
];

function formatDateTime(value?: string) {
  if (!value) return "---";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
}

export function MemoriesPage() {
  const [query, setQuery] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const currentSessionId = useUiStore((state) => state.currentSessionId);
  const setCurrentSessionId = useUiStore((state) => state.setCurrentSessionId);

  const params = new URLSearchParams();
  if (query) params.set("q", query);
  if (typeFilter) params.set("mem_type_filter", typeFilter);
  params.set("limit", "50");

  const sessionsQuery = useQuery({ queryKey: ["sessions"], queryFn: api.getSessions });
  const longTermQuery = useQuery({ queryKey: ["memories", query, typeFilter], queryFn: () => api.getMemories(params) });
  const shortTermQuery = useQuery({ queryKey: ["short-term"], queryFn: api.getShortTermMemories });
  const healthQuery = useQuery({ queryKey: ["memory-health"], queryFn: api.getMemoryHealth });

  const cleanupMutation = useMutation({
    mutationFn: api.cleanupShortTermMemories,
    onSuccess: () => {
      shortTermQuery.refetch();
      longTermQuery.refetch();
      healthQuery.refetch();
    }
  });

  const clearMutation = useMutation({
    mutationFn: api.clearMemories,
    onSuccess: () => {
      longTermQuery.refetch();
      healthQuery.refetch();
    }
  });

  const longTerm = (longTermQuery.data as any)?.items ?? [];
  const longTermTotal = (longTermQuery.data as any)?.total ?? longTerm.length;
  const shortTerm = (shortTermQuery.data as any)?.items ?? [];
  const sessions = (sessionsQuery.data ?? []) as any[];
  const memoryHealth = (healthQuery.data ?? {}) as any;

  return (
    <div className="grid gap-8 lg:grid-cols-[300px_1fr]">
      <aside className="space-y-6">
        <div className="rounded-none border border-white/5 bg-night p-6 shadow-glass">
          <h2 className="text-xs font-bold uppercase tracking-[0.25em] text-slate">Session History</h2>
          <div className="mt-6 flex flex-col gap-3">
            {sessions.length === 0 ? (
              <p className="text-xs text-slate/50">No sessions found.</p>
            ) : (
              sessions.map((session) => (
                <button
                  key={session.id}
                  onClick={() => startTransition(() => setCurrentSessionId(session.id))}
                  className={`group rounded-none p-4 text-left transition-all duration-300 ${
                    currentSessionId === session.id
                      ? "bg-ember text-white shadow-glass"
                      : "bg-white/5 text-slate hover:bg-white/10 hover:text-mist"
                  }`}
                >
                  <p className="truncate text-sm font-bold">{session.title || "Untitled Session"}</p>
                  <p className="mt-1 text-[10px] uppercase tracking-wider opacity-60">
                    {session.updated_at ? new Date(session.updated_at).toLocaleDateString() : "New Session"}
                  </p>
                </button>
              ))
            )}
          </div>
        </div>

        <div className="rounded-none border border-white/5 bg-night p-6 shadow-glass uppercase text-[10px] tracking-widest text-slate">
          <h3 className="mb-4 font-bold text-mist">Memory Health</h3>
          <div className="space-y-2">
            <div className="flex justify-between"><span>LTM Entries</span><span>{memoryHealth.memory_count ?? 0}</span></div>
            <div className="flex justify-between"><span>Active STM</span><span>{shortTerm.length}</span></div>
            <div className="flex justify-between"><span>Persistent</span><span>{memoryHealth.is_persistent ? "yes" : "no"}</span></div>
          </div>
        </div>
      </aside>

      <div className="space-y-8">
        <div className="flex flex-col gap-4 rounded-none border border-white/5 bg-night p-6 shadow-glass xl:flex-row xl:items-end">
          <label className="flex flex-1 flex-col gap-2">
            <span className="text-[10px] uppercase tracking-[0.25em] text-slate">Search LTM</span>
            <div className="relative">
              <span className="material-symbols-outlined absolute left-4 top-1/2 -translate-y-1/2 text-lg text-slate">search</span>
              <input
                value={query}
                onChange={(event) => setQuery(event.target.value)}
                placeholder="Search LTM content..."
                className="w-full rounded-squircle-md border border-white/5 bg-input py-3 pl-12 pr-4 text-sm text-mist outline-none transition-all shadow-inner focus:border-ember/50"
              />
            </div>
          </label>

          <label className="flex min-w-[200px] flex-col gap-2">
            <span className="text-[10px] uppercase tracking-[0.25em] text-slate">Type Filter</span>
            <select
              value={typeFilter}
              onChange={(event) => setTypeFilter(event.target.value)}
              className="rounded-squircle-md border border-white/5 bg-input px-4 py-3 text-sm text-mist outline-none transition-all focus:border-ember/50"
            >
              {longTermMemoryTypes.map((option) => (
                <option key={option.value || "all"} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>

          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => cleanupMutation.mutate()}
              className="rounded-none border border-pine/30 bg-pine/20 px-5 py-3 text-xs font-bold uppercase tracking-widest text-pine transition-all hover:bg-pine hover:text-white"
            >
              {cleanupMutation.isPending ? "Cleaning..." : "Cleanup STM"}
            </button>
            <button
              onClick={() => clearMutation.mutate()}
              className="rounded-none border border-warning/30 bg-warning/20 px-5 py-3 text-xs font-bold uppercase tracking-widest text-warning transition-all hover:bg-warning hover:text-white"
            >
              {clearMutation.isPending ? "Wiping..." : "Wipe LTM"}
            </button>
          </div>
        </div>

        <div className="grid gap-4 md:grid-cols-3">
          <div className="rounded-none border border-white/5 bg-white/[0.02] p-4 shadow-glass">
            <p className="text-[10px] uppercase tracking-[0.25em] text-slate">Visible LTM</p>
            <p className="mt-3 text-2xl font-bold text-mist">{longTerm.length}</p>
          </div>
          <div className="rounded-none border border-white/5 bg-white/[0.02] p-4 shadow-glass">
            <p className="text-[10px] uppercase tracking-[0.25em] text-slate">Total LTM Hits</p>
            <p className="mt-3 text-2xl font-bold text-mist">{longTermTotal}</p>
          </div>
          <div className="rounded-none border border-white/5 bg-white/[0.02] p-4 shadow-glass">
            <p className="text-[10px] uppercase tracking-[0.25em] text-slate">Active STM</p>
            <p className="mt-3 text-2xl font-bold text-mist">{shortTerm.length}</p>
          </div>
        </div>

        <div className="grid gap-8 xl:grid-cols-2">
          <section className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <h3 className="text-sm font-bold uppercase tracking-[0.25em] text-slate">Short-Term Buffer</h3>
              <span className="text-[10px] uppercase tracking-[0.25em] text-slate">{shortTerm.length} active</span>
            </div>
            <div className="max-h-[38rem] space-y-3 overflow-y-auto rounded-none border border-white/5 bg-white/[0.02] p-5 shadow-inner">
              {shortTerm.length === 0 ? (
                <p className="py-12 text-center text-sm uppercase tracking-widest text-slate opacity-40">Buffer Empty</p>
              ) : (
                shortTerm.map((entry: any) => (
                  <article key={entry.id} className="rounded-none border border-white/5 bg-night p-4 shadow-glass transition-all hover:border-white/10">
                    <div className="flex flex-wrap items-center gap-2 text-[9px] uppercase tracking-[0.22em] text-slate">
                      <span className="border border-white/10 px-2 py-1 text-ember">{entry.category}</span>
                      <span className="border border-white/10 px-2 py-1">{entry.importance}</span>
                      <span className="border border-white/10 px-2 py-1">{entry.migrated ? "migrated" : "active"}</span>
                    </div>
                    <p className="mt-4 whitespace-pre-wrap break-words text-sm leading-relaxed text-mist">{entry.content}</p>
                    <div className="mt-4 grid gap-2 text-[10px] text-slate sm:grid-cols-2">
                      <p className="truncate uppercase tracking-[0.18em]">Created: {formatDateTime(entry.created_at)}</p>
                      <p className="truncate uppercase tracking-[0.18em]">Expires: {formatDateTime(entry.expires_at)}</p>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>

          <section className="space-y-4">
            <div className="flex items-center justify-between px-2">
              <h3 className="text-sm font-bold uppercase tracking-[0.25em] text-slate">Long-Term Storage</h3>
              <span className="text-[10px] uppercase tracking-[0.25em] text-slate">{longTermTotal} matched</span>
            </div>
            <div className="max-h-[38rem] space-y-3 overflow-y-auto rounded-none border border-white/5 bg-white/[0.02] p-5 shadow-inner">
              {longTerm.length === 0 ? (
                <p className="py-12 text-center text-sm uppercase tracking-widest text-slate opacity-40">No entries found</p>
              ) : (
                longTerm.map((entry: any) => (
                  <article key={entry.id} className="group relative overflow-hidden rounded-none border border-white/10 bg-night p-4 shadow-glass">
                    <div className="absolute left-0 top-0 h-full w-1 bg-ember/30 transition-all group-hover:bg-ember" />
                    <div className="flex flex-wrap items-center gap-2 pl-2 text-[9px] uppercase tracking-[0.22em] text-slate">
                      <span className="border border-white/10 px-2 py-1">{entry.mem_type || "interaction"}</span>
                      <span className="border border-white/10 px-2 py-1">{entry.role}</span>
                      <span className="border border-white/10 px-2 py-1">{entry.label}</span>
                      <span className="border border-ember/20 px-2 py-1 text-ember">Score {entry.relevance_score?.toFixed(2) ?? "0.00"}</span>
                    </div>
                    <p className="mt-4 whitespace-pre-wrap break-words pl-2 text-sm leading-relaxed text-mist">{entry.content}</p>
                    <div className="mt-4 flex flex-wrap items-center gap-3 pl-2 text-[10px] uppercase tracking-[0.18em] text-slate">
                      <span>{formatDateTime(entry.timestamp)}</span>
                      <span className="break-all text-slate/70">{entry.id}</span>
                    </div>
                  </article>
                ))
              )}
            </div>
          </section>
        </div>
      </div>
    </div>
  );
}
