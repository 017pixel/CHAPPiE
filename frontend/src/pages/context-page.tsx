import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { SectionCard } from "../components/section-card";
import { api } from "../services/api";

const FILES = [
  { key: "soul", icon: "psychology", label: "soul" },
  { key: "user", icon: "person", label: "user" },
  { key: "preferences", icon: "settings_heart", label: "preferences" },
] as const;

export function ContextPage() {
  const query = useQuery({ queryKey: ["context-files"], queryFn: api.getContextFiles });
  const data = (query.data ?? {}) as Record<string, string>;
  const qc = useQueryClient();

  const [editing, setEditing] = useState<string | null>(null);
  const [editContent, setEditContent] = useState("");
  const [saveStatus, setSaveStatus] = useState<"idle" | "saving" | "saved" | "error">("idle");

  const mutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      api.updateContextFile(name, content),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["context-files"] });
      setEditing(null);
      setSaveStatus("saved");
      setTimeout(() => setSaveStatus("idle"), 2000);
    },
    onError: () => {
      setSaveStatus("error");
      setTimeout(() => setSaveStatus("idle"), 3000);
    },
  });

  function startEdit(key: string) {
    setEditContent(data[key] ?? "");
    setEditing(key);
    setSaveStatus("idle");
  }

  function cancelEdit() {
    setEditing(null);
    setSaveStatus("idle");
  }

  function saveEdit() {
    if (!editing) return;
    setSaveStatus("saving");
    mutation.mutate({ name: editing, content: editContent });
  }

  return (
    <SectionCard
      eyebrow="Intelligence Context"
      title="Active Personality & Soul"
      subtitle="Real-time access to the core personality files and user preferences. Edit and save changes directly."
    >
      <div className="grid gap-6 grid-cols-1 lg:grid-cols-3">
        {FILES.map(({ key, icon, label }) => (
          <article
            key={key}
            className="context-article flex flex-col rounded-none bg-white/[0.03] border border-white/5 p-6 shadow-glass hover:bg-white/[0.05] transition-all"
          >
            <div className="editor-header flex items-center justify-between gap-3 mb-5 border-b border-white/5 pb-4">
              <div className="flex items-center gap-3">
                <span className="material-symbols-outlined text-ember text-sm">{icon}</span>
                <h3 className="text-sm font-bold uppercase tracking-widest text-mist">{label}</h3>
              </div>

              <div className="flex items-center gap-2">
                {editing === key ? (
                  <>
                    <button
                      onClick={saveEdit}
                      disabled={mutation.isPending}
                      className="flex items-center gap-1 rounded-none bg-ember px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-white transition-all hover:bg-ember/80 disabled:opacity-50"
                    >
                      <span className="material-symbols-outlined text-base leading-none">
                        {mutation.isPending ? "hourglass_empty" : "check"}
                      </span>
                      Speichern
                    </button>
                    <button
                      onClick={cancelEdit}
                      className="flex items-center gap-1 rounded-none bg-white/10 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate transition-all hover:bg-white/20"
                    >
                      <span className="material-symbols-outlined text-base leading-none">close</span>
                      Abbrechen
                    </button>
                  </>
                ) : (
                  <>
                    <button
                      onClick={() => startEdit(key)}
                      className="flex items-center gap-1 rounded-none bg-white/5 px-3 py-1.5 text-xs font-bold uppercase tracking-wider text-slate transition-all hover:bg-ember hover:text-white"
                    >
                      <span className="material-symbols-outlined text-base leading-none">edit</span>
                      Bearbeiten
                    </button>
                  </>
                )}
              </div>
            </div>

            {saveStatus === "saved" && (
              <p className="mb-3 text-xs text-green-500">Gespeichert.</p>
            )}
            {saveStatus === "error" && (
              <p className="mb-3 text-xs text-red-500">Fehler beim Speichern.</p>
            )}

            <div className="flex-1 overflow-hidden">
              {editing === key ? (
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="h-full min-h-[20rem] w-full resize-y overflow-auto whitespace-pre-wrap rounded-none border border-white/10 bg-input p-4 text-[11px] leading-relaxed text-mist placeholder-slate/50 focus:border-ember focus:outline-none custom-scrollbar"
                  placeholder={`# ${label}.md content...`}
                  spellCheck={false}
                />
              ) : (
                <pre className="h-full max-h-[32rem] overflow-auto whitespace-pre-wrap text-[11px] leading-relaxed text-slate/80 custom-scrollbar pr-2 italic">
                  {query.isLoading
                    ? "Initializing neural pathways..."
                    : data[key] ?? "No synchronization data found."}
                </pre>
              )}
            </div>
          </article>
        ))}
      </div>
    </SectionCard>
  );
}
