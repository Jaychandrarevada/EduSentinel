"use client";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

export interface TrendDataPoint {
  label: string;        // e.g. "Week 1", "Feb", semester label
  attendance: number;   // 0–100
  marks: number;        // 0–100
  lms_engagement: number; // 0–100
}

interface Props {
  data: TrendDataPoint[];
  attendanceThreshold?: number;
}

export default function PerformanceTrendChart({ data, attendanceThreshold = 75 }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="label"
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
          formatter={(value: number) => [`${value.toFixed(1)}%`]}
        />
        <Legend iconType="circle" iconSize={8} />
        <ReferenceLine
          y={attendanceThreshold}
          stroke="#fbbf24"
          strokeDasharray="4 4"
          label={{ value: `${attendanceThreshold}% threshold`, fontSize: 11, fill: "#92400e" }}
        />
        <Line
          type="monotone"
          dataKey="attendance"
          stroke="#6366f1"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="Attendance"
        />
        <Line
          type="monotone"
          dataKey="marks"
          stroke="#10b981"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="Marks"
        />
        <Line
          type="monotone"
          dataKey="lms_engagement"
          stroke="#f59e0b"
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4 }}
          name="LMS Engagement"
          strokeDasharray="4 2"
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
