import { useMutation, useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

export function TrainingPage() {
  const statusQuery = useQuery({ queryKey: ["training-status"], queryFn: api.getTrainingStatus });
  const configQuery = useQuery({ queryKey: ["training-config"], queryFn: api.getTrainingConfig });
  const [draft, setDraft] = useState<Record<string, unknown>>({});

  const actionMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.runTrainingAction(payload),
    onSuccess: () => statusQuery.refetch()
  });

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.saveTrainingConfig(payload),
    onSuccess: () => configQuery.refetch()
  });

  const status = (statusQuery.data ?? {}) as any;
  const config = (configQuery.data ?? {}) as any;

  return (
    <div className="space-y-8">
      <SectionCard eyebrow="Neural Training" title="Daemon Control Center" subtitle="Manage the background training cycles, monitor active process PID, and view generation logs.">
        <div className="grid gap-6 md:grid-cols-4">
          {[
            { label: "Daemon Status", value: status.status_label, icon: "terminal" },
            { label: "Process ID", value: status.pid, icon: "fingerprint" },
            { label: "Cycle Count", value: status.loops, icon: "sync" },
            { label: "Memories Processed", value: status.memory_count, icon: "database" }
          ].map((item) => (
            <div key={item.label} className="group rounded-none border border-white/5 bg-white/[0.02] p-6 shadow-glass transition-all hover:bg-white/[0.04]">
              <div className="flex items-center gap-2 mb-4">
                <span className="material-symbols-outlined text-[14px] text-slate group-hover:text-ember transition-colors">{item.icon}</span>
                <p className="text-[10px] uppercase font-bold tracking-widest text-slate">{item.label}</p>
              </div>
              <p className="text-xl font-bold text-mist tracking-tight truncate">{item.value ?? "---"}</p>
            </div>
          ))}
        </div>
        
        <div className="mt-8 flex flex-wrap gap-4">
          <button 
            onClick={() => actionMutation.mutate({ action: "start" })} 
            className="rounded-none bg-pine px-6 py-3 text-xs font-bold text-white uppercase tracking-widest shadow-lg hover:scale-105 transition-all"
          >
            Initialize Daemon
          </button>
          <button 
            onClick={() => actionMutation.mutate({ action: "stop" })} 
            className="rounded-none bg-warning border border-warning/10 px-6 py-3 text-xs font-bold text-white uppercase tracking-widest hover:brightness-110 transition-all shadow-glass"
          >
            Kill Process
          </button>
          <button 
            onClick={() => actionMutation.mutate({ action: "restart", new: true })} 
            className="rounded-none bg-loading px-6 py-3 text-xs font-bold text-white uppercase tracking-widest shadow-lg hover:scale-105 transition-all"
          >
            Cold Restart
          </button>
          <button 
            onClick={() => actionMutation.mutate({ action: "logs", lines: 200 })} 
            className="rounded-none bg-white/5 border border-white/5 px-6 py-3 text-xs font-bold text-slate uppercase tracking-widest hover:bg-white/10 hover:text-mist transition-all"
          >
            Fetch Logs
          </button>
        </div>

        {(actionMutation.data as any)?.logs ? (
          <div className="mt-8 rounded-none border border-white/5 bg-ink p-8 shadow-inner overflow-hidden">
            <div className="flex items-center gap-3 mb-4">
                <span className="material-symbols-outlined text-ember text-sm translate-y-[1px]">description</span>
                <h4 className="text-[10px] uppercase font-bold tracking-widest text-slate">Process Output Log</h4>
            </div>
            <pre className="max-h-[32rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate/70 pr-4 custom-scrollbar font-mono italic">
                {(actionMutation.data as any).logs}
            </pre>
          </div>
        ) : null}
      </SectionCard>

      <SectionCard eyebrow="Configuration" title="Curriculum & Parameters" subtitle="Adjust the training focus area, persona overrides, and curriculum text.">
        <div className="grid gap-6 md:grid-cols-2">
          {[
            { key: "persona", value: config.persona, icon: "theater_comedy" },
            { key: "focus_area", value: config.focus_area, icon: "track_changes" },
            { key: "provider", value: config.provider, icon: "dns" },
            { key: "model_name", value: config.model_name, icon: "neurology" }
          ].map((item) => (
            <label key={item.key} className="group rounded-none border border-white/5 bg-white/[0.02] p-6 transition-all hover:border-ember/30">
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
        
        <label className="mt-6 block rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass transition-all hover:border-pine/30">
          <div className="flex items-center gap-2 mb-4">
            <span className="material-symbols-outlined text-[14px] text-slate">edit_note</span>
            <span className="text-[10px] uppercase font-bold tracking-widest text-slate">curriculum_text</span>
          </div>
          <textarea 
            defaultValue={config.curriculum_text ?? ""} 
            onChange={(event) => setDraft((current) => ({ ...current, curriculum_text: event.target.value }))} 
            className="w-full min-h-[16rem] rounded-none border border-white/5 bg-input p-6 text-sm text-mist outline-none focus:border-pine/50 transition-all shadow-inner italic leading-relaxed" 
          />
        </label>
        
        <div className="mt-8 flex justify-end">
          <button 
            type="button" 
            onClick={() => saveMutation.mutate({ ...config, ...draft })} 
            className="rounded-none bg-pine px-10 py-4 text-sm font-bold text-white shadow-xl transition-all hover:scale-105 active:scale-95"
          >
            {saveMutation.isPending ? "Updating Curriculum..." : "Save Neural Directives"}
          </button>
        </div>
      </SectionCard>
    </div>
  );
}
