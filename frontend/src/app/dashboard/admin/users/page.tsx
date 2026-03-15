"use client";

// ─────────────────────────────────────────────
//  Admin → User Management (Faculty & Admins)
// ─────────────────────────────────────────────
import { useState, useEffect } from "react";
import {
  UserPlus, Search, ShieldCheck, GraduationCap, ToggleLeft, ToggleRight,
  ChevronDown, X, Eye, EyeOff,
} from "lucide-react";
import { PageLoading } from "@/components/ui/LoadingSpinner";
import EmptyState from "@/components/ui/EmptyState";
import { formatDate } from "@/lib/utils";
import api from "@/lib/api";

interface SystemUser {
  id: number;
  email: string;
  full_name: string;
  role: "ADMIN" | "FACULTY";
  department: string | null;
  is_active: boolean;
  created_at: string;
}

// ── Register user modal ───────────────────────
function RegisterModal({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState({ email: "", full_name: "", password: "", role: "FACULTY", department: "CSE" });
  const [showPw, setShowPw] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm((f) => ({ ...f, [k]: e.target.value }));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await api.post("/auth/register", form);
      onSaved();
    } catch (err: unknown) {
      const ex = err as { response?: { data?: { detail?: string } } };
      setError(ex?.response?.data?.detail ?? "Registration failed.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4 backdrop-blur-sm">
      <div className="w-full max-w-md rounded-2xl bg-white shadow-xl ring-1 ring-gray-200">
        <div className="flex items-center justify-between border-b border-gray-100 px-6 py-4">
          <h2 className="text-base font-semibold text-gray-900">Register New User</h2>
          <button onClick={onClose} className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100">
            <X className="h-4 w-4" />
          </button>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4 p-6">
          {error && (
            <div className="rounded-lg bg-red-50 px-4 py-3 text-sm text-red-700 ring-1 ring-red-200">{error}</div>
          )}
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Full Name *</label>
            <input required className="input" value={form.full_name} onChange={set("full_name")} placeholder="Dr. Jane Smith" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Email *</label>
            <input required type="email" className="input" value={form.email} onChange={set("email")} placeholder="jane@institution.edu" />
          </div>
          <div>
            <label className="mb-1 block text-xs font-medium text-gray-700">Password *</label>
            <div className="relative">
              <input
                required
                type={showPw ? "text" : "password"}
                className="input pr-10"
                value={form.password}
                onChange={set("password")}
                placeholder="Min. 8 characters"
                minLength={8}
              />
              <button type="button" onClick={() => setShowPw((v) => !v)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
                {showPw ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Role</label>
              <select className="input" value={form.role} onChange={set("role")}>
                <option value="FACULTY">Faculty</option>
                <option value="ADMIN">Admin</option>
              </select>
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Department</label>
              <select className="input" value={form.department} onChange={set("department")}>
                {["CSE", "ECE", "MECH", "CIVIL", "IT", "Administration"].map((d) => <option key={d}>{d}</option>)}
              </select>
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary">Cancel</button>
            <button type="submit" disabled={saving} className="btn-primary">
              {saving ? "Registering…" : "Register User"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ── Role badge ────────────────────────────────
function RoleBadge({ role }: { role: "ADMIN" | "FACULTY" }) {
  return role === "ADMIN" ? (
    <span className="inline-flex items-center gap-1 rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-semibold text-indigo-700">
      <ShieldCheck className="h-3 w-3" /> Admin
    </span>
  ) : (
    <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
      <GraduationCap className="h-3 w-3" /> Faculty
    </span>
  );
}

// ── Page ──────────────────────────────────────
export default function AdminUsersPage() {
  const [users, setUsers] = useState<SystemUser[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [roleFilter, setRoleFilter] = useState<"ALL" | "ADMIN" | "FACULTY">("ALL");
  const [showRegister, setShowRegister] = useState(false);

  const fetchUsers = async () => {
    setLoading(true);
    try {
      const r = await api.get("/faculty");
      setUsers(r.data.items ?? r.data ?? []);
    } catch {
      setUsers([
        { id: 1, email: "admin@edusentinel.dev", full_name: "System Admin", role: "ADMIN", department: "Administration", is_active: true, created_at: "2024-07-01T00:00:00Z" },
        { id: 2, email: "faculty@edusentinel.dev", full_name: "Dr. Priya Sharma", role: "FACULTY", department: "CSE", is_active: true, created_at: "2024-07-15T00:00:00Z" },
        { id: 3, email: "john@edusentinel.dev", full_name: "Prof. John Doe", role: "FACULTY", department: "ECE", is_active: true, created_at: "2024-08-01T00:00:00Z" },
        { id: 4, email: "inactive@edusentinel.dev", full_name: "Dr. Old Staff", role: "FACULTY", department: "MECH", is_active: false, created_at: "2023-01-10T00:00:00Z" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchUsers(); }, []);

  const toggleActive = async (user: SystemUser) => {
    const endpoint = user.is_active ? `/faculty/${user.id}/deactivate` : `/faculty/${user.id}/activate`;
    await api.post(endpoint).catch(() => {});
    fetchUsers();
  };

  const filtered = users.filter((u) => {
    const q = search.toLowerCase();
    const matchesSearch = !q || u.full_name.toLowerCase().includes(q) || u.email.toLowerCase().includes(q);
    const matchesRole = roleFilter === "ALL" || u.role === roleFilter;
    return matchesSearch && matchesRole;
  });

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">User Management</h1>
          <p className="mt-0.5 text-sm text-gray-500">Register and manage faculty and admin accounts</p>
        </div>
        <button onClick={() => setShowRegister(true)} className="btn-primary flex items-center gap-2">
          <UserPlus className="h-4 w-4" /> Register User
        </button>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
          <input type="search" value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search users…" className="input pl-9" />
        </div>
        <div className="relative">
          <select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value as typeof roleFilter)} className="input w-36 appearance-none pr-8">
            <option value="ALL">All Roles</option>
            <option value="ADMIN">Admin</option>
            <option value="FACULTY">Faculty</option>
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-gray-400" />
        </div>
      </div>

      {/* Stats row */}
      <div className="flex gap-4 text-sm">
        <span className="text-gray-500">Total: <strong className="text-gray-900">{users.length}</strong></span>
        <span className="text-gray-500">Active: <strong className="text-emerald-600">{users.filter(u => u.is_active).length}</strong></span>
        <span className="text-gray-500">Inactive: <strong className="text-gray-400">{users.filter(u => !u.is_active).length}</strong></span>
      </div>

      {loading ? (
        <PageLoading />
      ) : filtered.length === 0 ? (
        <EmptyState icon={Search} title="No users found" description="Try a different search or register a new user." />
      ) : (
        <div className="overflow-hidden rounded-2xl bg-white shadow-sm ring-1 ring-gray-200">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-100 text-sm">
              <thead>
                <tr className="table-header">
                  <th className="px-6 py-3 text-left">User</th>
                  <th className="px-6 py-3 text-left">Role</th>
                  <th className="px-6 py-3 text-left">Department</th>
                  <th className="px-6 py-3 text-left">Joined</th>
                  <th className="px-6 py-3 text-center">Status</th>
                  <th className="px-6 py-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-50">
                {filtered.map((u) => (
                  <tr key={u.id} className="hover:bg-gray-50/60">
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-3">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-xs font-bold text-indigo-700">
                          {u.full_name.charAt(0)}
                        </div>
                        <div>
                          <p className="font-medium text-gray-900">{u.full_name}</p>
                          <p className="text-xs text-gray-500">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-6 py-3"><RoleBadge role={u.role} /></td>
                    <td className="px-6 py-3 text-gray-600">{u.department ?? "—"}</td>
                    <td className="px-6 py-3 text-gray-400">{formatDate(u.created_at)}</td>
                    <td className="px-6 py-3 text-center">
                      <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-semibold ${u.is_active ? "bg-emerald-50 text-emerald-700" : "bg-gray-100 text-gray-400"}`}>
                        {u.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-6 py-3 text-right">
                      <button
                        onClick={() => toggleActive(u)}
                        title={u.is_active ? "Deactivate" : "Activate"}
                        className={`rounded-lg p-1.5 transition-colors ${u.is_active ? "text-gray-400 hover:bg-red-50 hover:text-red-600" : "text-gray-400 hover:bg-emerald-50 hover:text-emerald-600"}`}
                      >
                        {u.is_active ? <ToggleRight className="h-5 w-5" /> : <ToggleLeft className="h-5 w-5" />}
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {showRegister && (
        <RegisterModal
          onClose={() => setShowRegister(false)}
          onSaved={() => { setShowRegister(false); fetchUsers(); }}
        />
      )}
    </div>
  );
}
