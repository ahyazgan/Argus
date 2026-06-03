"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

type AuditItem = {
  id: string;
  user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  detail: string | null;
  created_at: string;
};

const ACTION_LABEL: Record<string, string> = {
  "module.enable": "Modül açıldı",
  "module.disable": "Modül kapatıldı",
  "monitor.create": "Monitör eklendi",
  "monitor.delete": "Monitör silindi",
  "monitor.schedule": "Tarama sıklığı değişti",
  "finding.status": "Bulgu durumu değişti",
  "settings.update": "Ayarlar güncellendi",
  "billing.change_plan": "Plan değişti",
  "user.create": "Kullanıcı eklendi",
  "user.update": "Kullanıcı güncellendi",
  "user.delete": "Kullanıcı silindi",
};

export default function AuditPage() {
  const [items, setItems] = useState<AuditItem[]>([]);
  const [err, setErr] = useState("");

  useEffect(() => {
    api<AuditItem[]>("/audit")
      .then(setItems)
      .catch((e) => setErr(e.message));
  }, []);

  return (
    <div className="max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-bold">Denetim günlüğü</h1>
        <p className="text-sm text-slate-400">Kurumdaki önemli değişikliklerin kaydı</p>
      </div>

      {err && <p className="text-sm text-red-400">{err}</p>}

      <div className="space-y-2">
        {items.length === 0 && !err && (
          <p className="rounded-lg border border-slate-800 bg-slate-900 p-6 text-sm text-slate-400">
            Henüz kayıt yok.
          </p>
        )}
        {items.map((a) => (
          <div
            key={a.id}
            className="flex items-center justify-between rounded-lg border border-slate-800 bg-slate-900 p-3"
          >
            <div>
              <div className="text-sm font-medium">{ACTION_LABEL[a.action] ?? a.action}</div>
              {a.detail && <div className="text-xs text-slate-400">{a.detail}</div>}
            </div>
            <div className="text-right text-xs text-slate-500">
              {new Date(a.created_at).toLocaleString("tr-TR")}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
