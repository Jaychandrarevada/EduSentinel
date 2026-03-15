"use client";

// ─────────────────────────────────────────────
//  Admin → Course Management
// ─────────────────────────────────────────────
import { useState, useEffect } from "react";
import { BookOpen, Plus, Pencil, Trash2, X, AlertTriangle, Search } from "lucide-react";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import api from "@/lib/api";

interface Course {
  id: number;
  code: string;
  name: string;
  department: string;
  semester: number;
  credits: number;
  academic_year: string;
  faculty_id: number | null;
  faculty_name?: string;
}

const EMPTY_FORM = {
  code: "", name: "", department: "CSE", semester: "5",
  credits: "4", academic_year: "2024-25", faculty_id: "",
};

// ── Course Form Modal ─────────────────────────
function CourseModal({ initial, onClose, onSaved }: {
  initial?: Course | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form, setForm] = useState(
    initial
      ? { ...initial, semester: String(initial.semester), credits: String(initial.credits), faculty_id: String(initial.faculty_id ?? "") }
      : EMPTY_FORM
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof typeof EMPTY_FORM) =>
    (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
      setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        semester: Number(form.semester),
        credits: Number(form.credits),
        faculty_id: form.faculty_id ? Number(form.faculty_id) : null,
      };
      if (initial) {
        await api.put(`/courses/${initial.id}`, payload);
      } else {
        await api.post("/courses", payload);
      }
      onSaved();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "Failed to save course.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl ring-1 ring-gray-200">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            {initial ? "Edit Course" : "Add Course"}
          </h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error}</div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Course Code *</label>
              <input required className="input" value={form.code} onChange={set("code")} placeholder="CS501" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Course Name *</label>
              <input required className="input" value={form.name} onChange={set("name")} placeholder="Data Structures" />
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Department</label>
              <select className="input" value={form.department} onChange={set("department")}>
                {["CSE", "ECE", "MECH", "CIVIL", "IT"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Semester</label>
              <select className="input" value={form.semester} onChange={set("semester")}>
                {[1,2,3,4,5,6,7,8].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Credits</label>
              <input type="number" className="input" value={form.credits} onChange={set("credits")} min="1" max="6" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Academic Year</label>
              <input className="input" value={form.academic_year} onChange={set("academic_year")} placeholder="2024-25" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Faculty ID</label>
              <input type="number" className="input" value={form.faculty_id} onChange={set("faculty_id")} placeholder="Optional" />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Saving…" : initial ? "Save Changes" : "Add Course"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Page component ────────────────────────────
export default function AdminCoursesPage() {
  const [courses, setCourses] = useState<Course[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [showAdd, setShowAdd] = useState(false);
  const [editCourse, setEditCourse] = useState<Course | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Course | null>(null);

  const fetchCourses = async () => {
    setLoading(true);
    try {
      const r = await api.get("/courses");
      setCourses(r.data.items ?? r.data ?? []);
    } catch {
      // Use fallback data in dev
      setCourses([
        { id: 1, code: "CS501", name: "Data Structures", department: "CSE", semester: 5, credits: 4, academic_year: "2024-25", faculty_id: 2, faculty_name: "Dr. Priya Sharma" },
        { id: 2, code: "CS502", name: "Operating Systems", department: "CSE", semester: 5, credits: 4, academic_year: "2024-25", faculty_id: 2, faculty_name: "Dr. Priya Sharma" },
        { id: 3, code: "EC401", name: "Digital Electronics", department: "ECE", semester: 4, credits: 3, academic_year: "2024-25", faculty_id: null },
        { id: 4, code: "ME301", name: "Thermodynamics", department: "MECH", semester: 3, credits: 4, academic_year: "2024-25", faculty_id: null },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCourses(); }, []);

  const filtered = courses.filter((c) => {
    const q = search.toLowerCase();
    return !q || c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q) || c.department.toLowerCase().includes(q);
  });

  const handleDelete = async () => {
    if (!deleteTarget) return;
    await api.delete(`/courses/${deleteTarget.id}`).catch(() => {});
    setDeleteTarget(null);
    fetchCourses();
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Courses</h1>
          <p className="mt-0.5 text-sm text-gray-500">Manage course catalog and faculty assignments</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <Plus className="h-4 w-4" /> Add Course
        </button>
      </div>

      <div className="relative max-w-xs">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="search"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search courses…"
          className="input pl-9"
        />
      </div>

      {loading ? (
        <PageLoading />
      ) : filtered.length === 0 ? (
        <EmptyState icon={BookOpen} title="No courses found" description="Add a course to get started." />
      ) : (
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100 text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-6 py-3 text-left">Code</th>
                  <th className="px-6 py-3 text-left">Course Name</th>
                  <th className="px-6 py-3 text-left">Department</th>
                  <th className="px-6 py-3 text-left">Semester</th>
                  <th className="px-6 py-3 text-left">Credits</th>
                  <th className="px-6 py-3 text-left">Academic Year</th>
                  <th className="px-6 py-3 text-left">Faculty</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((c) => (
                  <tr key={c.id} className="hover:bg-gray-50/60">
                    <td className="px-6 py-3 font-mono text-xs font-medium text-indigo-700">{c.code}</td>
                    <td className="px-6 py-3 font-medium text-gray-900">{c.name}</td>
                    <td className="px-6 py-3 text-gray-600">{c.department}</td>
                    <td className="px-6 py-3 text-gray-600">Sem {c.semester}</td>
                    <td className="px-6 py-3 text-gray-600">{c.credits}</td>
                    <td className="px-6 py-3 text-gray-500">{c.academic_year}</td>
                    <td className="px-6 py-3 text-gray-500">
                      {c.faculty_name ?? <span className="text-gray-300">Unassigned</span>}
                    </td>
                    <td className="px-6 py-3 text-right">
                      <div className="flex items-center justify-end gap-1">
                        <button onClick={() => setEditCourse(c)} className="rounded-lg p-1.5 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600">
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button onClick={() => setDeleteTarget(c)} className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600">
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Modals */}
      {(showAdd || editCourse) && (
        <CourseModal
          initial={editCourse}
          onClose={() => { setShowAdd(false); setEditCourse(null); }}
          onSaved={() => { setShowAdd(false); setEditCourse(null); fetchCourses(); }}
        />
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
          <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl ring-1 ring-gray-200">
            <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
              <AlertTriangle className="h-6 w-6 text-red-500" />
            </div>
            <h2 className="text-base font-semibold text-gray-900">Delete Course</h2>
            <p className="mt-1 text-sm text-gray-500">
              Delete <strong>{deleteTarget.name}</strong> ({deleteTarget.code})? This cannot be undone.
            </p>
            <div className="mt-5 flex justify-end gap-3">
              <button onClick={() => setDeleteTarget(null)} className="btn-secondary">Cancel</button>
              <button onClick={handleDelete} className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700">
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
