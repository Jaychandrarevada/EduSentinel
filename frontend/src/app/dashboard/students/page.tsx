"use client";

// ─────────────────────────────────────────────
//  /dashboard/students → Role-aware redirect
//  Admin sees full management page, Faculty sees their students
// ─────────────────────────────────────────────
import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/authStore";

export default function StudentsRootPage() {
  const router = useRouter();
  const { user } = useAuthStore();

  useEffect(() => {
    if (!user) return;
    if (user.role === "ADMIN") {
      router.replace("/dashboard/admin/students");
    } else {
      router.replace("/dashboard/faculty");
    }
  }, [user, router]);

  return null;
}
