"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { api, clearTokens, isAuthed } from "@/lib/api";

type ModuleItem = { key: string; name: string; available: boolean; enabled: boolean };

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);
  const [modules, setModules] = useState<ModuleItem[]>([]);

  useEffect(() => {
    if (!isAuthed()) {
      router.replace("/login");
      return;
    }
    setReady(true);
    api<ModuleItem[]>("/modules")
      .then((m) => setModules(m.filter((x) => x.available)))
      .catch(() => {});
  }, [router]);

  if (!ready) {
    return (
      <main className="flex min-h-screen items-center justify-center">
        <p className="text-slate-400">Yükleniyor…</p>
      </main>
    );
  }

  function logout() {
    clearTokens();
    router.replace("/login");
  }

  const linkClass = (active: boolean) =>
    `flex items-center gap-3 rounded-lg px-3 py-2 text-sm ${
      active ? "bg-sky-600/20 text-sky-300" : "text-slate-300 hover:bg-slate-800"
    }`;

  return (
    <div className="flex min-h-screen">
      <aside className="flex w-64 flex-col border-r border-slate-800 bg-slate-900 p-4">
        <div className="mb-8 px-2">
          <div className="text-lg font-bold">Argus</div>
          <div className="text-xs text-slate-500">Intelligence</div>
        </div>
        <nav className="flex-1 space-y-1">
          <Link href="/dashboard" className={linkClass(pathname?.startsWith("/dashboard") ?? false)}>
            <span className="w-4 text-center">▣</span> Genel bakış
          </Link>
          <Link href="/modules" className={linkClass(pathname === "/modules")}>
            <span className="w-4 text-center">⊞</span> Modüller
          </Link>

          {modules.length > 0 && (
            <div className="px-3 pb-1 pt-4 text-[10px] uppercase tracking-wide text-slate-600">
              Modüller
            </div>
          )}
          {modules.map((m) => {
            const href = `/m/${m.key}`;
            const active = pathname === href;
            return (
              <Link key={m.key} href={href} className={linkClass(active)}>
                <span className="w-4 text-center">◎</span>
                <span className="truncate">{m.name}</span>
                {!m.enabled && (
                  <span className="ml-auto text-[10px] text-slate-600">kapalı</span>
                )}
              </Link>
            );
          })}

          <div className="px-3 pb-1 pt-4 text-[10px] uppercase tracking-wide text-slate-600">
            Hesap
          </div>
          <Link href="/billing" className={linkClass(pathname === "/billing")}>
            <span className="w-4 text-center">⊟</span> Abonelik
          </Link>
          <Link href="/team" className={linkClass(pathname === "/team")}>
            <span className="w-4 text-center">⊕</span> Ekip
          </Link>
          <Link href="/audit" className={linkClass(pathname === "/audit")}>
            <span className="w-4 text-center">▤</span> Denetim
          </Link>
          <Link href="/settings" className={linkClass(pathname === "/settings")}>
            <span className="w-4 text-center">⚙</span> Ayarlar
          </Link>
        </nav>
        <button
          onClick={logout}
          className="mt-4 rounded-lg px-3 py-2 text-left text-sm text-slate-400 hover:bg-slate-800"
        >
          ↪ Çıkış yap
        </button>
      </aside>
      <main className="flex-1 overflow-auto p-8">{children}</main>
    </div>
  );
}
