"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setTokens } from "@/lib/api";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api<{ access_token: string; refresh_token: string }>("/auth/login", {
        form: { username: email, password },
      });
      setTokens(data.access_token, data.refresh_token);
      router.replace("/dashboard");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm rounded-2xl border border-slate-800 bg-slate-900 p-8 shadow-xl">
        <h1 className="text-2xl font-bold">Argus Intelligence</h1>
        <p className="mb-6 text-sm text-slate-400">Hesabınıza giriş yapın</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            type="email"
            required
            placeholder="E-posta"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            type="password"
            required
            placeholder="Parola"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold hover:bg-sky-500 disabled:opacity-50"
          >
            {loading ? "Giriş yapılıyor…" : "Giriş yap"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400">
          Hesabınız yok mu?{" "}
          <Link href="/register" className="text-sky-400 hover:underline">
            Kayıt olun
          </Link>
        </p>
      </div>
    </main>
  );
}
