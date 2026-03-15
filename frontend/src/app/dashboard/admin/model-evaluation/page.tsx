"use client";

import { useState, useEffect, useCallback } from "react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
  RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
} from "recharts";
import {
  FlaskConical, Trophy, RefreshCw, Info, CheckCircle2,
  TrendingUp, Clock, Zap, AlertCircle,
} from "lucide-react";
import api from "@/lib/api";
import { ModelComparisonResult, ModelMetrics } from "@/types";

// ── colours per model ──────────────────────────────────────────────────────
const MODEL_COLORS: Record<string, string> = {
  "Logistic Regression": "#6366f1",
  "Random Forest":       "#10b981",
  "XGBoost":             "#f59e0b",
  "Gradient Boosting":   "#3b82f6",
};

const METRIC_LABELS: { key: keyof ModelMetrics; label: string; color: string }[] = [
  { key: "accuracy",  label: "Accuracy",  color: "#6366f1" },
  { key: "precision", label: "Precision", color: "#10b981" },
  { key: "recall",    label: "Recall",    color: "#f59e0b" },
  { key: "f1",        label: "F1 Score",  color: "#ef4444" },
  { key: "roc_auc",   label: "ROC-AUC",   color: "#8b5cf6" },
];

const DEMO_DATA: ModelComparisonResult = {
  models: [
    { name: "Logistic Regression", accuracy: 0.82, precision: 0.79, recall: 0.84, f1: 0.81, roc_auc: 0.88, training_time_sec: 1.2 },
    { name: "Random Forest",       accuracy: 0.89, precision: 0.87, recall: 0.91, f1: 0.89, roc_auc: 0.94, training_time_sec: 8.5 },
    { name: "XGBoost",             accuracy: 0.91, precision: 0.89, recall: 0.93, f1: 0.91, roc_auc: 0.96, training_time_sec: 12.3 },
  ],
  best_model: "XGBoost",
  best_metric: "roc_auc",
  comparison_date: new Date().toISOString(),
  data_source: "demo",
};

function pct(v: number) { return `${(v * 100).toFixed(1)}%`; }

function MetricCell({ value, best }: { value: number; best: boolean }) {
  return (
    <td className={`px-4 py-3 text-center text-sm font-semibold tabular-nums ${best ? "text-emerald-600" : "text-gray-700"}`}>
      <span className={best ? "inline-flex items-center gap-1" : ""}>
        {pct(value)}
        {best && <Trophy className="h-3 w-3 text-amber-500" />}
      </span>
    </td>
  );
}

export default function ModelEvaluationPage() {
  const [data, setData] = useState<ModelComparisonResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [training, setTraining] = useState(false);
  const [activeMetric, setActiveMetric] = useState<keyof ModelMetrics>("roc_auc");

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { data: res } = await api.get<ModelComparisonResult>("/ml/model-comparison");
      setData(res);
    } catch {
      setData(DEMO_DATA);
      setError("ML service offline — showing demo results.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  const handleTrainAll = async () => {
    setTraining(true);
    try {
      await api.post("/ml/train-all", { data_source: "synthetic", n_synthetic_samples: 1000 });
      setTimeout(fetchData, 3000);
    } catch {
      setError("Training request failed — check ML service.");
    } finally {
      setTraining(false);
    }
  };

  // Build bar chart data
  const barData = METRIC_LABELS.map(({ key, label }) => {
    const entry: Record<string, string | number> = { metric: label };
    (data ?? DEMO_DATA).models.forEach((m) => { entry[m.name] = +(m[key] as number * 100).toFixed(1); });
    return entry;
  });

  // Build radar data
  const radarData = METRIC_LABELS.map(({ key, label }) => {
    const entry: Record<string, string | number> = { metric: label };
    (data ?? DEMO_DATA).models.forEach((m) => { entry[m.name] = +(m[key] as number * 100).toFixed(1); });
    return entry;
  });

  // Best value per metric (for table highlighting)
  const bestPerMetric = (data ?? DEMO_DATA).models.reduce<Record<string, number>>((acc, m) => {
    METRIC_LABELS.forEach(({ key }) => {
      const k = key as string;
      const v = m[key] as number;
      if (!acc[k] || v > acc[k]) acc[k] = v;
    });
    return acc;
  }, {});

  const d = data ?? DEMO_DATA;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-violet-100">
            <FlaskConical className="h-5 w-5 text-violet-600" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-gray-900">Model Evaluation</h1>
            <p className="text-sm text-gray-500">Compare ML model performance across all metrics</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={fetchData}
            disabled={loading}
            className="inline-flex items-center gap-2 rounded-xl border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-600 hover:bg-gray-50 transition-all disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </button>
          <button
            onClick={handleTrainAll}
            disabled={training}
            className="inline-flex items-center gap-2 rounded-xl bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 transition-all disabled:opacity-50 shadow-sm shadow-violet-500/20"
          >
            <Zap className="h-4 w-4" />
            {training ? "Training…" : "Train All Models"}
          </button>
        </div>
      </div>

      {/* Error / demo notice */}
      {error && (
        <div className="flex items-center gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3">
          <AlertCircle className="h-4 w-4 shrink-0 text-amber-500" />
          <p className="text-sm text-amber-700">{error}</p>
        </div>
      )}

      {/* Best model banner */}
      {d && (
        <div className="flex items-center gap-4 rounded-2xl border border-emerald-200 bg-gradient-to-r from-emerald-50 to-teal-50 px-6 py-4">
          <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-emerald-100">
            <Trophy className="h-6 w-6 text-emerald-600" />
          </div>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600">Best Performing Model</p>
            <p className="text-xl font-bold text-gray-900">{d.best_model}</p>
            <p className="text-sm text-gray-500">
              Optimised for <span className="font-medium">{d.best_metric.replace("_", "-").toUpperCase()}</span>
              {" · "}
              <span className="text-emerald-700 font-semibold">{pct(d.models.find(m => m.name === d.best_model)?.roc_auc ?? 0)}</span> ROC-AUC
            </p>
          </div>
          {d.data_source === "demo" && (
            <span className="ml-auto rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
              Demo Data
            </span>
          )}
          {d.data_source === "registry" && (
            <span className="ml-auto rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold text-emerald-700 flex items-center gap-1">
              <CheckCircle2 className="h-3 w-3" /> Live Results
            </span>
          )}
        </div>
      )}

      {/* KPI row */}
      <div className="grid grid-cols-3 gap-4">
        {d.models.map((m) => (
          <div
            key={m.name}
            className={`card p-5 border-t-4 transition-all ${m.name === d.best_model ? "border-t-amber-400" : "border-t-transparent"}`}
          >
            <div className="flex items-center justify-between mb-3">
              <span className="text-sm font-semibold text-gray-700">{m.name}</span>
              {m.name === d.best_model && <Trophy className="h-4 w-4 text-amber-500" />}
            </div>
            <div className="grid grid-cols-2 gap-3">
              {METRIC_LABELS.map(({ key, label }) => (
                <div key={key}>
                  <p className="text-xs text-gray-400">{label}</p>
                  <p className={`text-lg font-bold tabular-nums ${(m[key] as number) === bestPerMetric[key] ? "text-emerald-600" : "text-gray-800"}`}>
                    {pct(m[key] as number)}
                  </p>
                </div>
              ))}
              {m.training_time_sec !== undefined && (
                <div>
                  <p className="text-xs text-gray-400 flex items-center gap-1"><Clock className="h-3 w-3" /> Train Time</p>
                  <p className="text-sm font-semibold text-gray-700">{m.training_time_sec}s</p>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Comparison table */}
      <div className="card overflow-hidden">
        <div className="flex items-center gap-3 border-b border-gray-100 px-6 py-4">
          <TrendingUp className="h-4 w-4 text-gray-400" />
          <h2 className="font-semibold text-gray-900">Full Metrics Comparison</h2>
          <span className="ml-auto flex items-center gap-1 text-xs text-gray-400">
            <Trophy className="h-3 w-3 text-amber-400" /> Best value highlighted
          </span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="table-header">
                <th className="px-6 py-3 text-left">Model</th>
                {METRIC_LABELS.map(({ label }) => (
                  <th key={label} className="px-4 py-3 text-center">{label}</th>
                ))}
                <th className="px-4 py-3 text-center">Train Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-50">
              {d.models.map((m) => (
                <tr key={m.name} className={`hover:bg-gray-50 transition-colors ${m.name === d.best_model ? "bg-amber-50/40" : ""}`}>
                  <td className="px-6 py-3">
                    <div className="flex items-center gap-2">
                      <span
                        className="h-2.5 w-2.5 rounded-full"
                        style={{ backgroundColor: MODEL_COLORS[m.name] ?? "#6b7280" }}
                      />
                      <span className="text-sm font-medium text-gray-900">{m.name}</span>
                      {m.name === d.best_model && (
                        <span className="rounded-full bg-amber-100 px-1.5 py-0.5 text-xs font-semibold text-amber-700">Best</span>
                      )}
                    </div>
                  </td>
                  {METRIC_LABELS.map(({ key }) => (
                    <MetricCell key={key} value={m[key] as number} best={(m[key] as number) === bestPerMetric[key]} />
                  ))}
                  <td className="px-4 py-3 text-center text-sm text-gray-500">
                    {m.training_time_sec !== undefined ? `${m.training_time_sec}s` : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Charts row */}
      <div className="grid grid-cols-2 gap-6">
        {/* Bar chart */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">Metric Comparison</h3>
            <div className="flex gap-1">
              {METRIC_LABELS.map(({ key, label }) => (
                <button
                  key={key}
                  onClick={() => setActiveMetric(key)}
                  className={`rounded-lg px-2 py-1 text-xs font-medium transition-all ${activeMetric === key ? "bg-indigo-100 text-indigo-700" : "text-gray-400 hover:text-gray-600"}`}
                >
                  {label}
                </button>
              ))}
            </div>
          </div>
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={barData} margin={{ top: 5, right: 10, bottom: 5, left: -10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f3f4f6" />
              <XAxis dataKey="metric" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <YAxis domain={[60, 100]} unit="%" tick={{ fontSize: 11, fill: "#9ca3af" }} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: "12px", border: "1px solid #e5e7eb" }} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              {d.models.map((m) => (
                <Bar key={m.name} dataKey={m.name} fill={MODEL_COLORS[m.name] ?? "#6b7280"} radius={[4, 4, 0, 0]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Radar chart */}
        <div className="card p-6">
          <h3 className="font-semibold text-gray-900 mb-4">Performance Radar</h3>
          <ResponsiveContainer width="100%" height={260}>
            <RadarChart data={radarData}>
              <PolarGrid stroke="#f3f4f6" />
              <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#6b7280" }} />
              <PolarRadiusAxis angle={30} domain={[60, 100]} tick={{ fontSize: 10, fill: "#9ca3af" }} />
              {d.models.map((m) => (
                <Radar
                  key={m.name}
                  name={m.name}
                  dataKey={m.name}
                  stroke={MODEL_COLORS[m.name] ?? "#6b7280"}
                  fill={MODEL_COLORS[m.name] ?? "#6b7280"}
                  fillOpacity={0.1}
                  strokeWidth={2}
                />
              ))}
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Tooltip formatter={(v) => `${v}%`} contentStyle={{ borderRadius: "12px", border: "1px solid #e5e7eb" }} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Info footer */}
      <div className="flex items-start gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3">
        <Info className="h-4 w-4 shrink-0 mt-0.5 text-blue-500" />
        <p className="text-sm text-blue-700">
          <span className="font-semibold">Recall is prioritised</span> — missing an at-risk student is more costly than a false alarm.
          ROC-AUC is the tiebreaker for overall discrimination ability. Click <span className="font-semibold">"Train All Models"</span> to run a fresh comparison on synthetic or live data.
        </p>
      </div>
    </div>
  );
}
