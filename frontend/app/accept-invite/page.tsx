"use client";

import { Suspense, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { api, setTokens } from "@/lib/api";

function AcceptInviteInner() {
  const router = useRouter();
  const params = useSearchParams();
  const token = params.get("token") || "";
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setBusy(true);
    try {
      const t = await api<{ access_token: string; refresh_token: string }>(
        "/auth/accept-invite",
        { body: { token, password } }
      );
      setTokens(t.access_token, t.refresh_token);
      router.replace("/dashboard");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-950 px-4">
      <form onSubmit={submit} className="w-full max-w-sm space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h1 className="text-xl font-bold text-slate-100">Daveti kabul et</h1>
        <p className="text-sm text-slate-400">Hesabınızı etkinleştirmek için bir parola belirleyin.</p>
        {!token && <p className="text-sm text-red-400">Davet token'ı bulunamadı.</p>}
        {err && <p className="text-sm text-red-400">{err}</p>}
        <input
          required
          type="password"
          placeholder="Yeni parola (min 8)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
        />
        <button
          disabled={!token || busy}
          className="w-full rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold text-white hover:bg-sky-500 disabled:opacity-40"
        >
          {busy ? "…" : "Hesabı etkinleştir"}
        </button>
      </form>
    </main>
  );
}

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={null}>
      <AcceptInviteInner />
    </Suspense>
  );
}
