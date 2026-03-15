// ─────────────────────────────────────────────
//  StatCard – KPI summary card
// ─────────────────────────────────────────────
import { LucideIcon } from "lucide-react";
import { clsx } from "clsx";

interface Props {
  title: string;
  value: string | number;
  delta?: string;        // e.g. "+4 this week"
  deltaPositive?: boolean;
  icon: LucideIcon;
  iconColor?: string;
}

export default function StatCard({
  title,
  value,
  delta,
  deltaPositive,
  icon: Icon,
  iconColor = "text-indigo-600",
}: Props) {
  return (
    <div className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-gray-200">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-gray-500">{title}</p>
          <p className="mt-1 text-3xl font-bold text-gray-900">{value}</p>
          {delta && (
            <p
              className={clsx(
                "mt-1 text-xs font-medium",
                deltaPositive ? "text-green-600" : "text-red-600"
              )}
            >
              {delta}
            </p>
          )}
        </div>
        <div className={clsx("rounded-xl bg-gray-50 p-3", iconColor)}>
          <Icon size={22} />
        </div>
      </div>
    </div>
  );
}
