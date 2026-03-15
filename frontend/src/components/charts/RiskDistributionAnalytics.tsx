"use client";

// ─────────────────────────────────────────────
//  Risk Distribution Analytics
//  Donut + legend cards with percentages
// ─────────────────────────────────────────────
import {
  PieChart,
  Pie,
  Cell,
  Tooltip,
  ResponsiveContainer,
} from "recharts";

export interface RiskDistributionData {
  high: number;
  medium: number;
  low: number;
}

interface Props {
  data: RiskDistributionData;
}

const SLICES = [
  { key: "high",   label: "High Risk",   color: "#ef4444", bg: "bg-red-50",    text: "text-red-700",    dot: "bg-red-500" },
  { key: "medium", label: "Medium Risk", color: "#f59e0b", bg: "bg-amber-50",  text: "text-amber-700",  dot: "bg-amber-500" },
  { key: "low",    label: "Low Risk",    color: "#22c55e", bg: "bg-green-50",  text: "text-green-700",  dot: "bg-green-500" },
] as const;

interface CustomLabelProps {
  cx: number;
  cy: number;
  total: number;
}

function CenterLabel({ cx, cy, total }: CustomLabelProps) {
  return (
    <g>
      <text x={cx} y={cy - 8} textAnchor="middle" fill="#111827" fontSize={28} fontWeight={700}>
        {total}
      </text>
      <text x={cx} y={cy + 14} textAnchor="middle" fill="#6b7280" fontSize={12}>
        students
      </text>
    </g>
  );
}

export default function RiskDistributionAnalytics({ data }: Props) {
  const total = data.high + data.medium + data.low;
  const chartData = [
    { name: "High",   value: data.high },
    { name: "Medium", value: data.medium },
    { name: "Low",    value: data.low },
  ];

  return (
    <div className="flex flex-col gap-6 sm:flex-row sm:items-center">
      {/* Donut */}
      <div className="mx-auto w-full max-w-[220px] flex-shrink-0 sm:mx-0">
        <ResponsiveContainer width="100%" height={220}>
          <PieChart>
            <Pie
              data={chartData}
              cx="50%"
              cy="50%"
              innerRadius={68}
              outerRadius={100}
              paddingAngle={3}
              dataKey="value"
              startAngle={90}
              endAngle={-270}
            >
              {chartData.map((_, i) => (
                <Cell key={i} fill={SLICES[i].color} stroke="none" />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: number) => [
                `${value} students (${total > 0 ? ((value / total) * 100).toFixed(1) : 0}%)`,
                "",
              ]}
              contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
            />
            {total > 0 && (
              <CenterLabel cx={0} cy={0} total={total} />
            )}
          </PieChart>
        </ResponsiveContainer>
      </div>

      {/* Legend cards */}
      <div className="flex flex-col gap-3 flex-1">
        {SLICES.map((s) => {
          const value = data[s.key];
          const pct = total > 0 ? ((value / total) * 100).toFixed(1) : "0.0";
          return (
            <div
              key={s.key}
              className={`flex items-center justify-between rounded-xl px-4 py-3 ${s.bg}`}
            >
              <div className="flex items-center gap-2.5">
                <span className={`h-2.5 w-2.5 rounded-full ${s.dot}`} />
                <span className={`text-sm font-medium ${s.text}`}>{s.label}</span>
              </div>
              <div className="flex items-center gap-3">
                <span className={`text-lg font-bold ${s.text}`}>{value}</span>
                <span className={`text-xs ${s.text} opacity-70`}>{pct}%</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
