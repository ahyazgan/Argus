"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type ModuleItem = {
  key: string;
  name: string;
  description: string;
  category: string;
  asset_types: string[];
  available: boolean;
  enabled: boolean;
};

type Subscription = {
  plan_name: string;
  module_limit: number;
  enabled_modules: string[];
};

// Görseldeki renk grupları (kategori -> etiket + Tailwind aksan renkleri)
const CATEGORY: Record<string, { label: string; dot: string; ring: string; text: string }> = {
  dark_web: { label: "Dark Web", dot: "bg-purple-500", ring: "border-purple-500/40", text: "text-purple-300" },
  security: { label: "Güvenlik", dot: "bg-red-500", ring: "border-red-500/40", text: "text-red-300" },
  illegal: { label: "Yasadışı İçerik", dot: "bg-orange-500", ring: "border-orange-500/40", text: "text-orange-300" },
  brand: { label: "Marka", dot: "bg-sky-500", ring: "border-sky-500/40", text: "text-sky-300" },
  competitor: { label: "Rekabet", dot: "bg-emerald-500", ring: "border-emerald-500/40", text: "text-emerald-300" },
  financial: { label: "Finansal Suç", dot: "bg-amber-500", ring: "border-amber-500/40", text: "text-amber-300" },
  disinformation: { label: "Dezenformasyon", dot: "bg-pink-500", ring: "border-pink-500/40", text: "text-pink-300" },
  due_diligence: { label: "Due Diligence", dot: "bg-teal-500", ring: "border-teal-500/40", text: "text-teal-300" },
  ai_testing: { label: "AI Güvenliği", dot: "bg-indigo-500", ring: "border-indigo-500/40", text: "text-indigo-300" },
};

function cat(key: string) {
  return CATEGORY[key] ?? { label: key, dot: "bg-slate-500", ring: "border-slate-700", text: "text-slate-300" };
}

export default function ModulesPage() {
  const [modules, setModules] = useState<ModuleItem[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [err, setErr] = useState("");

  async function load() {
    const [m, s] = await Promise.all([
      api<ModuleItem[]>("/modules"),
      api<Subscription>("/modules/subscription"),
    ]);
    setModules(m);
    setSub(s);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function toggle(mod: ModuleItem) {
    setErr("");
    setBusy(mod.key);
    try {
      await api("/modules/toggle", {
        body: { module_key: mod.key, enable: !mod.enabled },
      });
      await load();
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setBusy(null);
    }
  }

  const openCount = sub?.enabled_modules.length ?? 0;

  // Kategoriye göre grupla (görseldeki renk grupları)
  const groups = modules.reduce<Record<string, ModuleItem[]>>((acc, m) => {
    (acc[m.category] ||= []).push(m);
    return acc;
  }, {});

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Modüller</h1>
        <p className="text-sm text-slate-400">
          Müşteri ihtiyacına göre aç/kapa — {sub?.plan_name} planı · {openCount}/
          {sub?.module_limit} açık
        </p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}

      {Object.entries(groups).map(([category, items]) => {
        const c = cat(category);
        return (
          <div key={category} className="space-y-3">
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${c.dot}`} />
              <h2 className={`text-sm font-semibold uppercase tracking-wide ${c.text}`}>
                {c.label}
              </h2>
            </div>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {items.map((m) => (
                <div
                  key={m.key}
                  className={`rounded-xl border bg-slate-900 p-5 ${
                    m.enabled ? `${c.ring} bg-sky-600/5` : "border-slate-800"
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <div className="font-semibold">{m.name}</div>
                      <div className="mt-1 text-sm text-slate-400">{m.description}</div>
                    </div>
                    {!m.available && (
                      <span className="rounded-full bg-slate-700 px-2 py-0.5 text-xs text-slate-300">
                        yakında
                      </span>
                    )}
                  </div>
                  <div className="mt-4 flex items-center gap-2">
                    <button
                      disabled={!m.available || busy === m.key}
                      onClick={() => toggle(m)}
                      className={`rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-40 ${
                        m.enabled
                          ? "bg-slate-700 hover:bg-slate-600"
                          : "bg-sky-600 hover:bg-sky-500"
                      }`}
                    >
                      {busy === m.key ? "…" : m.enabled ? "Kapat" : m.available ? "Aç" : "Yakında"}
                    </button>
                    {m.enabled && <span className="text-xs text-emerald-400">● açık</span>}
                  </div>
                </div>
              ))}
            </div>
          </div>
        );
      })}
    </div>
  );
}
