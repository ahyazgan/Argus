"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type TeamUser = {
  id: string;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
};

type Me = { id: string; role: string };

const ROLE_LABEL: Record<string, string> = {
  owner: "Sahip",
  admin: "Yönetici",
  member: "Üye",
};

export default function TeamPage() {
  const [me, setMe] = useState<Me | null>(null);
  const [users, setUsers] = useState<TeamUser[]>([]);
  const [email, setEmail] = useState("");
  const [fullName, setFullName] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("member");
  const [err, setErr] = useState("");
  const [msg, setMsg] = useState("");

  const canManage = me?.role === "owner" || me?.role === "admin";

  async function load() {
    const [m, list] = await Promise.all([api<Me>("/auth/me"), api<TeamUser[]>("/team")]);
    setMe(m);
    setUsers(list);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function addUser(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    try {
      await api("/team", { body: { email, full_name: fullName, password, role } });
      setEmail("");
      setFullName("");
      setPassword("");
      setRole("member");
      setMsg("Kullanıcı eklendi.");
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function changeRole(id: string, newRole: string) {
    setErr("");
    try {
      await api(`/team/${id}`, { method: "PATCH", body: { role: newRole } });
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function toggleActive(u: TeamUser) {
    setErr("");
    try {
      await api(`/team/${u.id}`, { method: "PATCH", body: { is_active: !u.is_active } });
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function removeUser(id: string) {
    setErr("");
    try {
      await api(`/team/${id}`, { method: "DELETE" });
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Ekip</h1>
        <p className="text-sm text-slate-400">Organizasyon kullanıcıları ve rolleri</p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}
      {msg && <p className="text-sm text-green-400">{msg}</p>}

      {canManage && (
        <form
          onSubmit={addUser}
          className="grid grid-cols-1 gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 sm:grid-cols-5"
        >
          <input
            required
            type="email"
            placeholder="E-posta"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            placeholder="Ad Soyad"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            required
            type="password"
            placeholder="Parola (min 8)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <select
            value={role}
            onChange={(e) => setRole(e.target.value)}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          >
            <option value="member">Üye</option>
            <option value="admin">Yönetici</option>
          </select>
          <button className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold hover:bg-sky-500">
            + Ekle
          </button>
        </form>
      )}

      <div className="space-y-2">
        {users.map((u) => (
          <div
            key={u.id}
            className={`flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-4 ${
              u.is_active ? "" : "opacity-50"
            }`}
          >
            <div>
              <div className="font-medium">
                {u.full_name || u.email}
                {u.id === me?.id && <span className="ml-2 text-xs text-slate-500">(siz)</span>}
              </div>
              <div className="text-sm text-slate-400">{u.email}</div>
            </div>
            <div className="flex items-center gap-2">
              {canManage && u.role !== "owner" && u.id !== me?.id ? (
                <select
                  value={u.role}
                  onChange={(e) => changeRole(u.id, e.target.value)}
                  className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1 text-xs outline-none focus:border-sky-500"
                >
                  <option value="member">Üye</option>
                  <option value="admin">Yönetici</option>
                </select>
              ) : (
                <span className="rounded-full bg-slate-700/50 px-2 py-0.5 text-xs text-slate-300">
                  {ROLE_LABEL[u.role] ?? u.role}
                </span>
              )}
              {canManage && u.role !== "owner" && u.id !== me?.id && (
                <>
                  <button
                    onClick={() => toggleActive(u)}
                    className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
                  >
                    {u.is_active ? "Pasifleştir" : "Aktifleştir"}
                  </button>
                  <button
                    onClick={() => removeUser(u.id)}
                    className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
                  >
                    Sil
                  </button>
                </>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
