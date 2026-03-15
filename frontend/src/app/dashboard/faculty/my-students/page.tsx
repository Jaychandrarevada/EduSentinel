"use client";

// ─────────────────────────────────────────────
//  Faculty → My Students (detailed view with search & filters)
// ─────────────────────────────────────────────
import { redirect } from "next/navigation";

// This page provides a direct URL alias for the main faculty dashboard.
// All "my students" functionality lives at /dashboard/faculty.
export default function MyStudentsPage() {
  redirect("/dashboard/faculty");
}
