"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { api, apiBase, getToken } from "@/lib/api";

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
};

type Stats = {
  total: number;
  open: number;
  by_severity: Record<string, number>;
  by_module: Record<string, number>;
  by_day: { day: string; count: number }[];
};

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300",
  high: "bg-orange-500/20 text-orange-300",
  medium: "bg-yellow-500/20 text-yellow-300",
  low: "bg-blue-500/20 text-blue-300",
  info: "bg-slate-500/20 text-slate-300",
};

const SEV_BAR: Record<string, string> = {
  critical: "bg-red-500",
  high: "bg-orange-500",
  medium: "bg-yellow-500",
  low: "bg-blue-500",
  info: "bg-slate-500",
};

const SEV_ORDER = ["critical", "high", "medium", "low", "info"];

export default function DashboardPage() {
  const [sub, setSub] = useState<Subscription | null>(null);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [err, setErr] = useState("");
  const [live, setLive] = useState(false);
  const [flash, setFlash] = useState(false);
  const flashTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  async function loadData() {
    const [s, f, st] = await Promise.all([
      api<Subscription>("/modules/subscription"),
      api<Finding[]>("/findings?limit=8"),
      api<Stats>("/findings/stats"),
    ]);
    setSub(s);
    setFindings(f);
    setStats(st);
  }

  useEffect(() => {
    loadData().catch((e) => setErr(e.message));

    // Gercek-zamanli akis: yeni bulguda dashboard'u tazele
    const token = getToken();
    if (!token) return;
    const es = new EventSource(`${apiBase()}/api/v1/events/stream?token=${encodeURIComponent(token)}`);
    es.onopen = () => setLive(true);
    es.onerror = () => setLive(false);
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data);
        if (data.type === "findings") {
          loadData().catch(() => {});
          setFlash(true);
          if (flashTimer.current) clearTimeout(flashTimer.current);
          flashTimer.current = setTimeout(() => setFlash(false), 2500);
        }
      } catch {
        /* connected/keepalive cerceveleri yok sayilir */
      }
    };
    return () => {
      es.close();
      if (flashTimer.current) clearTimeout(flashTimer.current);
    };
  }, []);

  const sevMax = Math.max(1, ...Object.values(stats?.by_severity ?? {}));
  const dayMax = Math.max(1, ...(stats?.by_day ?? []).map((d) => d.count));
  const critHigh = (stats?.by_severity.critical || 0) + (stats?.by_severity.high || 0);

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Genel bakış</h1>
          <p className="text-sm text-slate-400">Tehdit istihbaratı komuta merkezi</p>
        </div>
        <div className="flex items-center gap-3">
          {flash && (
            <span className="rounded-full bg-emerald-500/20 px-3 py-1 text-xs text-emerald-300">
              ↻ Yeni bulgu
            </span>
          )}
          <span className="flex items-center gap-1.5 text-xs text-slate-400">
            <span className={`h-2 w-2 rounded-full ${live ? "bg-emerald-500" : "bg-slate-600"}`} />
            {live ? "Canlı" : "Bağlı değil"}
          </span>
        </div>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card title="Plan" value={sub?.plan_name ?? "—"} sub={sub?.price_label} />
        <Card
          title="Açık modüller"
          value={`${sub?.enabled_modules.length ?? 0} / ${sub?.module_limit ?? 0}`}
        />
        <Card title="Toplam bulgu" value={String(stats?.total ?? 0)} sub={`${stats?.open ?? 0} açık`} />
        <Card title="Yüksek/Kritik" value={String(critHigh)} />
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Önem dağılımı */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Önem dağılımı
          </h2>
          <div className="space-y-2">
            {SEV_ORDER.map((sev) => {
              const v = stats?.by_severity[sev] || 0;
              return (
                <div key={sev} className="flex items-center gap-3">
                  <span className="w-16 text-xs uppercase text-slate-400">{sev}</span>
                  <div className="h-3 flex-1 overflow-hidden rounded bg-slate-800">
                    <div
                      className={`h-full ${SEV_BAR[sev]}`}
                      style={{ width: `${(v / sevMax) * 100}%` }}
                    />
                  </div>
                  <span className="w-8 text-right text-xs text-slate-300">{v}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Son 14 gün trendi */}
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-4 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Son 14 gün (bulgu)
          </h2>
          {(stats?.by_day?.length ?? 0) === 0 ? (
            <p className="text-sm text-slate-500">Henüz veri yok.</p>
          ) : (
            <div className="flex h-32 items-end gap-1">
              {stats!.by_day.map((d) => (
                <div key={d.day} className="flex flex-1 flex-col items-center gap-1" title={`${d.day}: ${d.count}`}>
                  <div
                    className="w-full rounded-t bg-sky-500"
                    style={{ height: `${(d.count / dayMax) * 100}%`, minHeight: d.count ? "4px" : "0" }}
                  />
                  <span className="text-[9px] text-slate-600">{d.day.slice(5)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Modüle göre dağılım */}
      {stats && Object.keys(stats.by_module).length > 0 && (
        <div className="rounded-xl border border-slate-800 bg-slate-900 p-5">
          <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">
            Modüle göre bulgu
          </h2>
          <div className="flex flex-wrap gap-2">
            {Object.entries(stats.by_module).map(([k, v]) => (
              <Link
                key={k}
                href={`/m/${k}`}
                className="rounded-full border border-slate-700 px-3 py-1 text-xs text-slate-300 hover:bg-slate-800"
              >
                {k} · <span className="font-semibold">{v}</span>
              </Link>
            ))}
          </div>
        </div>
      )}

      <div>
        <h2 className="mb-3 text-lg font-semibold">Son bulgular</h2>
        <div className="space-y-2">
          {findings.length === 0 && (
            <p className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
              Henüz bulgu yok. <Link href="/modules" className="text-sky-400">Modüller</Link>’den bir
              modül açıp monitör ekleyin.
            </p>
          )}
          {findings.map((f) => (
            <div key={f.id} className="rounded-lg border border-slate-800 bg-slate-900 p-4">
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
