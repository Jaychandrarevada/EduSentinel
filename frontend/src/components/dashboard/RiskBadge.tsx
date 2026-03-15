import { cn } from "@/lib/utils";
import { RiskLabel } from "@/types";

interface Props {
  label: RiskLabel | string;
  size?: "sm" | "md";
}

const styles: Record<string, string> = {
  HIGH:   "bg-red-100 text-red-700 ring-1 ring-red-200",
  MEDIUM: "bg-amber-100 text-amber-700 ring-1 ring-amber-200",
  LOW:    "bg-green-100 text-green-700 ring-1 ring-green-200",
};

const dots: Record<string, string> = {
  HIGH:   "bg-red-500",
  MEDIUM: "bg-amber-500",
  LOW:    "bg-green-500",
};

export default function RiskBadge({ label, size = "md" }: Props) {
  const key = label.toString().toUpperCase();
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full font-semibold",
        size === "sm" ? "px-2 py-0.5 text-xs" : "px-2.5 py-1 text-xs",
        styles[key] ?? "bg-gray-100 text-gray-600"
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", dots[key] ?? "bg-gray-400")} />
      {key.charAt(0) + key.slice(1).toLowerCase()}
    </span>
  );
}
