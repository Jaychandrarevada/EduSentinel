"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  LayoutDashboard,
  Users,
  BarChart3,
  LineChart,
  Bell,
  LogOut,
  GraduationCap,
  ShieldCheck,
  ChevronRight,
  BookOpen,
  Brain,
  Upload,
  FileBarChart,
  BarChart2,
  Sparkles,
  Database,
  FlaskConical,
  Download,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAuthStore } from "@/store/authStore";

interface NavItem {
  label: string;
  href: string;
  icon: React.ElementType;
  roles?: string[];
  section?: string;
  badge?: string;
}

const NAV_ITEMS: NavItem[] = [
  // ── Admin ──────────────────────────────────
  { label: "Overview",          href: "/dashboard/admin",                     icon: LayoutDashboard, roles: ["ADMIN"], section: "Admin" },
  { label: "Students",          href: "/dashboard/admin/students",            icon: GraduationCap,   roles: ["ADMIN"], section: "Admin" },
  { label: "Courses",           href: "/dashboard/admin/courses",             icon: BookOpen,        roles: ["ADMIN"], section: "Admin" },
  { label: "Users",             href: "/dashboard/admin/users",               icon: Users,           roles: ["ADMIN"], section: "Admin" },
  { label: "Analytics",         href: "/dashboard/admin/analytics",           icon: BarChart2,       roles: ["ADMIN"], section: "Admin" },
  { label: "ML Config",         href: "/dashboard/admin/ml-config",           icon: Brain,           roles: ["ADMIN"], section: "Admin" },
  { label: "Model Evaluation",  href: "/dashboard/admin/model-evaluation",    icon: FlaskConical,    roles: ["ADMIN"], section: "Admin", badge: "New" },
  { label: "AI Explainability", href: "/dashboard/admin/ai-explainability",   icon: Sparkles,        roles: ["ADMIN"], section: "Admin", badge: "New" },
  { label: "Generate Data",     href: "/dashboard/admin/generate-data",       icon: Database,        roles: ["ADMIN"], section: "Admin" },

  // ── Faculty ────────────────────────────────
  { label: "My Students", href: "/dashboard/faculty",            icon: Users,        roles: ["FACULTY"], section: "Faculty" },
  { label: "Alerts",      href: "/dashboard/faculty/alerts",     icon: Bell,         roles: ["FACULTY"], section: "Faculty" },
  { label: "Upload Data", href: "/dashboard/faculty/upload",     icon: Upload,       roles: ["FACULTY"], section: "Faculty" },
  { label: "Reports",     href: "/dashboard/faculty/reports",    icon: FileBarChart, roles: ["FACULTY"], section: "Faculty" },
  { label: "Export CSV",  href: "/dashboard/faculty/export",     icon: Download,     roles: ["FACULTY"], section: "Faculty" },

  // ── Shared ─────────────────────────────────
  { label: "Analytics",   href: "/dashboard/analytics",  icon: BarChart3 },
  { label: "Insights",    href: "/dashboard/insights",   icon: LineChart },
  { label: "Alerts",      href: "/dashboard/alerts",     icon: Bell },
];

// Group items by section for visual separation
const SECTION_ORDER = ["Admin", "Faculty", undefined] as const;

export default function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuthStore();

  function handleLogout() {
    logout();
    router.push("/auth/login");
  }

  const visibleItems = NAV_ITEMS.filter(
    (item) => !item.roles || (user && item.roles.includes(user.role))
  );

  // Group by section
  const sections = SECTION_ORDER.map((section) => ({
    label: section,
    items: visibleItems.filter((i) => i.section === section),
  })).filter((s) => s.items.length > 0);

  return (
    <aside className="fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-white shadow-sm ring-1 ring-gray-200">
      {/* Logo */}
      <div className="flex h-16 items-center gap-3 border-b border-gray-100 px-6">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-indigo-500 to-violet-600">
          <ShieldCheck className="h-4 w-4 text-white" />
        </div>
        <div>
          <span className="block text-sm font-bold text-gray-900 leading-tight">EduSentinel</span>
          <span className="block text-xs text-gray-400">Learning Analytics</span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-3">
        {sections.map((section, si) => (
          <div key={si} className={si > 0 ? "mt-4" : ""}>
            {section.label && (
              <p className="mb-1 px-3 text-xs font-semibold uppercase tracking-wider text-gray-400">
                {section.label}
              </p>
            )}
            <div className="space-y-0.5">
              {section.items.map((item) => {
                const active = pathname === item.href || pathname.startsWith(item.href + "/");
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-all duration-150",
                      active
                        ? "bg-indigo-50 text-indigo-700"
                        : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
                    )}
                  >
                    <item.icon
                      className={cn(
                        "h-4 w-4 shrink-0",
                        active ? "text-indigo-600" : "text-gray-400 group-hover:text-gray-600"
                      )}
                    />
                    <span className="flex-1 truncate">{item.label}</span>
                    {item.badge && (
                      <span className="rounded-full bg-indigo-100 px-1.5 py-0.5 text-xs font-semibold text-indigo-600">
                        {item.badge}
                      </span>
                    )}
                    {active && !item.badge && (
                      <ChevronRight className="h-3.5 w-3.5 text-indigo-400" />
                    )}
                  </Link>
                );
              })}
            </div>
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-gray-100 p-3">
        <div className="mb-1 flex items-center gap-3 rounded-lg px-3 py-2">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-400 to-violet-500 text-xs font-bold text-white">
            {user?.full_name.charAt(0).toUpperCase()}
          </div>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-gray-900">{user?.full_name}</p>
            <p className="text-xs text-gray-400">{user?.role}</p>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium text-gray-500 hover:bg-red-50 hover:text-red-600 transition-colors"
        >
          <LogOut className="h-4 w-4" />
          Sign out
        </button>
      </div>
    </aside>
  );
}
