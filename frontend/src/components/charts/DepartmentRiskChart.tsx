"use client";

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import { DepartmentStat } from "@/hooks/useAnalytics";

interface Props {
  data: DepartmentStat[];
}

export default function DepartmentRiskChart({ data }: Props) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 4, right: 16, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
        <XAxis
          dataKey="department"
          tick={{ fontSize: 12, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 12, fill: "#6b7280" }}
          axisLine={false}
          tickLine={false}
          width={36}
        />
        <Tooltip
          contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
          formatter={(value: number, name: string) => [value, name === "high_risk_count" ? "High Risk" : "Total"]}
        />
        <Legend
          formatter={(value) => (value === "high_risk_count" ? "High Risk" : "Total Students")}
          iconType="circle"
          iconSize={8}
        />
        <Bar dataKey="total_students" fill="#e0e7ff" radius={[4, 4, 0, 0]} name="total_students" />
        <Bar dataKey="high_risk_count" fill="#ef4444" radius={[4, 4, 0, 0]} name="high_risk_count" />
      </BarChart>
    </ResponsiveContainer>
  );
}
