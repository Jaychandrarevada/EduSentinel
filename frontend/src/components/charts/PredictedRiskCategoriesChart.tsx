"use client";

// ─────────────────────────────────────────────
//  Predicted Risk Categories
//  Stacked bar by department/semester + trend line
// ─────────────────────────────────────────────
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";

export interface RiskCategoryPoint {
  group: string;    // department name or "Sem 1" etc.
  high: number;
  medium: number;
  low: number;
  total: number;
}

interface Props {
  data: RiskCategoryPoint[];
  groupLabel?: string; // e.g. "Department" or "Semester"
}

interface TooltipEntry {
  name: string;
  value: number;
  color: string;
  payload: RiskCategoryPoint;
}

function CustomTooltip({
  active,
  payload,
  label,
}: {
  active?: boolean;
  payload?: TooltipEntry[];
  label?: string;
}) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload as RiskCategoryPoint | undefined;
  if (!p) return null;

  const highPct  = p.total > 0 ? ((p.high   / p.total) * 100).toFixed(1) : "0";
  const medPct   = p.total > 0 ? ((p.medium / p.total) * 100).toFixed(1) : "0";
  const lowPct   = p.total > 0 ? ((p.low    / p.total) * 100).toFixed(1) : "0";

  return (
    <div className="rounded-xl bg-white p-3 shadow-lg ring-1 ring-gray-200 text-xs min-w-[160px]">
      <p className="mb-2 font-semibold text-gray-900">{label}</p>
      <div className="space-y-1">
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="h-2 w-2 rounded-full bg-red-500" />High
          </span>
          <span className="font-medium text-gray-800">{p.high} <span className="text-gray-400">({highPct}%)</span></span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="h-2 w-2 rounded-full bg-amber-400" />Medium
          </span>
          <span className="font-medium text-gray-800">{p.medium} <span className="text-gray-400">({medPct}%)</span></span>
        </div>
        <div className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5 text-gray-600">
            <span className="h-2 w-2 rounded-full bg-green-500" />Low
          </span>
          <span className="font-medium text-gray-800">{p.low} <span className="text-gray-400">({lowPct}%)</span></span>
        </div>
        <div className="mt-1.5 border-t border-gray-100 pt-1.5 flex items-center justify-between">
          <span className="text-gray-500">Total</span>
          <span className="font-semibold text-gray-800">{p.total}</span>
        </div>
      </div>
    </div>
  );
}

// Compute high-risk % for the trend line
function withHighRiskPct(data: RiskCategoryPoint[]) {
  return data.map((d) => ({
    ...d,
    high_risk_pct: d.total > 0 ? Math.round((d.high / d.total) * 100) : 0,
  }));
}

export default function PredictedRiskCategoriesChart({
  data,
  groupLabel = "Group",
}: Props) {
  const enriched = withHighRiskPct(data);

  return (
    <div className="space-y-2">
      <ResponsiveContainer width="100%" height={300}>
        <ComposedChart
          data={enriched}
          margin={{ top: 4, right: 48, left: 0, bottom: 0 }}
        >
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="group"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          {/* Left: student counts */}
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          {/* Right: high-risk % */}
          <YAxis
            yAxisId="right"
            orientation="right"
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            tickFormatter={(v) => `${v}%`}
            width={42}
          />
          <Tooltip content={<CustomTooltip />} />
          <Legend
            iconType="square"
            iconSize={10}
            wrapperStyle={{ fontSize: 12, paddingTop: 8 }}
          />

          {/* Stacked bars */}
          <Bar yAxisId="left" dataKey="high"   name="High"   stackId="risk" fill="#ef4444" fillOpacity={0.85} radius={[0, 0, 0, 0]} />
          <Bar yAxisId="left" dataKey="medium" name="Medium" stackId="risk" fill="#f59e0b" fillOpacity={0.85} />
          <Bar yAxisId="left" dataKey="low"    name="Low"    stackId="risk" fill="#22c55e" fillOpacity={0.85} radius={[4, 4, 0, 0]} />

          {/* High-risk % trend line */}
          <Line
            yAxisId="right"
            type="monotone"
            dataKey="high_risk_pct"
            name="High Risk %"
            stroke="#7c3aed"
            strokeWidth={2}
            dot={{ r: 4, fill: "#7c3aed", strokeWidth: 0 }}
            strokeDasharray="5 3"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="text-center text-[10px] text-gray-400">
        Stacked bars: student counts by risk level per {groupLabel.toLowerCase()} ·
        Dashed line: high-risk % (right axis)
      </p>
    </div>
  );
}
