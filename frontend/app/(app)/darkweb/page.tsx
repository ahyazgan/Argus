"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

// Eski yol -> yeni dinamik modul sayfasi
export default function DarkWebRedirect() {
  const router = useRouter();
  useEffect(() => {
    router.replace("/m/darkweb");
  }, [router]);
  return <p className="text-slate-400">Yönlendiriliyor…</p>;
}
