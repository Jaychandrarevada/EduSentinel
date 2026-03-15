"use client";

import { Bell, Search } from "lucide-react";
import { useAuthStore } from "@/store/authStore";

interface Props {
  title: string;
}

export default function TopBar({ title }: Props) {
  const user = useAuthStore((s) => s.user);

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between border-b border-gray-200 bg-white/80 px-6 backdrop-blur">
      <h1 className="text-lg font-semibold text-gray-900">{title}</h1>

      <div className="flex items-center gap-3">
        {/* Search */}
        <div className="hidden items-center gap-2 rounded-lg border border-gray-200 bg-gray-50 px-3 py-1.5 sm:flex">
          <Search className="h-3.5 w-3.5 text-gray-400" />
          <input
            placeholder="Search students…"
            className="w-40 bg-transparent text-sm text-gray-700 placeholder-gray-400 focus:outline-none"
          />
        </div>

        {/* Notifications */}
        <button className="relative rounded-lg p-2 text-gray-500 hover:bg-gray-100">
          <Bell className="h-4 w-4" />
          <span className="absolute right-1.5 top-1.5 h-2 w-2 rounded-full bg-red-500" />
        </button>

        {/* Avatar */}
        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-indigo-600 text-xs font-bold text-white">
          {user?.full_name.charAt(0).toUpperCase()}
        </div>
      </div>
    </header>
  );
}
