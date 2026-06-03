"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api, isAuthed } from "@/lib/api";

type CatalogItem = { key: string; name: string; description: string; category: string; available: boolean };
type Plan = { tier: string; name: string; module_limit: number; price_label: string };

const CAT_DOT: Record<string, string> = {
  dark_web: "bg-purple-500",
  security: "bg-red-500",
  illegal: "bg-orange-500",
  brand: "bg-sky-500",
  competitor: "bg-emerald-500",
  financial: "bg-amber-500",
  disinformation: "bg-pink-500",
  due_diligence: "bg-teal-500",
  ai_testing: "bg-indigo-500",
};

export default function Landing() {
  const [modules, setModules] = useState<CatalogItem[]>([]);
  const [plans, setPlans] = useState<Plan[]>([]);
  const [authed, setAuthed] = useState(false);

  useEffect(() => {
    setAuthed(isAuthed());
    Promise.all([api<CatalogItem[]>("/modules/catalog"), api<Plan[]>("/billing/plans")])
      .then(([m, p]) => {
        setModules(m);
        setPlans(p);
      })
      .catch(() => {});
  }, []);

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      {/* Üst bar */}
      <header className="flex items-center justify-between px-6 py-4 sm:px-10">
        <div className="text-lg font-bold">
          Argus <span className="text-sky-400">Intelligence</span>
        </div>
        <nav className="flex items-center gap-3 text-sm">
          {authed ? (
            <Link href="/dashboard" className="rounded-lg bg-sky-600 px-4 py-2 font-semibold hover:bg-sky-500">
              Panele git
            </Link>
          ) : (
            <>
              <Link href="/login" className="text-slate-300 hover:text-white">
                Giriş yap
              </Link>
              <Link href="/register" className="rounded-lg bg-sky-600 px-4 py-2 font-semibold hover:bg-sky-500">
                Ücretsiz başla
              </Link>
            </>
          )}
        </nav>
      </header>

      {/* Hero */}
      <section className="mx-auto max-w-4xl px-6 py-20 text-center">
        <h1 className="text-4xl font-bold leading-tight sm:text-5xl">
          Tek platform — sonsuz modül — bir abonelik
        </h1>
        <p className="mx-auto mt-5 max-w-2xl text-lg text-slate-400">
          OSINT & tehdit istihbaratı SaaS platformu. Dark web sızıntısından marka korumaya,
          finansal suçtan AI güvenliğine; tüm istihbarat ihtiyacınız tek çatı altında, açıp
          kapatabildiğiniz modüllerle.
        </p>
        <div className="mt-8 flex justify-center gap-3">
          <Link href="/register" className="rounded-lg bg-sky-600 px-6 py-3 font-semibold hover:bg-sky-500">
            Ücretsiz başla
          </Link>
          <a href="#moduller" className="rounded-lg border border-slate-700 px-6 py-3 font-semibold hover:bg-slate-800">
            Modülleri keşfet
          </a>
        </div>
      </section>

      {/* Modüller */}
      <section id="moduller" className="mx-auto max-w-6xl px-6 py-12">
        <h2 className="text-center text-2xl font-bold">{modules.length || 9} modül, tek çekirdek</h2>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {modules.map((m) => (
            <div key={m.key} className="rounded-xl border border-slate-800 bg-slate-900 p-5">
              <div className="flex items-center gap-2">
                <span className={`h-2.5 w-2.5 rounded-full ${CAT_DOT[m.category] ?? "bg-slate-500"}`} />
                <span className="font-semibold">{m.name}</span>
                {!m.available && (
                  <span className="ml-auto rounded-full bg-slate-700 px-2 py-0.5 text-[10px] text-slate-300">
                    yakında
                  </span>
                )}
              </div>
              <p className="mt-2 text-sm text-slate-400">{m.description}</p>
            </div>
          ))}
        </div>
      </section>

      {/* Fiyatlandırma */}
      <section className="mx-auto max-w-5xl px-6 py-12">
        <h2 className="text-center text-2xl font-bold">Fiyatlandırma</h2>
        <div className="mt-8 grid grid-cols-1 gap-4 md:grid-cols-3">
          {plans.map((p, i) => (
            <div
              key={p.tier}
              className={`rounded-xl border p-6 ${
                i === 1 ? "border-sky-600 bg-sky-600/5" : "border-slate-800 bg-slate-900"
              }`}
            >
              <div className="text-lg font-semibold">{p.name}</div>
              <div className="mt-2 text-2xl font-bold">{p.price_label}</div>
              <div className="mt-2 text-sm text-slate-400">{p.module_limit} modüle kadar</div>
              <Link
                href="/register"
                className="mt-4 block rounded-lg bg-sky-600 px-3 py-2 text-center text-sm font-semibold hover:bg-sky-500"
              >
                Başla
              </Link>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-800 px-6 py-8 text-center text-sm text-slate-500">
        Argus Intelligence · OSINT & tehdit istihbaratı
      </footer>
    </main>
  );
}
