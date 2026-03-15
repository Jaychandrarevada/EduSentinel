"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import Sidebar from "@/components/layout/Sidebar";
import { useAuthStore } from "@/store/authStore";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuthStore();
  const router = useRouter();

  useEffect(() => {
    // Only redirect once the auth check is complete
    if (status === "unauthenticated") {
      router.replace("/auth/login");
    }
  }, [status, router]);

  // Still verifying — render nothing (no redirect)
  if (status === "initializing") return null;

  // Verified: not logged in — render nothing, redirect is queued
  if (status === "unauthenticated") return null;

  // Verified: logged in
  return (
    <div className="flex min-h-screen bg-gray-50">
      <Sidebar />
      <div className="flex flex-1 flex-col pl-64">
        <main className="flex-1 p-6 lg:p-8">{children}</main>
      </div>
    </div>
  );
}
