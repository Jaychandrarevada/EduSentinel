"use client";

// ─────────────────────────────────────────────
//  LMS Engagement Trend
//  Multi-metric area chart with toggle controls
// ─────────────────────────────────────────────
import { useState } from "react";
import {
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

export interface LmsEngagementPoint {
  period: string;       // e.g. "Week 1", "Jan"
  logins: number;
  content_views: number;
  hours_spent: number;  // study hours
  forum_posts: number;
}

interface Props {
  data: LmsEngagementPoint[];
}

type MetricKey = "logins" | "content_views" | "hours_spent" | "forum_posts";

const METRICS: {
  key: MetricKey;
  label: string;
  color: string;
  gradId: string;
  yAxis: "left" | "right";
}[] = [
  { key: "logins",        label: "Logins",        color: "#6366f1", gradId: "loginGrad",   yAxis: "left" },
  { key: "content_views", label: "Content Views",  color: "#10b981", gradId: "viewGrad",    yAxis: "left" },
  { key: "hours_spent",   label: "Hours Spent",    color: "#f59e0b", gradId: "hourGrad",    yAxis: "right" },
  { key: "forum_posts",   label: "Forum Posts",    color: "#ec4899", gradId: "forumGrad",   yAxis: "right" },
];

function ToggleChip({
  label,
  color,
  active,
  onClick,
}: {
  label: string;
  color: string;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-medium transition-all ${
        active ? "bg-gray-800 text-white" : "bg-gray-100 text-gray-500 hover:bg-gray-200"
      }`}
    >
      <span
        className="h-2 w-2 rounded-full flex-shrink-0"
        style={{ backgroundColor: active ? color : "#9ca3af" }}
      />
      {label}
    </button>
  );
}

export default function LmsEngagementTrendChart({ data }: Props) {
  const [visible, setVisible] = useState<Record<MetricKey, boolean>>({
    logins:        true,
    content_views: true,
    hours_spent:   false,
    forum_posts:   false,
  });

  const toggle = (key: MetricKey) =>
    setVisible((prev) => ({ ...prev, [key]: !prev[key] }));

  const activeMetrics = METRICS.filter((m) => visible[m.key]);

  return (
    <div className="space-y-4">
      {/* Toggle controls */}
      <div className="flex flex-wrap gap-2">
        {METRICS.map((m) => (
          <ToggleChip
            key={m.key}
            label={m.label}
            color={m.color}
            active={visible[m.key]}
            onClick={() => toggle(m.key)}
          />
        ))}
      </div>

      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 4, right: 20, left: 0, bottom: 0 }}>
          <defs>
            {METRICS.map((m) => (
              <linearGradient key={m.gradId} id={m.gradId} x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={m.color} stopOpacity={0.18} />
                <stop offset="95%" stopColor={m.color} stopOpacity={0} />
              </linearGradient>
            ))}
          </defs>

          <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" vertical={false} />
          <XAxis
            dataKey="period"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
          />
          {/* Left Y-axis: logins / views */}
          <YAxis
            yAxisId="left"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          {/* Right Y-axis: hours / forum posts */}
          <YAxis
            yAxisId="right"
            orientation="right"
            tick={{ fontSize: 11, fill: "#6b7280" }}
            axisLine={false}
            tickLine={false}
            width={36}
          />
          <Tooltip
            contentStyle={{ borderRadius: 8, border: "none", boxShadow: "0 4px 16px rgba(0,0,0,0.1)" }}
          />

          {activeMetrics.map((m) =>
            m.yAxis === "left" ? (
              <Area
                key={m.key}
                yAxisId="left"
                type="monotone"
                dataKey={m.key}
                name={m.label}
                stroke={m.color}
                strokeWidth={2}
                fill={`url(#${m.gradId})`}
                dot={false}
                activeDot={{ r: 4 }}
              />
            ) : (
              <Line
                key={m.key}
                yAxisId="right"
                type="monotone"
                dataKey={m.key}
                name={m.label}
                stroke={m.color}
                strokeWidth={2}
                dot={{ r: 3, fill: m.color, strokeWidth: 0 }}
                strokeDasharray={m.key === "forum_posts" ? "4 3" : undefined}
              />
            )
          )}

          {activeMetrics.length === 0 && (
            <ReferenceLine yAxisId="left" y={0} stroke="transparent" />
          )}
        </ComposedChart>
      </ResponsiveContainer>

      <p className="text-center text-[10px] text-gray-400">
        Toggle metrics above · Areas use left axis · Lines use right axis
      </p>
    </div>
  );
}
