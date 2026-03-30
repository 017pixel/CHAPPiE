import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function GrowthPage() {
  const query = useQuery({ queryKey: ["growth"], queryFn: api.getGrowth });
  const data = (query.data ?? {}) as any;

  return (
    <SectionCard eyebrow="Evolutionary Path" title="Growth & Forecasting" subtitle="Strategic planning, social development arcs, and future timeline projections.">
      <div className="grid gap-6 xl:grid-cols-3">
        {[
          { title: "Planning State", value: data.planning_state, icon: "analytics" },
          { title: "Neural Forecast", value: data.forecast_state, icon: "query_stats" },
          { title: "Social Evolution", value: data.social_arc, icon: "share_location" },
          { title: "Timeline Synthesis", value: data.timeline_summary, icon: "timeline" },
          { title: "Maturity Level", value: data.development, icon: "upgrade" },
          { title: "Habitual Patterns", value: data.habit_dynamics, icon: "rebase_edit" }
        ].map((item) => (
          <article key={item.title} className="group rounded-none border border-white/5 bg-night p-6 shadow-glass hover:bg-white/[0.03] transition-all">
            <div className="flex items-center gap-3 mb-5 border-b border-white/5 pb-4">
                <span className="material-symbols-outlined text-ember text-sm opacity-50 group-hover:opacity-100 transition-opacity">{item.icon}</span>
                <h3 className="text-[11px] font-bold uppercase tracking-widest text-mist">{item.title}</h3>
            </div>
            <div className="flex-1 overflow-hidden">
                <pre className="max-h-[16rem] overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/70 pr-2 custom-scrollbar">
                {JSON.stringify(item.value, null, 2)}
                </pre>
            </div>
          </article>
        ))}
      </div>
      
      <article className="mt-8 rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass overflow-hidden">
        <div className="flex items-center gap-3 mb-6">
            <span className="material-symbols-outlined text-pine">history_edu</span>
            <h3 className="text-sm font-bold uppercase tracking-widest text-mist">Timeline Logs</h3>
        </div>
        <div className="rounded-none bg-night/50 border border-white/5 p-6">
            <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/60 pr-2 custom-scrollbar italic">
            {JSON.stringify(data.timeline_history ?? [], null, 2)}
            </pre>
        </div>
      </article>
    </SectionCard>
  );
}
