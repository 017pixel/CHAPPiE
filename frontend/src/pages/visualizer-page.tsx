import { useQuery } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { VisualizerCanvas } from "../components/visualizer-canvas";
import { api } from "../services/api";

export function VisualizerPage() {
  const query = useQuery({ queryKey: ["visualizer"], queryFn: api.getVisualizer, refetchInterval: 1000 });
  const data = (query.data ?? {}) as any;
  const emotions = data.emotions ?? {};

  return (
    <SectionCard eyebrow="Spatial Neural Interface" title="3D Emotion Lattice" subtitle="High-fidelity 3D representation of the digital entity's current emotional state using React Three Fiber.">
      <div className="grid gap-8 xl:grid-cols-[1.5fr_1fr]">
        <div className="relative rounded-none border border-white/10 bg-night overflow-hidden shadow-glass min-h-[500px]">
          <div className="absolute top-6 left-6 z-10 flex gap-4">
              <div className="rounded-none bg-ember/20 border border-ember/30 px-3 py-1 flex items-center gap-2">
                  <div className="h-1.5 w-1.5 rounded-none bg-ember animate-pulse" />
                  <span className="text-[10px] font-bold text-ember uppercase tracking-widest">Live Rendering</span>
              </div>
          </div>
          <VisualizerCanvas
            happiness={Number(emotions.happiness ?? 50)}
            energy={Number(emotions.energy ?? 50)}
            frustration={Number(emotions.frustration ?? 0)}
          />
        </div>

        <div className="space-y-6">
            <article className="rounded-none border border-white/5 bg-white/[0.02] p-8 shadow-glass h-full">
                <div className="flex items-center gap-3 mb-6">
                    <span className="material-symbols-outlined text-ember text-sm">view_in_ar</span>
                    <h3 className="text-[10px] uppercase font-bold tracking-widest text-mist">Telemetry Matrix</h3>
                </div>
                <div className="grid gap-4 mb-8">
                    {Object.entries(emotions).map(([key, val]: any) => (
                        <div key={key} className="flex items-center justify-between p-3 rounded-none bg-night border border-white/5">
                            <span className="text-xs text-slate uppercase tracking-wider">{key}</span>
                            <span className="text-sm font-bold text-mist">{val}%</span>
                        </div>
                    ))}
                </div>
                <div className="rounded-none bg-night/80 border border-white/5 p-6 border-dashed">
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-4">Raw Lattice Data</p>
                    <pre className="max-h-[16rem] overflow-auto whitespace-pre-wrap text-[10px] leading-relaxed text-slate/50 pr-2 custom-scrollbar italic font-mono">
                        {JSON.stringify(data, null, 2)}
                    </pre>
                </div>
            </article>
        </div>
      </div>
    </SectionCard>
  );
}
