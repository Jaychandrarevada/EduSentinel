"use client";

// ─────────────────────────────────────────────
//  Attendance vs Performance – Scatter Chart
// ─────────────────────────────────────────────
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  ZAxis,
} from "recharts";

export interface ScatterStudent {
  student_name: string;
  attendance_pct: number;
  avg_marks_pct: number;
  risk_label: "HIGH" | "MEDIUM" | "LOW";
}

interface Props {
  data: ScatterStudent[];
  attendanceThreshold?: number;
  marksThreshold?: number;
}

const RISK_COLORS: Record<string, string> = {
  HIGH:   "#ef4444",
  MEDIUM: "#f59e0b",
  LOW:    "#22c55e",
};

interface TooltipPayload {
  payload: ScatterStudent;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: TooltipPayload[] }) {
  if (!active || !payload?.length) return null;
  const d = payload[0].payload;
  return (
    <div className="rounded-xl border-none bg-white p-3 shadow-lg ring-1 ring-gray-200">
      <p className="mb-1.5 text-sm font-semibold text-gray-900">{d.student_name}</p>
      <div className="space-y-0.5 text-xs text-gray-600">
        <p>Attendance: <span className="font-medium text-gray-800">{d.attendance_pct.toFixed(1)}%</span></p>
        <p>Marks: <span className="font-medium text-gray-800">{d.avg_marks_pct.toFixed(1)}%</span></p>
        <p>
          Risk:{" "}
          <span
            className="font-semibold"
            style={{ color: RISK_COLORS[d.risk_label] }}
          >
            {d.risk_label}
          </span>
        </p>
      </div>
    </div>
  );
}

export default function AttendanceVsPerformanceChart({
  data,
  attendanceThreshold = 75,
  marksThreshold = 50,
}: Props) {
  // Split by risk level for separate scatter series with distinct colors
  const high   = data.filter((d) => d.risk_label === "HIGH");
  const medium = data.filter((d) => d.risk_label === "MEDIUM");
  const low    = data.filter((d) => d.risk_label === "LOW");

  const series = [
    { label: "High Risk",   points: high,   color: "#ef4444" },
    { label: "Medium Risk", points: medium, color: "#f59e0b" },
    { label: "Low Risk",    points: low,    color: "#22c55e" },
  ];

  return (
    <div className="space-y-3">
      {/* Legend */}
      <div className="flex flex-wrap gap-4">
        {series.map((s) => (
          <div key={s.label} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: s.color }}
            />
            <span className="text-xs text-gray-500">{s.label}</span>
          </div>
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ScatterChart margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
          <XAxis
            type="number"
            dataKey="attendance_pct"
            domain={[0, 100]}
            name="Attendance"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            label={{ value: "Attendance (%)", position: "insideBottom", offset: -2, fill: "#9ca3af", fontSize: 11 }}
            height={40}
          />
          <YAxis
            type="number"
            dataKey="avg_marks_pct"
            domain={[0, 100]}
            name="Marks"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={40}
            label={{ value: "Marks (%)", angle: -90, position: "insideLeft", fill: "#9ca3af", fontSize: 11 }}
          />
          <ZAxis range={[40, 40]} />
          <Tooltip content={<CustomTooltip />} />
          <ReferenceLine x={attendanceThreshold} stroke="#6366f1" strokeDasharray="5 4" strokeWidth={1.5} />
          <ReferenceLine y={marksThreshold}      stroke="#10b981" strokeDasharray="5 4" strokeWidth={1.5} />

          {series.map((s) => (
            <Scatter
              key={s.label}
              name={s.label}
              data={s.points}
              fill={s.color}
              fillOpacity={0.75}
            />
          ))}
        </ScatterChart>
      </ResponsiveContainer>

      <p className="text-center text-[10px] text-gray-400">
        Dashed lines: attendance threshold ({attendanceThreshold}%) · marks threshold ({marksThreshold}%)
      </p>
    </div>
  );
}
