import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function DebugPage() {
  const query = useQuery({ queryKey: ["debug"], queryFn: api.getDebug, refetchInterval: 2000 });
  const data = (query.data ?? {}) as any;
  const lastMeta = data.last_assistant_message?.metadata ?? {};

  return (
    <div className="space-y-8">
      <SectionCard eyebrow="Neural Diagnostic" title="Brain Monitor" subtitle="Deep inspection of assistant metadata, attention mechanisms, and execution logs.">
        <div className="grid gap-6 xl:grid-cols-2">
          <article className="rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass transition-all hover:bg-white/[0.04]">
            <div className="flex items-center gap-3 mb-6">
                <span className="material-symbols-outlined text-ember text-sm">psychology</span>
                <h3 className="text-[10px] uppercase font-bold tracking-widest text-mist">Last Response Metadata</h3>
            </div>
            <div className="rounded-none bg-night/80 border border-white/5 p-6 h-full">
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate/80 pr-2 custom-scrollbar italic font-mono pr-2">
                    {JSON.stringify(lastMeta, null, 2)}
                </pre>
            </div>
          </article>

          <article className="rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass transition-all hover:bg-white/[0.04]">
            <div className="flex items-center gap-3 mb-6">
                <span className="material-symbols-outlined text-pine text-sm">history</span>
                <h3 className="text-[10px] uppercase font-bold tracking-widest text-mist">Execution Stream</h3>
            </div>
            <div className="rounded-none bg-night/80 border border-white/5 p-6 h-full">
                <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate/80 pr-2 custom-scrollbar font-mono italic">
                    {data.formatted_log ?? "Initializing stream..."}
                </pre>
            </div>
          </article>
        </div>
      </SectionCard>

      <SectionCard eyebrow="Neural Events" title="Activity Timeline" subtitle="Indexed event logs with structured payload inspection.">
        <div className="space-y-4">
          {(data.entries ?? []).map((entry: any, index: number) => (
            <article key={`${entry.category}-${index}`} className="group rounded-none border border-white/5 bg-night p-6 transition-all hover:bg-white/[0.03] hover:border-white/10">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <span className={`h-2 w-2 rounded-full ${entry.category === 'error' ? 'bg-red-500' : 'bg-ember'}`} />
                    <p className="text-sm font-bold text-mist tracking-tight lowercase">{entry.category}</p>
                </div>
                <span className="text-[9px] uppercase tracking-widest text-slate opacity-40">Entry #{index}</span>
              </div>
              <p className="text-sm text-slate mb-4 leading-relaxed">{entry.message}</p>
              <div className="rounded-none bg-white/[0.02] border border-white/5 p-4 overflow-hidden">
                  <pre className="max-h-[12rem] overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/60 pr-2 custom-scrollbar font-mono italic">
                    {JSON.stringify(entry.details ?? {}, null, 2)}
                  </pre>
              </div>
            </article>
          ))}
          {(data.entries ?? []).length === 0 && (
              <div className="py-20 text-center">
                  <span className="material-symbols-outlined text-slate/20 text-5xl">insights</span>
                  <p className="mt-4 text-xs uppercase tracking-widest text-slate/30">Quiet on the neural bus</p>
              </div>
          )}
        </div>
      </SectionCard>
    </div>
  );
}
