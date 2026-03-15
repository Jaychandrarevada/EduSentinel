// ─────────────────────────────────────────────
//  Attendance Trend – Line Chart (Recharts)
// ─────────────────────────────────────────────
"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";
import { TrendPoint } from "@/types";

interface Props {
  data: TrendPoint[];
  threshold?: number;  // e.g. 75 for the attendance requirement line
}

export default function AttendanceTrendChart({
  data,
  threshold = 75,
}: Props) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <LineChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" />
        <XAxis dataKey="week" tick={{ fontSize: 12 }} />
        <YAxis domain={[0, 100]} unit="%" tick={{ fontSize: 12 }} />
        <Tooltip formatter={(v: number) => [`${v}%`, "Attendance"]} />
        <ReferenceLine
          y={threshold}
          stroke="#ef4444"
          strokeDasharray="4 4"
          label={{ value: `${threshold}% min`, position: "insideTopRight", fontSize: 11 }}
        />
        <Line
          type="monotone"
          dataKey="value"
          stroke="#6366f1"
          strokeWidth={2}
          dot={{ r: 3 }}
          activeDot={{ r: 5 }}
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
