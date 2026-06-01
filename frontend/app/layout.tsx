import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Argus Intelligence",
  description: "Tek platform — sonsuz modül — bir abonelik",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="tr">
      <body>{children}</body>
    </html>
  );
}
