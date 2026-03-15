"use client";

// ─────────────────────────────────────────────
//  Assignment Score Timeline
//  Combo: bars (individual scores) + line (rolling avg)
// ─────────────────────────────────────────────
import {
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Legend,
  Cell,
  ResponsiveContainer,
} from "recharts";

export interface AssignmentTimelinePoint {
  label: string;      // e.g. "Assignment 1", "Week 3"
  score: number;      // 0–100 normalised percentage
  max_score: number;
  is_late: boolean;
  submitted: boolean;
}

interface Props {
  data: AssignmentTimelinePoint[];
  passingScore?: number; // default 50
}

function rollingAverage(data: AssignmentTimelinePoint[], window = 3): (number | null)[] {
  return data.map((_, i) => {
    const slice = data.slice(Math.max(0, i - window + 1), i + 1).filter((d) => d.submitted);
    if (slice.length === 0) return null;
    return Math.round(slice.reduce((s, d) => s + d.score, 0) / slice.length);
  });
}

interface TooltipEntry {
  name: string;
  value: number;
  payload: AssignmentTimelinePoint;
}

function CustomTooltip({ active, payload, label }: { active?: boolean; payload?: TooltipEntry[]; label?: string }) {
  if (!active || !payload?.length) return null;
  const p = payload[0]?.payload as AssignmentTimelinePoint | undefined;
  if (!p) return null;
  return (
    <div className="rounded-xl bg-white p-3 shadow-lg ring-1 ring-gray-200 text-xs">
      <p className="mb-1.5 font-semibold text-gray-900">{label}</p>
      {p.submitted ? (
        <>
          <p className="text-gray-600">
            Score: <span className="font-medium text-gray-800">{p.score} / {p.max_score}</span>
          </p>
          {p.is_late && (
            <p className="mt-0.5 font-medium text-orange-600">Submitted late</p>
          )}
        </>
      ) : (
        <p className="font-medium text-red-500">Not submitted</p>
      )}
      {payload[1] && (
        <p className="mt-0.5 text-gray-500">
          Rolling avg: <span className="font-medium">{payload[1].value}%</span>
        </p>
      )}
    </div>
  );
}

export default function AssignmentScoreTimelineChart({ data, passingScore = 50 }: Props) {
  const avgValues = rollingAverage(data);
  const enriched = data.map((d, i) => ({ ...d, rolling_avg: avgValues[i] }));

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm bg-indigo-500" />
          <span className="text-xs text-gray-500">On-time</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm bg-orange-400" />
          <span className="text-xs text-gray-500">Late submission</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-sm bg-red-300" />
          <span className="text-xs text-gray-500">Not submitted</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="block h-0.5 w-5 bg-violet-500" style={{ marginTop: 2 }} />
          <span className="text-xs text-gray-500">Rolling avg</span>
        </div>
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={enriched} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="label"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[0, 100]}
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={36}
            tickFormatter={(v) => `${v}%`}
          />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine y={passingScore} stroke="#fbbf24" strokeDasharray="4 4" strokeWidth={1.5} />

          <Bar dataKey="score" radius={[4, 4, 0, 0]} maxBarSize={36}>
            {enriched.map((entry, idx) => (
              <Cell
                key={idx}
                fill={
                  !entry.submitted
                    ? "#fca5a5"
                    : entry.is_late
                    ? "#fb923c"
                    : entry.score >= passingScore
                    ? "#6366f1"
                    : "#ef4444"
                }
                fillOpacity={0.85}
              />
            ))}
          </Bar>

          <Line
            type="monotone"
            dataKey="rolling_avg"
            stroke="#7c3aed"
            strokeWidth={2}
            dot={{ r: 3, fill: "#7c3aed", strokeWidth: 0 }}
            connectNulls
            name="Rolling avg"
          />
        </ComposedChart>
      </ResponsiveContainer>

      <p className="text-center text-[10px] text-gray-400">
        Dashed line: passing score ({passingScore}%) · Line: 3-assignment rolling average
      </p>
    </div>
  );
}
