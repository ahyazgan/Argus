"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { api, apiBase, getToken } from "@/lib/api";

type ModuleItem = {
  key: string;
  name: string;
  description: string;
  asset_types: string[];
  available: boolean;
  enabled: boolean;
};

type Monitor = {
  id: string;
  name: string;
  asset_type: string;
  asset_value: string;
  scan_interval_minutes: number | null;
  last_scanned_at: string | null;
};

const SCHEDULE_OPTIONS: { value: number | null; label: string }[] = [
  { value: null, label: "Manuel" },
  { value: 15, label: "15 dk" },
  { value: 60, label: "1 saat" },
  { value: 360, label: "6 saat" },
  { value: 1440, label: "24 saat" },
];

function scheduleLabel(min: number | null): string {
  return SCHEDULE_OPTIONS.find((o) => o.value === min)?.label ?? `${min} dk`;
}

function lastScanLabel(iso: string | null): string {
  if (!iso) return "henüz taranmadı";
  const d = new Date(iso);
  return `son tarama: ${d.toLocaleString("tr-TR")}`;
}

type Finding = {
  id: string;
  title: string;
  severity: string;
  summary: string | null;
  recommendation: string | null;
  source: string;
  asset_value: string;
  seen_count: number;
};

const SEV_COLOR: Record<string, string> = {
  critical: "bg-red-500/20 text-red-300",
  high: "bg-orange-500/20 text-orange-300",
  medium: "bg-yellow-500/20 text-yellow-300",
  low: "bg-blue-500/20 text-blue-300",
  info: "bg-slate-500/20 text-slate-300",
};

const ASSET_LABEL: Record<string, string> = {
  domain: "Domain",
  email: "E-posta",
  keyword: "Anahtar kelime",
  brand: "Marka",
};

export default function ModulePage() {
  const params = useParams();
  const key = String(params.key);

  const [mod, setMod] = useState<ModuleItem | null>(null);
  const [monitors, setMonitors] = useState<Monitor[]>([]);
  const [findings, setFindings] = useState<Finding[]>([]);
  const [name, setName] = useState("");
  const [assetType, setAssetType] = useState("");
  const [assetValue, setAssetValue] = useState("");
  const [intervalMin, setIntervalMin] = useState<number | null>(null);
  const [err, setErr] = useState("");
  const [notice, setNotice] = useState("");
  const [scanning, setScanning] = useState<string | null>(null);
  const [notEnabled, setNotEnabled] = useState(false);

  async function loadModule() {
    const mods = await api<ModuleItem[]>("/modules");
    const m = mods.find((x) => x.key === key) || null;
    setMod(m);
    if (m && m.asset_types.length) setAssetType((prev) => prev || m.asset_types[0]);
    return m;
  }

  async function loadData() {
    try {
      const [mo, fi] = await Promise.all([
        api<Monitor[]>(`/m/${key}/monitors`),
        api<Finding[]>(`/findings?module=${key}&limit=200`),
      ]);
      setMonitors(mo);
      setFindings(fi);
      setNotEnabled(false);
    } catch (e: any) {
      if (String(e.message).includes("açık değil")) setNotEnabled(true);
      else setErr(e.message);
    }
  }

  useEffect(() => {
    setErr("");
    setNotice("");
    setNotEnabled(false);
    loadModule()
      .then((m) => {
        if (m && m.enabled) return loadData();
        if (m && !m.enabled) setNotEnabled(true);
      })
      .catch((e) => setErr(e.message));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);

  async function addMonitor(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    try {
      await api(`/m/${key}/monitors`, {
        body: {
          module_key: key,
          name,
          asset_type: assetType,
          asset_value: assetValue,
          scan_interval_minutes: intervalMin,
        },
      });
      setName("");
      setAssetValue("");
      await loadData();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function removeMonitor(id: string) {
    await api(`/m/${key}/monitors/${id}`, { method: "DELETE" });
    await loadData();
  }

  async function setSchedule(id: string, value: number | null) {
    setErr("");
    try {
      await api(`/m/${key}/monitors/${id}/schedule`, {
        method: "PATCH",
        body: { scan_interval_minutes: value },
      });
      await loadData();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function scan(id: string) {
    setErr("");
    setNotice("");
    setScanning(id);
    try {
      const res = await api<{ task_id: string }>(`/m/${key}/monitors/${id}/scan`, {
        method: "POST",
      });
      await pollTask(res.task_id);
      await loadData();
      setNotice("Tarama tamamlandı.");
    } catch (e: any) {
      setErr(e.message);
    } finally {
      setScanning(null);
    }
  }

  async function pollTask(taskId: string) {
    for (let i = 0; i < 15; i++) {
      const t = await api<{ status: string }>(`/m/${key}/tasks/${taskId}`);
      if (t.status === "done" || t.status === "failed") return;
      await new Promise((r) => setTimeout(r, 1000));
    }
  }

  function downloadPdf() {
    const token = getToken();
    fetch(`${apiBase()}/api/v1/reports/findings.pdf?module=${key}`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then((r) => r.blob())
      .then((blob) => {
        const a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = `argus-${key}-rapor.pdf`;
        a.click();
      });
  }

  if (notEnabled) {
    return (
      <div className="rounded-xl border border-slate-800 bg-slate-900 p-8">
        <h1 className="text-xl font-bold">{mod?.name ?? key}</h1>
        <p className="mt-2 text-sm text-slate-400">
          Bu modül aboneliğinizde açık değil.{" "}
          <a href="/modules" className="text-sky-400 hover:underline">
            Modüller
          </a>{" "}
          sayfasından açın.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">{mod?.name ?? key}</h1>
          <p className="text-sm text-slate-400">{mod?.description}</p>
        </div>
        <button
          onClick={downloadPdf}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
        >
          ⬇ PDF rapor indir
        </button>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}
      {notice && <p className="text-sm text-green-400">{notice}</p>}

      <form
        onSubmit={addMonitor}
        className="grid grid-cols-1 gap-3 rounded-xl border border-slate-800 bg-slate-900 p-5 sm:grid-cols-5"
      >
        <input
          required
          placeholder="Monitör adı"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
        />
        <select
          value={assetType}
          onChange={(e) => setAssetType(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
        >
          {(mod?.asset_types ?? []).map((t) => (
            <option key={t} value={t}>
              {ASSET_LABEL[t] ?? t}
            </option>
          ))}
        </select>
        <input
          required
          placeholder="örn. markam"
          value={assetValue}
          onChange={(e) => setAssetValue(e.target.value)}
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
        />
        <select
          value={intervalMin ?? ""}
          onChange={(e) => setIntervalMin(e.target.value === "" ? null : Number(e.target.value))}
          title="Otomatik tarama sıklığı"
          className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
        >
          {SCHEDULE_OPTIONS.map((o) => (
            <option key={o.label} value={o.value ?? ""}>
              {o.value === null ? "Manuel" : `Otomatik: ${o.label}`}
            </option>
          ))}
        </select>
        <button className="rounded-lg bg-sky-600 px-3 py-2 text-sm font-semibold hover:bg-sky-500">
          + Monitör ekle
        </button>
      </form>

      <div>
        <h2 className="mb-3 text-lg font-semibold">Monitörler</h2>
        <div className="space-y-2">
          {monitors.length === 0 && <p className="text-sm text-slate-400">Henüz monitör yok.</p>}
          {monitors.map((m) => (
            <div
              key={m.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-4"
            >
              <div>
                <div className="font-medium">{m.name}</div>
                <div className="text-sm text-slate-400">
                  {ASSET_LABEL[m.asset_type] ?? m.asset_type}:{" "}
                  <span className="font-mono">{m.asset_value}</span>
                </div>
                <div className="mt-1 text-xs text-slate-500">
                  {m.scan_interval_minutes
                    ? `⏱ Otomatik: her ${scheduleLabel(m.scan_interval_minutes)} · ${lastScanLabel(
                        m.last_scanned_at
                      )}`
                    : `Manuel · ${lastScanLabel(m.last_scanned_at)}`}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <select
                  value={m.scan_interval_minutes ?? ""}
                  onChange={(e) =>
                    setSchedule(m.id, e.target.value === "" ? null : Number(e.target.value))
                  }
                  title="Otomatik tarama sıklığı"
                  className="rounded-lg border border-slate-700 bg-slate-800 px-2 py-1.5 text-xs outline-none focus:border-sky-500"
                >
                  {SCHEDULE_OPTIONS.map((o) => (
                    <option key={o.label} value={o.value ?? ""}>
                      {o.value === null ? "Manuel" : o.label}
                    </option>
                  ))}
                </select>
                <button
                  onClick={() => scan(m.id)}
                  disabled={scanning === m.id}
                  className="rounded-lg bg-sky-600 px-3 py-1.5 text-sm font-medium hover:bg-sky-500 disabled:opacity-50"
                >
                  {scanning === m.id ? "Taranıyor…" : "Tara"}
                </button>
                <button
                  onClick={() => removeMonitor(m.id)}
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800"
                >
                  Sil
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      <div>
        <h2 className="mb-3 text-lg font-semibold">Bulgular ({findings.length})</h2>
        <div className="space-y-2">
          {findings.length === 0 && (
            <p className="text-sm text-slate-400">Bulgu yok. Bir monitör için “Tara”ya basın.</p>
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
                {f.seen_count > 1 && (
                  <span className="rounded-full bg-slate-700/50 px-2 py-0.5 text-xs text-slate-400">
                    {f.seen_count}× görüldü
                  </span>
                )}
                <span className="ml-auto text-xs text-slate-500">{f.source}</span>
              </div>
              {f.summary && <p className="mt-2 text-sm text-slate-300">{f.summary}</p>}
              {f.recommendation && (
                <div className="mt-2 rounded-lg border-l-2 border-sky-500 bg-slate-800/50 p-2 text-sm text-slate-400">
                  <span className="font-semibold text-slate-300">Öneri: </span>
                  {f.recommendation}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
