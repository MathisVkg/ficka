import type { Metadata } from "next";
import { AppShell } from "@/components/layout/app-shell";
import "./globals.css";
export const metadata: Metadata = {
  title: { default: "Dashboard · Ficka", template: "%s · Ficka" },
  description: "A clearer view of your small business finances.",
};
export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
