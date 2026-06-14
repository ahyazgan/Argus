"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type Settings = {
  organization_name: string;
  webhook_url: string | null;
  has_webhook_secret: boolean;
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
  report_schedule: string;
  has_api_key: boolean;
};

type ApiKeyItem = {
  id: string;
  name: string;
  prefix: string;
  last_used_at: string | null;
  revoked_at: string | null;
  created_at: string;
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
  const [reportSchedule, setReportSchedule] = useState("none");
  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [newKeyName, setNewKeyName] = useState("");
  const [freshKey, setFreshKey] = useState("");
  const [freshSecret, setFreshSecret] = useState("");
  const [msg, setMsg] = useState("");
  const [err, setErr] = useState("");

  async function loadKeys() {
    setKeys(await api<ApiKeyItem[]>("/api-keys"));
  }

  async function load() {
    const data = await api<Settings>("/settings");
    await loadKeys();
    setS(data);
    setWebhook(data.webhook_url || "");
    setSlack(data.slack_webhook_url || "");
    setEmail(data.notify_email || "");
    setGhRepo(data.github_repo || "");
    setJiraUrl(data.jira_base_url || "");
    setJiraEmail(data.jira_email || "");
    setJiraProject(data.jira_project_key || "");
    setGovUrl(data.gov_report_url || "");
    setReportSchedule(data.report_schedule || "none");
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
          report_schedule: reportSchedule,
        },
      });
      setMsg("Ayarlar kaydedildi.");
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function createKey() {
    setErr("");
    const name = newKeyName.trim();
    if (!name) return;
    try {
      const data = await api<ApiKeyItem & { key: string }>("/api-keys", { body: { name } });
      setFreshKey(data.key);
      setNewKeyName("");
      await loadKeys();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function genWebhookSecret() {
    setErr("");
    try {
      const data = await api<{ webhook_secret: string }>("/settings/webhook-secret", {
        method: "POST",
      });
      setFreshSecret(data.webhook_secret);
      await load();
    } catch (e: any) {
      setErr(e.message);
    }
  }

  async function revokeKey(id: string) {
    setErr("");
    try {
      await api(`/api-keys/${id}`, { method: "DELETE" });
      await loadKeys();
    } catch (e: any) {
      setErr(e.message);
    }
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
          <p className="mt-1 text-xs text-slate-500">
            İmza sırrı tanımlıysa istekler <code className="text-slate-400">X-Argus-Signature</code>{" "}
            (HMAC-SHA256) ve <code className="text-slate-400">X-Argus-Timestamp</code> başlıklarıyla
            imzalanır.
          </p>
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

        <h2 className="pt-2 font-semibold">Zamanlanmış rapor</h2>
        <div>
          <label className="text-sm text-slate-400">PDF raporu e-posta ile gönder</label>
          <select
            value={reportSchedule}
            onChange={(e) => setReportSchedule(e.target.value)}
            className="mt-1 w-full rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500 sm:w-60"
          >
            <option value="none">Kapalı</option>
            <option value="daily">Günlük</option>
            <option value="weekly">Haftalık</option>
          </select>
          <p className="mt-1 text-xs text-slate-500">
            Yukarıdaki bildirim e-postası adresine gönderilir (SMTP gereklidir).
          </p>
        </div>

        <button className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold hover:bg-sky-500">
          Kaydet
        </button>
      </form>

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="font-semibold">Webhook imza sırrı</h2>
        <p className="text-sm text-slate-400">
          Genel webhook isteklerini HMAC-SHA256 ile imzalar; alıcı taraf gövdeyi bu sır ile
          doğrular. {s?.has_webhook_secret ? "Tanımlı." : "Henüz oluşturulmadı."}
        </p>
        {freshSecret && (
          <div className="rounded-lg border border-emerald-700 bg-emerald-500/10 p-3">
            <p className="text-xs text-emerald-300">
              İmza sırrı — alıcı sistemde bu değeri saklayın (tekrar gösterilmez):
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="block flex-1 break-all rounded bg-slate-900 p-2 text-xs text-emerald-200">
                {freshSecret}
              </code>
              <button
                onClick={() => navigator.clipboard?.writeText(freshSecret)}
                className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
              >
                Kopyala
              </button>
              <button
                onClick={() => setFreshSecret("")}
                className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
              >
                Gizle
              </button>
            </div>
          </div>
        )}
        <button
          onClick={genWebhookSecret}
          className="rounded-lg border border-slate-700 px-4 py-2 text-sm hover:bg-slate-800"
        >
          {s?.has_webhook_secret ? "Yeniden oluştur" : "İmza sırrı oluştur"}
        </button>
      </div>

      <div className="space-y-3 rounded-xl border border-slate-800 bg-slate-900 p-6">
        <h2 className="font-semibold">REST API anahtarları</h2>
        <p className="text-sm text-slate-400">
          Dış sistemlerin (SIEM, otomasyon) Argus'a salt-okuma erişimi için.{" "}
          <code className="text-slate-300">X-API-Key</code> başlığıyla veya{" "}
          <code className="text-slate-300">Authorization: Bearer ak_…</code> ile kullanın.
        </p>

        {freshKey && (
          <div className="rounded-lg border border-emerald-700 bg-emerald-500/10 p-3">
            <p className="text-xs text-emerald-300">
              Anahtar oluşturuldu — bu değer yalnızca bir kez gösterilir, güvenli bir yere kaydedin:
            </p>
            <div className="mt-2 flex items-center gap-2">
              <code className="block flex-1 break-all rounded bg-slate-900 p-2 text-xs text-emerald-200">
                {freshKey}
              </code>
              <button
                onClick={() => navigator.clipboard?.writeText(freshKey)}
                className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
              >
                Kopyala
              </button>
              <button
                onClick={() => setFreshKey("")}
                className="rounded-lg border border-slate-700 px-2 py-1 text-xs hover:bg-slate-800"
              >
                Gizle
              </button>
            </div>
          </div>
        )}

        <div className="space-y-2">
          {keys.length === 0 && (
            <p className="text-sm text-slate-500">Henüz anahtar yok.</p>
          )}
          {keys.map((k) => (
            <div
              key={k.id}
              className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-800/40 p-3"
            >
              <div>
                <div className="text-sm font-medium">
                  {k.name}{" "}
                  <span className="font-mono text-xs text-slate-500">{k.prefix}</span>
                  {k.revoked_at && (
                    <span className="ml-2 rounded-full bg-red-500/20 px-2 py-0.5 text-xs text-red-300">
                      iptal edildi
                    </span>
                  )}
                </div>
                <div className="text-xs text-slate-500">
                  {k.last_used_at
                    ? `son kullanım: ${new Date(k.last_used_at).toLocaleString("tr-TR")}`
                    : "henüz kullanılmadı"}
                </div>
              </div>
              {!k.revoked_at && (
                <button
                  onClick={() => revokeKey(k.id)}
                  className="rounded-lg border border-slate-700 px-3 py-1.5 text-sm hover:bg-slate-800"
                >
                  İptal et
                </button>
              )}
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <input
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && createKey()}
            placeholder="Anahtar adı (örn. SIEM entegrasyonu)"
            className="flex-1 rounded-lg border border-slate-700 bg-slate-800 px-3 py-2 text-sm outline-none focus:border-sky-500"
          />
          <button
            onClick={createKey}
            className="rounded-lg bg-sky-600 px-4 py-2 text-sm font-semibold hover:bg-sky-500"
          >
            + Anahtar oluştur
          </button>
        </div>
        <p className="text-xs text-slate-500">
          Anahtar oluşturma/iptal yalnızca sahip ve yöneticiler içindir.
        </p>
      </div>
    </div>
  );
}
