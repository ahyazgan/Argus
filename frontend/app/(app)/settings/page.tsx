"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = {
  organization_name: string;
  webhook_url: string | null;
  slack_webhook_url: string | null;
  has_api_key: boolean;
};

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [webhook, setWebhook] = useState("");
  const [slack, setSlack] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const data = await api<Settings>("/settings");
    setS(data);
    setWebhook(data.webhook_url || "");
    setSlack(data.slack_webhook_url || "");
  }

  useEffect(() => {
    load().catch((e) => setErr(e.message));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setErr("");
    setMsg("");
    try {
      await api("/settings", {
        method: "PUT",
        body: { webhook_url: webhook, slack_webhook_url: slack },
      });
      setMsg("Ayarlar kaydedildi.");
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function genKey() {
    const data = await api<{ api_key: string }>("/settings/api-key", { method: "POST" });
    setApiKey(data.api_key);
    await load();
  }

  return (
    <div className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-2xl font-bold">Ayarlar</h1>
        <p className="text-sm text-slate-400">{s?.organization_name}</p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}
      {msg && <p className="text-sm text-green-400">{msg}</p>}

      <form onSubmit={save} className="space-y-4 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="font-semibold">Bildirim kanalları</h2>
        <div>
          <label className="text-sm text-slate-400">Genel webhook URL</label>
          <input
            value={webhook}
            onChange={(e) => setWebhook(e.target.value)}
            placeholder="https://ornek.com/webhook"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
        </div>
        <div>
          <label className="text-sm text-slate-400">Slack webhook URL</label>
          <input
            value={slack}
            onChange={(e) => setSlack(e.target.value)}
            placeholder="https://hooks.slack.com/services/…"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
        </div>
        <button className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold hover:bg-sky-500">
          Kaydet
        </button>
      </form>

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="font-semibold">REST API anahtarı</h2>
        <p className="text-sm text-slate-400">
          Dış sistemlerin (SIEM, otomasyon) Argus'a bağlanması için. {s?.has_api_key ? "Tanımlı." : "Henüz oluşturulmadı."}
        </p>
        {apiKey && (
          <code className="block break-all rounded-lg bg-slate-800 p-3 text-xs text-green-300">
            {apiKey}
          </code>
        )}
        <button
          onClick={genKey}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
        >
          {s?.has_api_key ? "Yeniden oluştur" : "API anahtarı oluştur"}
        </button>
      </div>
    </div>
  );
}
