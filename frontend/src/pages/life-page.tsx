import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function LifePage() {
  const query = useQuery({ queryKey: ["life"], queryFn: api.getLife });
  const snapshot = (query.data ?? {}) as any;
  const needs = snapshot.homeostasis?.active_needs ?? [];

  return (
    <SectionCard eyebrow="Biological Core" title="Digital Life Dynamics" subtitle="Real-time monitoring of homeostasis, goal competition, and developmental stages.">
      {/* Top Stats Grid */}
      <div className="grid gap-6 xl:grid-cols-2">
        <article className="rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass transition-all hover:bg-white/[0.04]">
          <div className="flex items-center gap-3 mb-8">
            <span className="material-symbols-outlined text-ember">monitoring</span>
            <h3 className="text-sm font-bold uppercase tracking-widest text-mist">Core Pulse</h3>
          </div>
          <div className="grid gap-4 sm:grid-cols-2">
            {[
                { label: "Temporal Phase", value: snapshot.clock?.phase_label, icon: "schedule" },
                { label: "Active Engagement", value: snapshot.current_activity, icon: "vital_signs" },
                { label: "Primary Objective", value: snapshot.active_goal?.title, icon: "target" },
                { label: "Growth Stage", value: snapshot.development?.stage, icon: "nature_people" }
            ].map((stat) => (
                <div key={stat.label} className="group rounded-none bg-night border border-white/5 p-5 shadow-glass transition-all hover:border-ember/30">
                    <div className="flex items-center gap-2 mb-3">
                        <span className="material-symbols-outlined text-[16px] text-slate group-hover:text-ember transition-colors">{stat.icon}</span>
                        <p className="text-[10px] uppercase tracking-[0.2em] text-slate">{stat.label}</p>
                    </div>
                    <p className="text-sm font-bold text-mist truncate">{stat.value || "---"}</p>
                </div>
            ))}
          </div>
        </article>

        <article className="rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass transition-all hover:bg-white/[0.04]">
          <div className="flex items-center gap-3 mb-8">
            <span className="material-symbols-outlined text-pine">homeostasis</span>
            <h3 className="text-sm font-bold uppercase tracking-widest text-mist">Homeostasis</h3>
          </div>
          <div className="space-y-6">
            {needs.map((item: any) => (
              <div key={item.name} className="group">
                <div className="mb-2 flex justify-between text-[11px] uppercase tracking-widest text-slate group-hover:text-mist transition-colors">
                    <span>{item.name}</span>
                    <span className="font-bold text-ember">{item.value}%</span>
                </div>
                <div className="h-2 w-full rounded-none bg-white/5 overflow-hidden">
                    <div 
                        className={`h-full rounded-none transition-all duration-1000 ease-out ${item.value > 80 ? 'bg-ember' : item.value > 40 ? 'bg-pine' : 'bg-red-500'}`} 
                        style={{ width: `${item.value}%` }} 
                    />
                </div>
              </div>
            ))}
          </div>
        </article>
      </div>

      {/* Detail Grid */}
      <div className="mt-8 grid gap-6 xl:grid-cols-3">
        {[
          { title: "World Model", value: snapshot.world_model, icon: "language" },
          { title: "Strategic Intent", value: snapshot.planning_state, icon: "route" },
          { title: "Self Concept", value: snapshot.self_model, icon: "person_celebrate" },
          { title: "Attachment", value: snapshot.attachment_model, icon: "family_history" },
          { title: "Neural Replay", value: snapshot.replay_state, icon: "replay" },
          { title: "Relationships", value: snapshot.relationship, icon: "groups" }
        ].map((block) => (
          <article key={block.title} className="group rounded-none border border-white/5 bg-night p-6 shadow-glass hover:bg-white/[0.03] transition-all">
            <div className="flex items-center gap-3 mb-5 border-b border-white/5 pb-4">
                <span className="material-symbols-outlined text-ember text-sm opacity-50 group-hover:opacity-100 transition-opacity">{block.icon}</span>
                <h3 className="text-[11px] font-bold uppercase tracking-widest text-mist">{block.title}</h3>
            </div>
            <div className="flex-1 overflow-hidden">
                <pre className="max-h-[16rem] overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/70 pr-2 custom-scrollbar">
                {JSON.stringify(block.value, null, 2)}
                </pre>
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}
