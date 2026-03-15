"use client";

// ─────────────────────────────────────────────
//  Admin → Student Management
//  Full CRUD: list, add, edit (modal), delete
// ─────────────────────────────────────────────
import { useState, useMemo } from "react";
import {
  UserPlus, Search, Pencil, Trash2, ChevronLeft, ChevronRight, X, AlertTriangle,
} from "lucide-react";
import RiskBadge from "@/components/dashboard/RiskBadge";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { useStudents } from "@/hooks/useStudents";
import { usePredictions } from "@/hooks/usePredictions";
import api from "@/lib/api";
import type { Student, Prediction } from "@/types";

const DEPARTMENTS = ["All", "CSE", "ECE", "MECH", "CIVIL", "IT"];
const SEMESTERS = ["All", "1", "2", "3", "4", "5", "6", "7", "8"];
const PAGE_SIZE = 15;

// ── Add/Edit modal ────────────────────────────
interface StudentFormData {
  roll_no: string;
  full_name: string;
  email: string;
  department: string;
  semester: string;
  batch_year: string;
  phone: string;
}

const EMPTY_FORM: StudentFormData = {
  roll_no: "", full_name: "", email: "", department: "CSE",
  semester: "5", batch_year: new Date().getFullYear().toString(), phone: "",
};

interface StudentModalProps {
  initial?: Student | null;
  onClose: () => void;
  onSaved: () => void;
}

function StudentModal({ initial, onClose, onSaved }: StudentModalProps) {
  const [form, setForm] = useState<StudentFormData>(
    initial
      ? { ...initial, semester: String(initial.semester), batch_year: String(initial.batch_year), phone: initial.phone ?? "" }
      : EMPTY_FORM
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: keyof StudentFormData) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = { ...form, semester: Number(form.semester), batch_year: Number(form.batch_year) };
      if (initial) {
        await api.put(`/students/${initial.id}`, payload);
      } else {
        await api.post("/students", payload);
      }
      onSaved();
    } catch (err: unknown) {
      const e = err as { response?: { data?: { detail?: string } } };
      setError(e?.response?.data?.detail ?? "Failed to save student.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-lg rounded-2xl bg-white shadow-xl ring-1 ring-gray-200">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">
            {initial ? "Edit Student" : "Add New Student"}
          </h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">
              {error}
            </div>
          )}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Roll No *</label>
              <input required className="input" value={form.roll_no} onChange={set("roll_no")} placeholder="CS20210001" />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Full Name *</label>
              <input required className="input" value={form.full_name} onChange={set("full_name")} placeholder="Student Name" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Email *</label>
            <input required type="email" className="input" value={form.email} onChange={set("email")} placeholder="student@college.edu" />
          </div>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Department *</label>
              <select required className="input" value={form.department} onChange={set("department")}>
                {["CSE", "ECE", "MECH", "CIVIL", "IT"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Semester *</label>
              <select required className="input" value={form.semester} onChange={set("semester")}>
                {[1,2,3,4,5,6,7,8].map((s) => <option key={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Batch Year *</label>
              <input required className="input" type="number" value={form.batch_year} onChange={set("batch_year")} min="2015" max="2030" />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Phone</label>
            <input className="input" value={form.phone} onChange={set("phone")} placeholder="+91 98765 43210" />
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Saving…" : initial ? "Save Changes" : "Add Student"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Confirm delete modal ──────────────────────
interface ConfirmDeleteProps {
  student: Student;
  onClose: () => void;
  onDeleted: () => void;
}

function ConfirmDeleteModal({ student, onClose, onDeleted }: ConfirmDeleteProps) {
  const [deleting, setDeleting] = useState(false);
  const handleDelete = async () => {
    setDeleting(true);
    try {
      await api.delete(`/students/${student.id}`);
      onDeleted();
    } finally {
      setDeleting(false);
    }
  };
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-sm rounded-2xl bg-white p-6 shadow-xl ring-1 ring-gray-200">
        <div className="mb-4 flex h-12 w-12 items-center justify-center rounded-full bg-red-50">
          <AlertTriangle className="h-6 w-6 text-red-500" />
        </div>
        <h2 className="text-base font-semibold text-gray-900">Delete Student</h2>
        <p className="mt-1 text-sm text-gray-500">
          Are you sure you want to delete <strong>{student.full_name}</strong>? This action cannot be undone.
        </p>
        <div className="mt-5 flex justify-end gap-3">
          <button onClick={onClose} className="btn-secondary">Cancel</button>
          <button
            onClick={handleDelete}
            disabled={deleting}
            className="rounded-xl bg-red-600 px-4 py-2 text-sm font-semibold text-white hover:bg-red-700 disabled:opacity-50"
          >
            {deleting ? "Deleting…" : "Delete"}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Page component ────────────────────────────
export default function AdminStudentsPage() {
  const [search, setSearch] = useState("");
  const [debouncedSearch, setDebouncedSearch] = useState("");
  const [department, setDepartment] = useState("All");
  const [semester, setSemester] = useState("All");
  const [page, setPage] = useState(1);
  const [showAdd, setShowAdd] = useState(false);
  const [editStudent, setEditStudent] = useState<Student | null>(null);
  const [deleteStudent, setDeleteStudent] = useState<Student | null>(null);
  const [refreshKey, setRefreshKey] = useState(0);

  const handleSearchChange = (val: string) => {
    setSearch(val);
    setPage(1);
    clearTimeout((window as Window & { _st?: number })._st);
    (window as Window & { _st?: number })._st = window.setTimeout(() => setDebouncedSearch(val), 350);
  };

  const { data, loading } = useStudents({
    search: debouncedSearch.trim() || undefined,
    department: department !== "All" ? department : undefined,
    semester: semester !== "All" ? Number(semester) : undefined,
    page,
    size: PAGE_SIZE,
    _refresh: refreshKey,
  } as Parameters<typeof useStudents>[0]);

  const { data: predictionsData } = usePredictions({ size: 500 });

  const predMap = useMemo(() => {
    const map = new Map<number, Prediction>();
    predictionsData?.items.forEach((p) => map.set(p.student_id, p));
    return map;
  }, [predictionsData]);

  const refresh = () => { setRefreshKey((k) => k + 1); setShowAdd(false); setEditStudent(null); setDeleteStudent(null); };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Students</h1>
          <p className="mt-0.5 text-sm text-gray-500">Manage the complete student roster</p>
        </div>
        <button onClick={() => setShowAdd(true)} className="btn-primary flex items-center gap-2">
          <UserPlus className="h-4 w-4" /> Add Student
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input
            type="search"
            value={search}
            onChange={(e) => handleSearchChange(e.target.value)}
            placeholder="Search by name or roll no…"
            className="input pl-9"
          />
        </div>
        <select value={department} onChange={(e) => { setDepartment(e.target.value); setPage(1); }} className="input w-32">
          {DEPARTMENTS.map((d) => <option key={d}>{d}</option>)}
        </select>
        <select value={semester} onChange={(e) => { setSemester(e.target.value); setPage(1); }} className="input w-32">
          {SEMESTERS.map((s) => <option key={s} value={s}>{s === "All" ? "All Sems" : `Sem ${s}`}</option>)}
        </select>
      </div>

      {/* Table */}
      {loading ? (
        <PageLoading />
      ) : !data || data.items.length === 0 ? (
        <EmptyState icon={Search} title="No students found" description="Try adjusting your search or filters." />
      ) : (
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100 text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-6 py-3 text-left">Roll No</th>
                  <th className="px-6 py-3 text-left">Name</th>
                  <th className="px-6 py-3 text-left">Department</th>
                  <th className="px-6 py-3 text-left">Semester</th>
                  <th className="px-6 py-3 text-left">Batch</th>
                  <th className="px-6 py-3 text-left">Risk</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {data.items.map((s) => {
                  const pred = predMap.get(s.id);
                  return (
                    <tr key={s.id} className="hover:bg-gray-50/60">
                      <td className="px-6 py-3 font-mono text-xs text-gray-500">{s.roll_no}</td>
                      <td className="px-6 py-3 font-medium text-gray-900">{s.full_name}</td>
                      <td className="px-6 py-3 text-gray-600">{s.department}</td>
                      <td className="px-6 py-3 text-gray-600">Sem {s.semester}</td>
                      <td className="px-6 py-3 text-gray-500">{s.batch_year}</td>
                      <td className="px-6 py-3">
                        {pred ? <RiskBadge label={pred.risk_label} size="sm" /> : <span className="text-xs text-gray-300">—</span>}
                      </td>
                      <td className="px-6 py-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <button
                            onClick={() => setEditStudent(s)}
                            className="rounded-lg p-1.5 text-gray-400 hover:bg-indigo-50 hover:text-indigo-600"
                            title="Edit"
                          >
                            <Pencil className="h-4 w-4" />
                          </button>
                          <button
                            onClick={() => setDeleteStudent(s)}
                            className="rounded-lg p-1.5 text-gray-400 hover:bg-red-50 hover:text-red-600"
                            title="Delete"
                          >
                            <Trash2 className="h-4 w-4" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Pagination */}
          {data.pages > 1 && (
            <div className="flex items-center justify-between border-t border-gray-100 px-6 py-3">
              <p className="text-xs text-gray-400">
                Page {page} of {data.pages} · {data.total.toLocaleString()} students
              </p>
              <div className="flex items-center gap-2">
                <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page <= 1} className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40">
                  <ChevronLeft className="h-3.5 w-3.5" />
                </button>
                <button onClick={() => setPage((p) => Math.min(data.pages, p + 1))} disabled={page >= data.pages} className="btn-secondary px-3 py-1.5 text-xs disabled:opacity-40">
                  <ChevronRight className="h-3.5 w-3.5" />
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Modals */}
      {(showAdd || editStudent) && (
        <StudentModal
          initial={editStudent}
          onClose={() => { setShowAdd(false); setEditStudent(null); }}
          onSaved={refresh}
        />
      )}
      {deleteStudent && (
        <ConfirmDeleteModal
          student={deleteStudent}
          onClose={() => setDeleteStudent(null)}
          onDeleted={refresh}
        />
      )}
    </div>
  );
}
