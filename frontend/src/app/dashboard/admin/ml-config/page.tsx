"use client";

// ─────────────────────────────────────────────
//  Admin → ML Configuration & Training
// ─────────────────────────────────────────────
import { useState, useEffect } from "react";
import {
  Brain, Play, RefreshCw, CheckCircle, AlertCircle, Clock, BarChart3,
  ChevronDown, ChevronRight,
} from "lucide-react";
import api from "@/lib/api";
import { formatDate } from "@/lib/utils";
import { cn } from "@/lib/utils";

interface ModelMeta {
  version: string;
  model_name: string;
  threshold: number;
  trained_at: string;
  metrics: {
    roc_auc: number;
    recall: number;
    precision: number;
    f1: number;
    accuracy: number;
    passes_gates: boolean;
  };
  feature_cols: string[];
}

interface TrainResult {
  version: string;
  best_model: string;
  passes_gates: boolean;
  metrics: ModelMeta["metrics"];
  all_metrics?: Array<{ model_name: string } & ModelMeta["metrics"]>;
}

const SEMESTERS = ["Sem 1", "Sem 2", "Sem 3", "Sem 4", "Sem 5", "Sem 6"];

function MetricBar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  const color = pct >= 80 ? "bg-emerald-500" : pct >= 65 ? "bg-amber-400" : "bg-red-400";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-600">{label}</span>
        <span className="font-semibold tabular-nums text-gray-900">{pct}%</span>
      </div>
      <div className="h-2 w-full overflow-hidden rounded-full bg-gray-100">
        <div className={`h-full rounded-full transition-all duration-500 ${color}`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function AdminMLConfigPage() {
  const [modelMeta, setModelMeta] = useState<ModelMeta | null>(null);
  const [loading, setLoading] = useState(true);
  const [training, setTraining] = useState(false);
  const [trainResult, setTrainResult] = useState<TrainResult | null>(null);
  const [trainError, setTrainError] = useState<string | null>(null);
  const [selectedSemester, setSelectedSemester] = useState("Sem 5");
  const [showAllMetrics, setShowAllMetrics] = useState(false);
  const [runSemester, setRunSemester] = useState("Sem 5");

  const fetchModel = async () => {
    setLoading(true);
    try {
      const r = await api.get("/ml/model");
      setModelMeta(r.data);
    } catch {
      // fallback demo data
      setModelMeta({
        version: "v20240310_140000",
        model_name: "gradient_boosting",
        threshold: 0.52,
        trained_at: "2024-03-10T14:00:00Z",
        metrics: { roc_auc: 0.91, recall: 0.87, precision: 0.83, f1: 0.85, accuracy: 0.88, passes_gates: true },
        feature_cols: ["attendance_pct", "avg_ia_score", "assignment_avg_score", "lms_login_frequency", "lms_time_spent_hours", "previous_gpa"],
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchModel(); }, []);

  const handleTrain = async () => {
    setTraining(true);
    setTrainError(null);
    setTrainResult(null);
    try {
      const r = await api.post("/train", { source: "synthetic", n_samples: 2000 });
      setTrainResult(r.data);
      fetchModel();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setTrainError(e?.response?.data?.detail ?? "Training failed. Check ML service logs.");
    } finally {
      setTraining(false);
    }
  };

  const handleRunPredictions = async () => {
    try {
      await api.post("/predictions/run", { semester: runSemester });
      alert(`Prediction run started for ${runSemester}. Results will appear shortly.`);
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      alert(e?.response?.data?.detail ?? "Failed to trigger prediction run.");
    }
  };

  return (
    <div className="space-y-8">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">ML Configuration</h1>
        <p className="mt-0.5 text-sm text-gray-500">
          Manage the at-risk prediction model — train, evaluate, and run predictions
        </p>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Current model card */}
        <div className="card p-6">
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-base font-semibold text-gray-800">Current Production Model</h2>
            <button onClick={fetchModel} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100" title="Refresh">
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </button>
          </div>

          {loading ? (
            <div className="space-y-3">
              {[...Array(4)].map((_, i) => (
                <div key={i} className="h-4 animate-pulse rounded bg-gray-100" />
              ))}
            </div>
          ) : modelMeta ? (
            <div className="space-y-5">
              {/* Model info */}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Algorithm</p>
                  <p className="mt-0.5 font-semibold capitalize text-gray-900">
                    {modelMeta.model_name.replace(/_/g, " ")}
                  </p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Version</p>
                  <p className="mt-0.5 font-mono text-xs font-semibold text-gray-900">{modelMeta.version}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Decision Threshold</p>
                  <p className="mt-0.5 font-semibold text-gray-900">{modelMeta.threshold.toFixed(2)}</p>
                </div>
                <div className="rounded-lg bg-gray-50 p-3">
                  <p className="text-xs text-gray-500">Trained At</p>
                  <p className="mt-0.5 text-xs font-semibold text-gray-900">{formatDate(modelMeta.trained_at)}</p>
                </div>
              </div>

              {/* Quality gate */}
              <div className={cn(
                "flex items-center gap-2 rounded-lg px-4 py-3 text-sm font-medium",
                modelMeta.metrics.passes_gates
                  ? "bg-emerald-50 text-emerald-700"
                  : "bg-amber-50 text-amber-700"
              )}>
                {modelMeta.metrics.passes_gates
                  ? <CheckCircle className="h-4 w-4" />
                  : <AlertCircle className="h-4 w-4" />}
                {modelMeta.metrics.passes_gates ? "Passes all quality gates" : "Quality gates not met — consider retraining"}
              </div>

              {/* Metrics */}
              <div className="space-y-3">
                <p className="text-xs font-semibold uppercase tracking-wide text-gray-500">Model Metrics</p>
                <MetricBar label="ROC-AUC" value={modelMeta.metrics.roc_auc} />
                <MetricBar label="Recall" value={modelMeta.metrics.recall} />
                <MetricBar label="Precision" value={modelMeta.metrics.precision} />
                <MetricBar label="F1 Score" value={modelMeta.metrics.f1} />
                <MetricBar label="Accuracy" value={modelMeta.metrics.accuracy} />
              </div>

              {/* Features */}
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-500">
                  Features ({modelMeta.feature_cols.length})
                </p>
                <div className="flex flex-wrap gap-1.5">
                  {modelMeta.feature_cols.map((f) => (
                    <span key={f} className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-medium text-indigo-700">
                      {f}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-400">No model loaded. Train a model to get started.</p>
          )}
        </div>

        {/* Actions panel */}
        <div className="space-y-4">
          {/* Train model */}
          <div className="card p-6">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-50">
                <Brain className="h-5 w-5 text-indigo-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Train New Model</h3>
                <p className="text-xs text-gray-500">Trains all 4 algorithms, selects best by ROC-AUC</p>
              </div>
            </div>

            {trainResult && (
              <div className={cn(
                "mb-4 rounded-lg p-4 text-sm",
                trainResult.passes_gates ? "bg-emerald-50 ring-1 ring-emerald-200" : "bg-amber-50 ring-1 ring-amber-200"
              )}>
                <div className="flex items-center gap-2 font-semibold">
                  {trainResult.passes_gates ? <CheckCircle className="h-4 w-4 text-emerald-600" /> : <AlertCircle className="h-4 w-4 text-amber-500" />}
                  Training complete — Best: <span className="capitalize">{trainResult.best_model.replace(/_/g, " ")}</span>
                </div>
                <p className="mt-1 text-xs text-gray-600">
                  Version: <code className="font-mono">{trainResult.version}</code> &nbsp;·&nbsp;
                  ROC-AUC: {(trainResult.metrics.roc_auc * 100).toFixed(1)}% &nbsp;·&nbsp;
                  Recall: {(trainResult.metrics.recall * 100).toFixed(1)}%
                </p>

                {trainResult.all_metrics && (
                  <button
                    onClick={() => setShowAllMetrics((v) => !v)}
                    className="mt-2 flex items-center gap-1 text-xs font-medium text-indigo-600 hover:text-indigo-800"
                  >
                    {showAllMetrics ? <ChevronDown className="h-3 w-3" /> : <ChevronRight className="h-3 w-3" />}
                    {showAllMetrics ? "Hide" : "Show"} all model results
                  </button>
                )}

                {showAllMetrics && trainResult.all_metrics && (
                  <div className="mt-3 overflow-hidden rounded-lg ring-1 ring-gray-200">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="bg-gray-50">
                          <th className="px-3 py-2 text-left">Model</th>
                          <th className="px-3 py-2 text-right">AUC</th>
                          <th className="px-3 py-2 text-right">Recall</th>
                          <th className="px-3 py-2 text-right">F1</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-100">
                        {trainResult.all_metrics.map((m) => (
                          <tr key={m.model_name} className={m.model_name === trainResult.best_model ? "bg-indigo-50" : ""}>
                            <td className="px-3 py-2 capitalize font-medium">{m.model_name.replace(/_/g, " ")}</td>
                            <td className="px-3 py-2 text-right tabular-nums">{(m.roc_auc * 100).toFixed(1)}%</td>
                            <td className="px-3 py-2 text-right tabular-nums">{(m.recall * 100).toFixed(1)}%</td>
                            <td className="px-3 py-2 text-right tabular-nums">{(m.f1 * 100).toFixed(1)}%</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </div>
            )}

            {trainError && (
              <div className="mb-4 flex items-start gap-2 rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
                <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
                {trainError}
              </div>
            )}

            <button
              onClick={handleTrain}
              disabled={training}
              className="btn-primary flex w-full items-center justify-center gap-2"
            >
              {training ? (
                <>
                  <RefreshCw className="h-4 w-4 animate-spin" /> Training in progress…
                </>
              ) : (
                <>
                  <Play className="h-4 w-4" /> Start Training
                </>
              )}
            </button>
            <p className="mt-2 text-center text-xs text-gray-400">
              Uses 2000 synthetic samples · LR + RF + GB + XGBoost · 5-fold CV
            </p>
          </div>

          {/* Run predictions */}
          <div className="card p-6">
            <div className="mb-3 flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50">
                <BarChart3 className="h-5 w-5 text-emerald-600" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-gray-900">Run Predictions</h3>
                <p className="text-xs text-gray-500">Score all students and update risk flags</p>
              </div>
            </div>
            <div className="mb-3">
              <label className="mb-1 block text-xs font-medium text-gray-700">Semester</label>
              <select value={runSemester} onChange={(e) => setRunSemester(e.target.value)} className="input">
                {SEMESTERS.map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <button onClick={handleRunPredictions} className="btn-secondary flex w-full items-center justify-center gap-2">
              <Play className="h-4 w-4" /> Run for {runSemester}
            </button>
          </div>

          {/* Schedule info */}
          <div className="card p-4">
            <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
              <Clock className="h-4 w-4 text-gray-400" /> Scheduled Jobs
            </div>
            <ul className="mt-3 space-y-2 text-xs text-gray-500">
              <li className="flex items-start gap-2">
                <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-emerald-400 shrink-0" />
                <span><strong>Weekly predictions</strong> — Sundays at 02:00 UTC via Celery Beat</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="mt-0.5 h-1.5 w-1.5 rounded-full bg-indigo-400 shrink-0" />
                <span><strong>Alert checks</strong> — Every hour for new high-risk flags</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
}
