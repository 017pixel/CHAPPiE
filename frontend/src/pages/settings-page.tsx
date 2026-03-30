import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function SettingsPage() {
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.getSettings });
  const layerQuery = useQuery({ queryKey: ["emotion-layer-config"], queryFn: api.getEmotionLayerConfig });
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.saveSettings(payload),
    onSuccess: () => settingsQuery.refetch()
  });

  const layerMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.updateEmotionLayerConfig(payload),
    onSuccess: () => layerQuery.refetch()
  });

  const settings = (settingsQuery.data ?? {}) as any;
  const layerRows = (layerQuery.data ?? []) as any[];

  return (
    <div className="space-y-8">
      <SectionCard eyebrow="System Configuration" title="Runtime & Model Parameters" subtitle="Configure the LLM provider, generation temperature, and memory retrieval thresholds.">
        <div className="grid gap-6 md:grid-cols-2 xl:grid-cols-4">
          {[
            { key: "llm_provider", value: settings.llm_provider, icon: "hub" },
            { key: "vllm_model", value: settings.vllm_model, icon: "model_training" },
            { key: "temperature", value: settings.temperature, icon: "thermostat" },
            { key: "memory_top_k", value: settings.memory_top_k, icon: "reorder" }
          ].map((item) => (
            <label key={item.key} className="group rounded-none bg-white/[0.02] border border-white/5 p-6 shadow-glass transition-all hover:border-ember/30">
              <div className="flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-[14px] text-slate group-hover:text-ember transition-colors">{item.icon}</span>
                <span className="text-[10px] uppercase font-bold tracking-widest text-slate">{item.key}</span>
              </div>
              <input
                defaultValue={String(item.value ?? "")}
                onChange={(event) => setDraft((current) => ({ ...current, [item.key]: event.target.value }))}
                className="w-full rounded-none border border-white/5 bg-input px-4 py-3 text-sm text-mist outline-none focus:border-ember/50 transition-all shadow-inner"
              />
            </label>
          ))}
        </div>
        <div className="mt-8 flex justify-end">
            <button 
                type="button" 
                onClick={() => saveMutation.mutate(draft)} 
                className="rounded-none bg-ember px-8 py-3 text-sm font-bold text-white shadow-lg transition-all hover:scale-105 active:scale-95"
            >
                {saveMutation.isPending ? "Applying Changes..." : "Sync Runtime Configuration"}
            </button>
        </div>
      </SectionCard>

      <SectionCard eyebrow="Steering Layers" title="Emotion Neural Mapping" subtitle="Fine-tune how emotional vectors influence the model's output distribution.">
        <div className="grid gap-6">
          {layerRows.map((row: any) => (
            <article key={row.emotion} className="group rounded-none border border-white/5 bg-white/[0.02] p-6 shadow-glass hover:bg-white/[0.04] transition-all">
              <div className="flex flex-wrap items-center justify-between gap-6 border-b border-white/5 pb-6 mb-6">
                <div className="flex items-center gap-4">
                    <div className="h-12 w-12 flex items-center justify-center rounded-none bg-night border border-white/5 text-ember shadow-glass">
                        <span className="material-symbols-outlined">psychology</span>
                    </div>
                    <div>
                        <h3 className="text-lg font-bold text-mist tracking-tight lowercase">{row.emotion}</h3>
                        <p className="text-[10px] uppercase tracking-widest text-slate mt-1">{row.surface_effect}</p>
                    </div>
                </div>
                <button
                  type="button"
                  onClick={() =>
                    layerMutation.mutate({
                      emotion_name: row.emotion,
                      layer_start: row.layer_start,
                      layer_end: row.layer_end,
                      default_alpha: row.default_alpha
                    })
                  }
                  className="rounded-none bg-white/5 border border-white/10 px-5 py-2.5 text-xs font-bold text-mist uppercase tracking-widest hover:bg-ember hover:text-white transition-all"
                >
                  Regenerate Mapping
                </button>
              </div>
              <div className="grid gap-6 md:grid-cols-3">
                <div className="rounded-none bg-night p-4 border border-white/5">
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-2">Layer Range</p>
                    <p className="text-sm font-code text-mist">{row.layer_start} → {row.layer_end}</p>
                </div>
                <div className="rounded-none bg-night p-4 border border-white/5">
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-2">Alpha Strength</p>
                    <p className="text-sm font-code text-mist">{row.default_alpha}</p>
                </div>
                <div className="rounded-none bg-night p-4 border border-white/5">
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-2">Vector ID</p>
                    <p className="text-sm font-code text-slate truncate">{row.vector_id || "N/A"}</p>
                </div>
              </div>
            </article>
          ))}
        </div>
      </SectionCard>
    </div>
  );
}
