"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Plan = {
  tier: string;
  name: string;
  module_limit: number;
  price_label: string;
};

type Subscription = {
  plan: string;
  plan_name: string;
  status: string;
  module_limit: number;
  enabled_modules: string[];
  price_label: string;
};

export default function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const [p, s] = await Promise.all([
      api<Plan[]>("/billing/plans"),
      api<Subscription>("/modules/subscription"),
    ]);
    setPlans(p);
    setSub(s);
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function changePlan(tier: string) {
    setErr("");
    setMsg("");
    try {
      await api("/billing/change-plan", { body: { plan: tier } });
      const c = await api<{ message: string }>("/billing/checkout", { body: { plan: tier } });
      setMsg(c.message);
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Abonelik</h1>
        <p className="text-sm text-slate-400">
          Mevcut plan: <span className="font-semibold text-slate-200">{sub?.plan_name}</span> ·{" "}
          {sub?.enabled_modules.length}/{sub?.module_limit} modül açık
        </p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}
      {msg && <p className="rounded-lg border border-slate-800 bg-slate-900 p-3 text-sm text-sky-300">{msg}</p>}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {plans.map((p) => {
          const current = sub?.plan === p.tier;
          return (
            <div
              key={p.tier}
              className={`rounded-xl border p-6 ${
                current ? "border-sky-600 bg-sky-600/5" : "border-slate-800 bg-slate-900"
              }`}
            >
              <div className="text-lg font-semibold">{p.name}</div>
              <div className="mt-1 text-2xl font-bold">{p.price_label}</div>
              <div className="mt-2 text-sm text-slate-400">{p.module_limit} modüle kadar</div>
              <button
                disabled={current}
                onClick={() => changePlan(p.tier)}
                className="mt-4 w-full rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold hover:bg-sky-500 disabled:opacity-40"
              >
                {current ? "Mevcut plan" : "Bu plana geç"}
              </button>
            </div>
          );
        })}
      </div>
      <p className="text-xs text-slate-500">
        Not: Stripe entegrasyonu şu an stub modunda. Gerçek ödeme akışı STRIPE_ENABLED=true ile
        etkinleşir.
      </p>
    </div>
  );
}
