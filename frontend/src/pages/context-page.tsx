import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function ContextPage() {
  const query = useQuery({ queryKey: ["context-files"], queryFn: api.getContextFiles });
  const data = (query.data ?? {}) as Record<string, string>;

  return (
    <SectionCard eyebrow="Intelligence Context" title="Active Personality & Soul" subtitle="Real-time access to the core personality files and user preferences.">
      <div className="grid gap-6 lg:grid-cols-3">
        {["soul", "user", "preferences"].map((key) => (
          <article key={key} className="flex flex-col rounded-none bg-white/[0.03] border border-white/5 p-6 shadow-glass hover:bg-white/[0.05] transition-all">
            <div className="flex items-center gap-3 mb-5 border-b border-white/5 pb-4">
              <span className="material-symbols-outlined text-ember text-sm">{key === 'soul' ? 'psychology' : key === 'user' ? 'person' : 'settings_heart'}</span>
              <h3 className="text-sm font-bold uppercase tracking-widest text-mist">{key}</h3>
            </div>
            <div className="flex-1 overflow-hidden">
                <pre className="h-full max-h-[32rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate/80 custom-scrollbar pr-2 italic">
                {query.isLoading ? "Initializing neural pathways..." : data[key] ?? "No synchronization data found."}
                </pre>
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}
