"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import {
  LayoutDashboard,
  ArrowDownLeft,
  ArrowUpRight,
  Repeat2,
  ChartNoAxesCombined,
  Settings2,
  Menu,
  X,
  Sprout,
} from "lucide-react";
const navigation = [
  ["Dashboard", "/", LayoutDashboard],
  ["Income", "/income", ArrowDownLeft],
  ["Expenses", "/expenses", ArrowUpRight],
  ["Recurring", "/recurring", Repeat2],
  ["Reports", "/reports", ChartNoAxesCombined],
  ["Settings", "/settings", Settings2],
] as const;
export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      <header className="mobile-header">
        <Link href="/" className="brand">
          ficka<span>.</span>
        </Link>
        <button
          aria-label={open ? "Close navigation" : "Open navigation"}
          aria-expanded={open}
          aria-controls="sidebar"
          onClick={() => setOpen(!open)}
        >
          {open ? <X /> : <Menu />}
        </button>
      </header>
      <aside id="sidebar" className={open ? "sidebar is-open" : "sidebar"}>
        <Link href="/" className="brand">
          ficka<span>.</span>
        </Link>
        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav aria-label="Main navigation">
          {navigation.map(([label, href, Icon]) => (
            <Link
              key={href}
              href={href}
              aria-current={pathname === href ? "page" : undefined}
              onClick={() => setOpen(false)}
            >
              <Icon size={19} strokeWidth={1.7} />
              {label}
            </Link>
          ))}
        </nav>
        <div className="sidebar-footer">
          <Sprout size={20} />
          <strong>A clearer view of your business</strong>
          <p>Your finances, in your hands.</p>
          <span>Ficka · Self-hosted</span>
        </div>
      </aside>
      <main id="main" className="main-content">
        {children}
      </main>
    </div>
  );
}
