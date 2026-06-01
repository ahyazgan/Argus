"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api";

type Subscription = {
  plan_name: string;
  status: string;
  module_limit: number;
  enabled_modules: string[];
  price_label: string;
};

type Finding = {
  id: string;
  title: string;
  severity: string;
  summary: string | null;
  asset_value: string;
  detected_at: string;
};

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300",
  high: "bg-orange-500/20 text-orange-300",
  medium: "bg-yellow-500/20 text-yellow-300",
  low: "bg-blue-500/20 text-blue-300",
  info: "bg-slate-500/20 text-slate-300",
};

export default function DashboardPage() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    Promise.all([
      api<Subscription>("/modules/subscription"),
      api<Finding[]>("/findings?limit=10"),
    ])
      .then(([s, f]) => {
        setSub(s);
        setFindings(f);
      })
      .catch((e) => setErr(e.message));
  }, []);

  const counts = findings.reduce<Record<string, number>>((acc, f) => {
    acc[f.severity] = (acc[f.severity] || 0) + 1;
    return acc;
  }, {});

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Genel bakış</h1>
        <p className="text-sm text-slate-400">Tehdit istihbaratı özeti</p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="Plan" value={sub?.plan_name ?? "—"} sub={sub?.price_label} />
        <Card
          title="Açık modüller"
          value={`${sub?.enabled_modules.length ?? 0} / ${sub?.module_limit ?? 0}`}
        />
        <Card title="Toplam bulgu" value={String(findings.length)} />
        <Card
          title="Yüksek/Kritik"
          value={String((counts.high || 0) + (counts.critical || 0))}
        />
      </div>

      <div>
        <div className="mb-3 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Son bulgular</h2>
          <Link href="/m/darkweb" className="text-sm text-sky-400 hover:underline">
            Tümünü gör →
          </Link>
        </div>
        <div className="space-y-2">
          {findings.length === 0 && (
            <p className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
              Henüz bulgu yok. <Link href="/m/darkweb" className="text-sky-400">Dark web izleme</Link>’den
              bir monitör ekleyip tarama başlatın.
            </p>
          )}
          {findings.map((f) => (
            <div
              key={f.id}
              className="rounded-lg border border-slate-800 bg-slate-900 p-4"
            >
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-0.5 text-xs font-semibold uppercase ${
                    SEV_COLOR[f.severity] || SEV_COLOR.info
                  }`}
                >
                  {f.severity}
                </span>
                <span className="font-medium">{f.title}</span>
              </div>
              {f.summary && <p className="mt-1 text-sm text-slate-400">{f.summary}</p>}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Card({ title, value, sub }: { title: string; value: string; sub?: string }) {
  return (
    <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
      <div className="text-xs uppercase tracking-wide text-slate-500">{title}</div>
      <div className="mt-2 text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs text-slate-500">{sub}</div>}
    </div>
  );
}
