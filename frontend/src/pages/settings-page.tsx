import { useMutation, useQuery } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

const PROVIDER_OPTIONS = [
  { value: "vllm", label: "vLLM (Local GPU)" },
  { value: "ollama", label: "Ollama (Local)" },
  { value: "groq", label: "Groq (Cloud)" },
];

interface SettingDef {
  key: string;
  label: string;
  type: "string" | "number" | "boolean" | "provider";
  group: string;
  icon: string;
}

const SETTINGS_GROUPS: { id: string; label: string }[] = [
  { id: "provider", label: "Provider & Models" },
  { id: "generation", label: "Generation" },
  { id: "memory", label: "Memory & Processing" },
  { id: "steering", label: "Steering" },
  { id: "intent", label: "Intent & Query" },
  { id: "training", label: "Training" },
  { id: "rate", label: "Rate Limits" },
];

const SETTINGS_DEFS: SettingDef[] = [
  { key: "llm_provider", label: "LLM Provider", type: "provider", group: "provider", icon: "hub" },
  { key: "vllm_model", label: "vLLM Model", type: "string", group: "provider", icon: "model_training" },
  { key: "vllm_url", label: "vLLM URL", type: "string", group: "provider", icon: "dns" },
  { key: "vllm_force_single_model", label: "Force Single Model", type: "boolean", group: "provider", icon: "lock" },
  { key: "ollama_model", label: "Ollama Model", type: "string", group: "provider", icon: "smart_toy" },
  { key: "ollama_host", label: "Ollama Host", type: "string", group: "provider", icon: "dns" },
  { key: "groq_model", label: "Groq Model", type: "string", group: "provider", icon: "cloud" },
  { key: "groq_format_model", label: "Groq Format Model", type: "string", group: "provider", icon: "cloud" },
  { key: "groq_memory_model", label: "Groq Memory Model", type: "string", group: "provider", icon: "cloud" },

  { key: "temperature", label: "Temperature", type: "number", group: "generation", icon: "thermostat" },
  { key: "repetition_penalty", label: "Repetition Penalty", type: "number", group: "generation", icon: "repeat" },
  { key: "max_tokens", label: "Max Tokens", type: "number", group: "generation", icon: "token" },
  { key: "chappie_thinking_token_limit", label: "Thinking Token Limit", type: "number", group: "generation", icon: "psychology" },
  { key: "chappie_answer_token_limit", label: "Answer Token Limit", type: "number", group: "generation", icon: "chat" },
  { key: "chain_of_thought", label: "Chain of Thought", type: "boolean", group: "generation", icon: "account_tree" },

  { key: "memory_top_k", label: "Memory Top-K", type: "number", group: "memory", icon: "reorder" },
  { key: "memory_min_relevance", label: "Min Relevance", type: "number", group: "memory", icon: "filter_alt" },
  { key: "enable_two_step_processing", label: "Two-Step Processing", type: "boolean", group: "memory", icon: "stairs" },
  { key: "memory_consolidation_enabled", label: "Consolidation", type: "boolean", group: "memory", icon: "merge" },
  { key: "memory_consolidation_max_tokens", label: "Consolidation Tokens", type: "number", group: "memory", icon: "data_usage" },
  { key: "stm_summary_threshold", label: "STM Summary Threshold", type: "number", group: "memory", icon: "summarize" },
  { key: "stm_summary_batch_size", label: "STM Batch Size", type: "number", group: "memory", icon: "batch_prediction" },
  { key: "history_max_messages", label: "Max History Messages", type: "number", group: "memory", icon: "history" },
  { key: "context_token_limit", label: "Context Token Limit", type: "number", group: "memory", icon: "data_object" },
  { key: "context_token_warning_threshold", label: "Token Warning Threshold", type: "number", group: "memory", icon: "warning" },

  { key: "enable_steering", label: "Enable Steering", type: "boolean", group: "steering", icon: "tune" },
  { key: "steering_model", label: "Steering Model", type: "string", group: "steering", icon: "model_training" },
  { key: "steering_quantize", label: "Steering Quantize (NF4)", type: "boolean", group: "steering", icon: "compress" },
  { key: "steering_context_length", label: "Steering Context Length", type: "number", group: "steering", icon: "straighten" },

  { key: "intent_provider", label: "Intent Provider", type: "provider", group: "intent", icon: "psychology" },
  { key: "intent_processor_model_vllm", label: "Intent Model (vLLM)", type: "string", group: "intent", icon: "smart_toy" },
  { key: "intent_processor_model_groq", label: "Intent Model (Groq)", type: "string", group: "intent", icon: "cloud" },
  { key: "intent_processor_model_ollama", label: "Intent Model (Ollama)", type: "string", group: "intent", icon: "smart_toy" },
  { key: "query_extraction_provider", label: "Query Extract. Provider", type: "provider", group: "intent", icon: "search" },

  { key: "training_use_global_settings", label: "Use Global Settings", type: "boolean", group: "training", icon: "settings" },
  { key: "training_chappie_model", label: "Training Model", type: "string", group: "training", icon: "model_training" },

  { key: "groq_requests_per_minute", label: "Groq RPM", type: "number", group: "rate", icon: "speed" },
  { key: "groq_tokens_per_minute", label: "Groq TPM", type: "number", group: "rate", icon: "token" },
];

function SettingInput({ def, value, onChange }: { def: SettingDef; value: any; onChange: (key: string, val: any) => void }) {
  if (def.type === "boolean") {
    return (
      <button
        onClick={() => onChange(def.key, !value)}
        className={`w-12 h-6 rounded-none border transition-all ${value ? "bg-ember border-ember" : "bg-white/10 border-white/20"}`}
      >
        <div className={`h-4 w-4 rounded-none bg-white transition-transform ${value ? "translate-x-6" : "translate-x-1"}`} />
      </button>
    );
  }
  if (def.type === "provider") {
    return (
      <select
        value={String(value ?? "")}
        onChange={(e) => onChange(def.key, e.target.value)}
        className="rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50"
      >
        <option value="">auto</option>
        {PROVIDER_OPTIONS.map((opt) => (
          <option key={opt.value} value={opt.value}>{opt.label}</option>
        ))}
      </select>
    );
  }
  if (def.type === "number") {
    return (
      <input
        type="number"
        value={value ?? ""}
        onChange={(e) => onChange(def.key, e.target.value === "" ? null : Number(e.target.value))}
        className="w-24 rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50 font-mono"
      />
    );
  }
  return (
    <input
      value={String(value ?? "")}
      onChange={(e) => onChange(def.key, e.target.value)}
      className="w-full rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50 font-mono"
    />
  );
}

export function SettingsPage() {
  const settingsQuery = useQuery({ queryKey: ["settings"], queryFn: api.getSettings });
  const layerQuery = useQuery({ queryKey: ["emotion-layer-config"], queryFn: api.getEmotionLayerConfig });
  const emotionQuery = useQuery({ queryKey: ["emotion-state"], queryFn: api.getEmotionState });

  const [filter, setFilter] = useState("");
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set(["provider", "generation", "memory"]));
  const [draft, setDraft] = useState<Record<string, any>>({});
  const [emotionValues, setEmotionValues] = useState<Record<string, number>>({});
  const [layerEdits, setLayerEdits] = useState<Record<string, { layer_start: number; layer_end: number; default_alpha: number }>>({});
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const saveMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.saveSettings(payload),
    onSuccess: () => settingsQuery.refetch(),
  });

  const layerMutation = useMutation({
    mutationFn: (payload: Record<string, unknown>) => api.updateEmotionLayerConfig(payload),
    onSuccess: () => layerQuery.refetch(),
  });

  const emotionMutation = useMutation({
    mutationFn: (payload: Record<string, number>) => api.setEmotionState(payload),
    onSuccess: () => emotionQuery.refetch(),
  });

  const settings = (settingsQuery.data ?? {}) as any;
  const layerRows = (layerQuery.data ?? []) as any[];
  const emotionState = (emotionQuery.data ?? { emotions: {}, steering: {} }) as any;
  const currentEmotions: Record<string, number> = emotionState.emotions ?? {};

  useEffect(() => {
    if (emotionState.emotions && Object.keys(emotionValues).length === 0) {
      setEmotionValues({ ...emotionState.emotions });
    }
  }, [emotionState.emotions]);

  useEffect(() => {
    if (layerRows.length > 0 && Object.keys(layerEdits).length === 0) {
      const edits: Record<string, any> = {};
      layerRows.forEach((row: any) => {
        edits[row.emotion] = { layer_start: row.layer_start, layer_end: row.layer_end, default_alpha: row.default_alpha };
      });
      setLayerEdits(edits);
    }
  }, [layerRows]);

  const handleSettingsChange = useCallback(
    (key: string, value: any) => {
      const updated = { ...draft, [key]: value };
      setDraft(updated);
      if (saveTimer.current) clearTimeout(saveTimer.current);
      saveTimer.current = setTimeout(() => {
        saveMutation.mutate(updated);
        setDraft({});
      }, 500);
    },
    [draft, saveMutation],
  );

  const handleEmotionChange = useCallback(
    (emotion: string, value: number) => {
      setEmotionValues((prev) => ({ ...prev, [emotion]: value }));
    },
    [],
  );

  const applyEmotion = useCallback(
    (emotion: string) => {
      const value = emotionValues[emotion];
      if (value === undefined) return;
      emotionMutation.mutate({ [emotion]: value });
    },
    [emotionValues, emotionMutation],
  );

  const handleLayerEdit = useCallback(
    (emotion: string, field: string, value: number) => {
      setLayerEdits((prev) => ({
        ...prev,
        [emotion]: { ...prev[emotion], [field]: value },
      }));
    },
    [],
  );

  const saveLayerEdit = useCallback(
    (emotion: string) => {
      const edit = layerEdits[emotion];
      if (!edit) return;
      layerMutation.mutate({ emotion_name: emotion, ...edit });
    },
    [layerEdits, layerMutation],
  );

  const toggleGroup = (groupId: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(groupId)) next.delete(groupId);
      else next.add(groupId);
      return next;
    });
  };

  const filteredDefs = useMemo(() => {
    if (!filter) return SETTINGS_DEFS;
    const lower = filter.toLowerCase();
    return SETTINGS_DEFS.filter(
      (d) => d.label.toLowerCase().includes(lower) || d.key.toLowerCase().includes(lower) || d.group.toLowerCase().includes(lower),
    );
  }, [filter]);

  const groupedDefs = useMemo(() => {
    const groups: Record<string, SettingDef[]> = {};
    for (const def of filteredDefs) {
      if (!groups[def.group]) groups[def.group] = [];
      groups[def.group].push(def);
    }
    return groups;
  }, [filteredDefs]);

  const getValue = (key: string) => (key in draft ? draft[key] : settings[key]);

  const EMOTION_META: Record<string, { label: string; icon: string; color: string }> = {
    happiness: { label: "Happiness", icon: "sentiment_satisfied", color: "#fbbf24" },
    trust: { label: "Trust", icon: "verified_user", color: "#34d399" },
    energy: { label: "Energy", icon: "bolt", color: "#f97316" },
    curiosity: { label: "Curiosity", icon: "explore", color: "#a78bfa" },
    frustration: { label: "Frustration", icon: "sentiment_dissatisfied", color: "#ef4444" },
    motivation: { label: "Motivation", icon: "rocket_launch", color: "#2dd4bf" },
    sadness: { label: "Sadness", icon: "sentiment_very_dissatisfied", color: "#64748b" },
  };

  return (
    <div className="space-y-8">
      {/* Settings Filter */}
      <div className="flex items-center gap-3 rounded-none border border-white/5 bg-night p-4">
        <span className="material-symbols-outlined text-slate">search</span>
        <input
          value={filter}
          onChange={(e) => setFilter(e.target.value)}
          placeholder="Filter settings..."
          className="flex-1 bg-transparent text-sm text-mist outline-none placeholder:text-slate/50"
        />
        {filter && (
          <button onClick={() => setFilter("")} className="text-slate hover:text-white">
            <span className="material-symbols-outlined text-sm">close</span>
          </button>
        )}
      </div>

      {/* Manual Emotion Control */}
      <SectionCard eyebrow="Live Emotion Control" title="Manual Emotion Steering" subtitle="Set CHAPPiE's emotional state directly. Adjust the slider, then click Apply to update each emotion.">
        <div className="space-y-2">
          {Object.entries(EMOTION_META).map(([key, meta]) => (
            <div key={key} className="flex items-center gap-4 rounded-none border border-white/5 bg-white/[0.02] px-4 py-3">
              <div className="flex items-center gap-2 w-32 shrink-0">
                <span className="material-symbols-outlined text-sm" style={{ color: meta.color }}>{meta.icon}</span>
                <span className="text-[10px] uppercase tracking-widest text-slate">{meta.label}</span>
              </div>
              <input
                type="range"
                min="0"
                max="100"
                value={emotionValues[key] ?? 50}
                onChange={(e) => handleEmotionChange(key, Number(e.target.value))}
                className="flex-1 h-1"
                style={{ accentColor: meta.color }}
              />
              <span className="w-10 text-right text-xs font-mono text-mist shrink-0">{emotionValues[key] ?? 50}</span>
              <button
                onClick={() => applyEmotion(key)}
                disabled={emotionMutation.isPending}
                className="shrink-0 rounded-none px-4 py-1.5 text-[10px] font-bold text-white uppercase tracking-widest transition-all hover:brightness-110 disabled:opacity-50"
                style={{ backgroundColor: meta.color, color: key === "sadness" || key === "happiness" ? "#1a1a2e" : "#fff" }}
              >
                Apply
              </button>
            </div>
          ))}
        </div>
        {emotionMutation.isPending && (
          <p className="mt-2 text-[10px] text-slate/70">Applying emotion...</p>
        )}
        {emotionState.steering && (
          <div className="mt-4 grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 text-[10px]">
            <div className="rounded-none bg-night/50 border border-white/5 p-3">
              <span className="text-slate">Dominant: </span>
              <span className="text-ember">{emotionState.steering.dominant_vector ?? "neutral"}</span>
              <span className="text-slate/60 ml-2">({emotionState.steering.dominant_strength ?? 0})</span>
            </div>
            <div className="rounded-none bg-night/50 border border-white/5 p-3">
              <span className="text-slate">Summary: </span>
              <span className="text-mist">{emotionState.steering.summary ?? "Neutral"}</span>
            </div>
            <div className="rounded-none bg-night/50 border border-white/5 p-3">
              <span className="text-slate">Active: </span>
              <span className="text-pine">{emotionState.steering.steering_active ? "Yes" : "No"}</span>
            </div>
          </div>
        )}
      </SectionCard>

      {/* Settings Sections */}
      {SETTINGS_GROUPS.map((group) => {
        const defs = groupedDefs[group.id];
        if (!defs || defs.length === 0) return null;
        return (
          <SectionCard key={group.id} eyebrow="" title={group.label} subtitle="">
            <button
              onClick={() => toggleGroup(group.id)}
              className="flex w-full items-center justify-between mb-4 text-xs uppercase tracking-widest text-slate hover:text-mist"
            >
              <span>{group.label}</span>
              <span className="material-symbols-outlined text-sm">
                {expandedGroups.has(group.id) ? "expand_less" : "expand_more"}
              </span>
            </button>
            {expandedGroups.has(group.id) && (
              <div className="grid gap-3 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
                {defs.map((def) => (
                  <label key={def.key} className="flex items-center justify-between gap-3 rounded-none border border-white/5 bg-white/[0.02] px-4 py-3 hover:border-ember/30 transition-all">
                    <div className="flex items-center gap-2 min-w-0">
                      <span className="material-symbols-outlined text-[14px] text-slate shrink-0">{def.icon}</span>
                      <span className="text-[10px] uppercase tracking-wider text-slate truncate">{def.label}</span>
                    </div>
                    <SettingInput def={def} value={getValue(def.key)} onChange={handleSettingsChange} />
                  </label>
                ))}
              </div>
            )}
          </SectionCard>
        );
      })}

      {/* Emotion Neural Mapping */}
      <SectionCard eyebrow="Steering Layers" title="Emotion Neural Mapping" subtitle="Fine-tune layer ranges and alpha strength for each emotion vector.">
        <div className="grid gap-4">
          {layerRows.map((row: any) => {
            const edit = layerEdits[row.emotion] || { layer_start: row.layer_start, layer_end: row.layer_end, default_alpha: row.default_alpha };
            return (
              <article key={row.emotion} className="rounded-none border border-white/5 bg-white/[0.02] p-5">
                <div className="flex flex-wrap items-center justify-between gap-4 mb-4">
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-bold text-mist lowercase">{row.emotion}</span>
                    <span className="text-[10px] text-slate/60">{row.surface_effect}</span>
                  </div>
                  <button
                    onClick={() => saveLayerEdit(row.emotion)}
                    className="rounded-none bg-ember px-4 py-1.5 text-[10px] font-bold text-white uppercase tracking-widest hover:brightness-110 transition-all"
                  >
                    Save
                  </button>
                </div>
                <div className="grid gap-3 grid-cols-1 sm:grid-cols-3">
                  <div>
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-1">Layer Start</p>
                    <input
                      type="number"
                      value={edit.layer_start}
                      onChange={(e) => handleLayerEdit(row.emotion, "layer_start", Number(e.target.value))}
                      className="w-full rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50 font-mono"
                    />
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-1">Layer End</p>
                    <input
                      type="number"
                      value={edit.layer_end}
                      onChange={(e) => handleLayerEdit(row.emotion, "layer_end", Number(e.target.value))}
                      className="w-full rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50 font-mono"
                    />
                  </div>
                  <div>
                    <p className="text-[9px] uppercase tracking-widest text-slate mb-1">Alpha</p>
                    <input
                      type="number"
                      step="0.01"
                      value={edit.default_alpha}
                      onChange={(e) => handleLayerEdit(row.emotion, "default_alpha", Number(e.target.value))}
                      className="w-full rounded-none border border-white/5 bg-input px-3 py-2 text-xs text-mist outline-none focus:border-ember/50 font-mono"
                    />
                  </div>
                </div>
              </article>
            );
          })}
        </div>
      </SectionCard>

      {saveMutation.isPending && (
        <div className="fixed bottom-6 right-6 rounded-none bg-ember px-5 py-3 text-xs font-bold text-white shadow-lg z-50">
          Saving settings...
        </div>
      )}
    </div>
  );
}
