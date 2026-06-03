"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = {
  organization_name: string;
  webhook_url: string | null;
  slack_webhook_url: string | null;
  notify_email: string | null;
  github_repo: string | null;
  has_github_token: boolean;
  jira_base_url: string | null;
  jira_email: string | null;
  jira_project_key: string | null;
  has_jira_token: boolean;
  gov_report_url: string | null;
  has_gov_report_token: boolean;
  has_api_key: boolean;
};

export default function SettingsPage() {
  const [s, setS] = useState<Settings | null>(null);
  const [webhook, setWebhook] = useState("");
  const [slack, setSlack] = useState("");
  const [email, setEmail] = useState("");
  const [ghRepo, setGhRepo] = useState("");
  const [ghToken, setGhToken] = useState("");
  const [jiraUrl, setJiraUrl] = useState("");
  const [jiraEmail, setJiraEmail] = useState("");
  const [jiraProject, setJiraProject] = useState("");
  const [jiraToken, setJiraToken] = useState("");
  const [govUrl, setGovUrl] = useState("");
  const [govToken, setGovToken] = useState("");
  const [apiKey, setApiKey] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function load() {
    const data = await api<Settings>("/settings");
    setS(data);
    setWebhook(data.webhook_url || "");
    setSlack(data.slack_webhook_url || "");
    setEmail(data.notify_email || "");
    setGhRepo(data.github_repo || "");
    setJiraUrl(data.jira_base_url || "");
    setJiraEmail(data.jira_email || "");
    setJiraProject(data.jira_project_key || "");
    setGovUrl(data.gov_report_url || "");
    // Token'lar sunucudan donmez; kutular bos baslar (girilirse guncellenir)
    setGhToken("");
    setJiraToken("");
    setGovToken("");
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
        body: {
          webhook_url: webhook,
          slack_webhook_url: slack,
          notify_email: email,
          github_repo: ghRepo,
          github_token: ghToken || undefined,
          jira_base_url: jiraUrl,
          jira_email: jiraEmail,
          jira_project_key: jiraProject,
          jira_token: jiraToken || undefined,
          gov_report_url: govUrl,
          gov_report_token: govToken || undefined,
        },
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
        <div>
          <label className="text-sm text-slate-400">E-posta (bildirim alıcısı)</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="guvenlik@firma.com"
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <p className="mt-1 text-xs text-slate-500">SMTP sunucu ayarları .env'de tanımlı olmalıdır.</p>
        </div>

        <h2 className="pt-2 font-semibold">GitHub Issues</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            value={ghRepo}
            onChange={(e) => setGhRepo(e.target.value)}
            placeholder="owner/repo"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            type="password"
            value={ghToken}
            onChange={(e) => setGhToken(e.target.value)}
            placeholder={s?.has_github_token ? "Token tanımlı (değiştirmek için yazın)" : "GitHub token (repo izni)"}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
        </div>

        <h2 className="pt-2 font-semibold">Jira</h2>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            value={jiraUrl}
            onChange={(e) => setJiraUrl(e.target.value)}
            placeholder="https://firma.atlassian.net"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            value={jiraProject}
            onChange={(e) => setJiraProject(e.target.value)}
            placeholder="Proje anahtarı (örn. SEC)"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            value={jiraEmail}
            onChange={(e) => setJiraEmail(e.target.value)}
            placeholder="jira-kullanici@firma.com"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            type="password"
            value={jiraToken}
            onChange={(e) => setJiraToken(e.target.value)}
            placeholder={s?.has_jira_token ? "Token tanımlı (değiştirmek için yazın)" : "Jira API token"}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
        </div>

        <h2 className="pt-2 font-semibold">Kamu / BTK ihbar</h2>
        <p className="text-xs text-slate-500">
          BTK İhbarweb'in açık API'si yoktur. Yapılandırılmış ihbar payload'ı, tanımladığınız bir
          uç noktaya (uyum sistemi / e-Devlet aracı relay) gönderilir. Modüle göre kurum (BTK/MASAK/
          USOM) işaretlenir.
        </p>
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          <input
            value={govUrl}
            onChange={(e) => setGovUrl(e.target.value)}
            placeholder="https://uyum-sistemi.firma.com/ihbar"
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <input
            type="password"
            value={govToken}
            onChange={(e) => setGovToken(e.target.value)}
            placeholder={s?.has_gov_report_token ? "Token tanımlı (değiştirmek için yazın)" : "Bearer token (opsiyonel)"}
            className="rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
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
