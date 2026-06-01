"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { api, setTokens } from "@/lib/api";

export default function RegisterPage() {
  const router = useRouter();
  const [orgName, setOrgName] = useState("");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      const data = await api<{ access_token: string; refresh_token: string }>("/auth/register", {
        body: {
          organization_name: orgName,
          full_name: fullName || null,
          email,
          password,
        },
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
        <p className="mb-6 text-sm text-slate-400">Kurum hesabı oluşturun</p>
        <form onSubmit={onSubmit} className="space-y-4">
          <input
            required
            placeholder="Kurum adı"
            value={orgName}
            onChange={(e) => setOrgName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            placeholder="Ad soyad (opsiyonel)"
            value={fullName}
            onChange={(e) => setFullName(e.target.value)}
            className="w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
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
            minLength={8}
            placeholder="Parola (en az 8 karakter)"
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
            {loading ? "Oluşturuluyor…" : "Kayıt ol"}
          </button>
        </form>
        <p className="mt-6 text-center text-sm text-slate-400">
          Zaten hesabınız var mı?{" "}
          <Link href="/login" className="text-sky-400 hover:underline">
            Giriş yapın
          </Link>
        </p>
      </div>
    </main>
  );
}
