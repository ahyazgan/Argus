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

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
        {modules.map((m) => (
          <div
            key={m.key}
            className={`rounded-xl border p-5 ${
              m.enabled
                ? "border-sky-600/50 bg-sky-600/5"
                : "border-slate-800 bg-slate-900"
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
            <div className="mt-4">
              <button
                disabled={!m.available || busy === m.key}
                onClick={() => toggle(m)}
                className={`rounded-lg px-3 py-1.5 text-sm font-medium disabled:opacity-40 ${
                  m.enabled
                    ? "bg-slate-700 hover:bg-slate-600"
                    : "bg-sky-600 hover:bg-sky-500"
                }`}
              >
                {busy === m.key
                  ? "…"
                  : m.enabled
                  ? "Kapat"
                  : m.available
                  ? "Aç"
                  : "Yakında"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
