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

export interface AssignmentPoint {
  name: string;    // assignment title or number
  score: number;   // 0–100
  max_score: number;
  is_late: boolean;
}

interface Props {
  data: AssignmentPoint[];
}

export default function AssignmentScoreChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={260}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="name"
          tick={{ fontSize: 11, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          domain={[0, 100]}
          tick={{ fontSize: 12, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
          width={36}
          tickFormatter={(v) => `${v}`}
        />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
          formatter={(value: number, _: string, props) => [
            `${value} / ${props.payload.max_score}`,
            props.payload.is_late ? "Score (late)" : "Score",
          ]}
        />
        <ReferenceLine y={50} stroke="#fbbf24" strokeDasharray="4 4" />
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {data.map((entry, idx) => (
            <Cell
              key={idx}
              fill={entry.is_late ? "#f97316" : entry.score >= 50 ? "#6366f1" : "#ef4444"}
              fillOpacity={0.85}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
