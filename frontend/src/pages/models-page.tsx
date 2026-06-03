import { useState, useEffect } from "react";
import { api } from "../services/api";

interface FinetuneModel {
  name: string;
  target_person: string;
  status: string;
  adapter_ready: boolean;
  created: string;
  total_pairs: number;
  final_loss: number | null;
  adapter_path: string | null;
}

export function ModelsPage() {
  const [models, setModels] = useState<FinetuneModel[]>([]);
  const [activeAdapter, setActiveAdapter] = useState<string | null>(null);
  const [activeModelName, setActiveModelName] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<string | null>(null);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const res = await api.get("/finetune/models");
      setModels(res.data);
      const activeRes = await api.get("/finetune/active");
      setActiveAdapter(activeRes.data.active_adapter);
      setActiveModelName(activeRes.data.active_model_name);
    } catch (e) {
      console.error("Fehler beim Laden der Modelle:", e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchModels();
    const interval = setInterval(fetchModels, 5000);
    return () => clearInterval(interval);
  }, []);

  const handleSwitch = async (modelName: string | null) => {
    setSwitching(modelName || "base");
    try {
      await api.put("/finetune/active", { model_name: modelName });
      await fetchModels();
    } catch (e) {
      alert("Modell-Wechsel fehlgeschlagen: " + (e as Error).message);
    } finally {
      setSwitching(null);
    }
  };

  const handleDelete = async (name: string) => {
    if (!window.confirm(`Modell "${name}" wirklich loeschen?`)) return;
    try {
      await api.delete(`/finetune/models/${name}`);
      fetchModels();
    } catch (e) {
      alert("Loeschen fehlgeschlagen: " + (e as Error).message);
    }
  };

  const handleTrain = async (name: string) => {
    if (!window.confirm(`Training fuer "${name}" starten? Der Steering-Server wird gestoppt.`)) return;
    try {
      await api.post(`/finetune/models/${name}/train`);
      fetchModels();
    } catch (e) {
      alert("Training-Start fehlgeschlagen: " + (e as Error).message);
    }
  };

  const handleStop = async (name: string) => {
    try {
      await api.post(`/finetune/models/${name}/stop`);
      fetchModels();
    } catch (e) {
      alert("Stop fehlgeschlagen: " + (e as Error).message);
    }
  };

  if (loading && models.length === 0) {
    return <div className="p-8 text-center">Lade Modelle...</div>;
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Modelle & Fine-Tuning</h1>
        <div className="text-sm text-gray-400">
          Aktiv: {activeModelName || "Qwen3.5-4B (Base)"}
        </div>
      </div>

      <div className="bg-gray-900 rounded-lg overflow-hidden mb-6">
        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-800 text-gray-300">
              <th className="px-4 py-3 text-left">Name</th>
              <th className="px-4 py-3 text-left">Zielperson</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Adapter</th>
              <th className="px-4 py-3 text-left">Paare</th>
              <th className="px-4 py-3 text-left">Loss</th>
              <th className="px-4 py-3 text-left">Aktionen</th>
            </tr>
          </thead>
          <tbody>
            {/* Base Model Row */}
            <tr className={`border-t border-gray-700 ${!activeAdapter ? "bg-blue-900/20" : ""}`}>
              <td className="px-4 py-3 font-medium">Qwen3.5-4B (Base)</td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">
                <span className="px-2 py-1 rounded text-xs bg-green-900 text-green-300">bereit</span>
              </td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">-</td>
              <td className="px-4 py-3">
                <button
                  onClick={() => handleSwitch(null)}
                  disabled={switching !== null || !activeAdapter}
                  className="px-3 py-1 rounded text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
                >
                  {switching === "base" ? "Wechsle..." : "Aktivieren"}
                </button>
              </td>
            </tr>

            {/* Fine-tuned Models */}
            {models.map((model) => (
              <tr
                key={model.name}
                className={`border-t border-gray-700 ${model.adapter_path === activeAdapter ? "bg-blue-900/20" : ""}`}
              >
                <td className="px-4 py-3 font-medium">{model.name}</td>
                <td className="px-4 py-3">{model.target_person}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    model.status === "completed"
                      ? "bg-green-900 text-green-300"
                      : model.status === "training"
                      ? "bg-yellow-900 text-yellow-300"
                      : model.status === "failed"
                      ? "bg-red-900 text-red-300"
                      : "bg-gray-700 text-gray-300"
                  }`}>
                    {model.status}
                  </span>
                </td>
                <td className="px-4 py-3">
                  {model.adapter_ready ? (
                    <span className="text-green-400">✓</span>
                  ) : (
                    <span className="text-gray-500">✗</span>
                  )}
                </td>
                <td className="px-4 py-3">{model.total_pairs}</td>
                <td className="px-4 py-3">
                  {model.final_loss !== null ? model.final_loss.toFixed(3) : "-"}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    {model.adapter_ready && (
                      <button
                        onClick={() => handleSwitch(model.name)}
                        disabled={switching !== null || model.adapter_path === activeAdapter}
                        className="px-3 py-1 rounded text-xs bg-blue-600 hover:bg-blue-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
                      >
                        {switching === model.name ? "Wechsle..." : "Aktivieren"}
                      </button>
                    )}
                    {model.status === "training" ? (
                      <button
                        onClick={() => handleStop(model.name)}
                        className="px-3 py-1 rounded text-xs bg-red-600 hover:bg-red-500 transition-colors"
                      >
                        Stop
                      </button>
                    ) : (
                      <button
                        onClick={() => handleTrain(model.name)}
                        disabled={model.status === "training"}
                        className="px-3 py-1 rounded text-xs bg-green-600 hover:bg-green-500 disabled:bg-gray-700 disabled:cursor-not-allowed transition-colors"
                      >
                        Train
                      </button>
                    )}
                    <button
                      onClick={() => handleDelete(model.name)}
                      className="px-3 py-1 rounded text-xs bg-red-900 hover:bg-red-700 transition-colors"
                    >
                      Löschen
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {models.length === 0 && (
        <div className="text-center text-gray-500 py-8">
          Keine Modelle vorhanden. Starte ein Training ueber die API oder den Manager.
        </div>
      )}

      <div className="bg-gray-900 rounded-lg p-4 text-sm text-gray-400">
        <h3 className="font-bold text-gray-300 mb-2">Hinweise</h3>
        <ul className="list-disc list-inside space-y-1">
          <li>Base Model = Standard Qwen3.5-4B ohne Fine-Tuning</li>
          <li>Bei Modell-Wechsel wird der Steering-Server automatisch neu gestartet</li>
          <li>Training stoppt den Steering-Server (alle GPU-Ressourcen fuer Training)</li>
          <li>LoRA-Adapter sind ~30 MB, das Base Model bleibt unveraendert</li>
        </ul>
      </div>
    </div>
  );
}
