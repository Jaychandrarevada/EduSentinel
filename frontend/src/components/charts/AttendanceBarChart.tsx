"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  Cell,
  ResponsiveContainer,
} from "recharts";

export interface AttendancePoint {
  month: string;
  pct: number;
}

interface Props {
  data: AttendancePoint[];
  threshold?: number;
}

export default function AttendanceBarChart({ data, threshold = 75 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="month"
          tick={{ fontSize: 12, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
          width={36}
          tickFormatter={(v) => `${v}%`}
        />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
          formatter={(value: number) => [`${value.toFixed(1)}%`, "Attendance"]}
        />
        <ReferenceLine y={threshold} stroke="#f59e0b" strokeDasharray="4 4" />
        <Bar dataKey="pct" radius={[4, 4, 0, 0]} name="Attendance">
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={entry.pct >= threshold ? "#6366f1" : "#ef4444"}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
