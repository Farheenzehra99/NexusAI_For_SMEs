"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import {
  LayoutDashboard,
  Command,
  Users,
  Building2,
  Bell,
  Settings,
  ChevronLeft,
  Loader2,
} from "lucide-react";

const navItems = [
  { href: "/", icon: LayoutDashboard, label: "Dashboard" },
  { href: "/command-center", icon: Command, label: "AI Command Center", primary: true },
  { href: "/ai-employees", icon: Users, label: "AI Employees" },
];

/**
 * Header status reflects the real workforce state. Pages dispatch
 * `nexusai:workforce` ({ active: boolean }) when an analysis starts/ends;
 * the header shows "AI Workforce Active" while any agent is processing
 * and "All Agents Online" otherwise.
 */
function useWorkforceActive(): boolean {
  const [active, setActive] = useState(false);
  useEffect(() => {
    const handler = (event: Event) => {
      setActive(Boolean((event as CustomEvent).detail?.active));
    };
    window.addEventListener("nexusai:workforce", handler);
    return () => window.removeEventListener("nexusai:workforce", handler);
  }, []);
  return active;
}

export default function Sidebar({ children }: { children: React.ReactNode }) {
  const [collapsed, setCollapsed] = useState(false);
  const pathname = usePathname();
  const workforceActive = useWorkforceActive();

  // Small screens start collapsed so content never overflows the viewport;
  // the owner can always expand from the collapse toggle.
  useEffect(() => {
    if (window.matchMedia("(max-width: 767px)").matches) setCollapsed(true);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-navy-950">
      {/* Sidebar */}
      <aside
        className={`${
          collapsed ? "w-20" : "w-64"
        } flex-shrink-0 bg-slate-900/80 border-r border-slate-700/50 flex flex-col transition-all duration-300`}
      >
        {/* Brand */}
        <div className="p-5 border-b border-slate-700/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-900/40">
              <Building2 size={20} className="text-white" />
            </div>
            {!collapsed && (
              <div className="min-w-0">
                {/* Brand is page chrome, not a page heading — each page keeps
                    exactly one h1 for the screen-reader outline. */}
                <div className="text-sm font-bold truncate heading-ai heading-ai-emerald">NexusAI for SMEs</div>
                <p className="text-[11px] text-slate-400 truncate">AI-Powered Workforce</p>
              </div>
            )}
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={isActive ? "page" : undefined}
                className={`group relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? item.primary
                      ? "bg-emerald-500/15 text-emerald-400 border border-emerald-500/25 shadow-[0_0_16px_rgba(16,185,129,0.12)]"
                      : "bg-slate-800/80 text-white border border-slate-700/50"
                    : "text-slate-400 hover:text-white hover:bg-slate-800/60 border border-transparent"
                }`}
              >
                <item.icon
                  size={18}
                  className={`flex-shrink-0 transition-all duration-200 ${
                    isActive && item.primary
                      ? "text-emerald-400 drop-shadow-[0_0_6px_rgba(16,185,129,0.6)]"
                      : "group-hover:drop-shadow-[0_0_5px_rgba(16,185,129,0.35)]"
                  }`}
                />
                {!collapsed && <span className="truncate">{item.label}</span>}
                {isActive && !collapsed && item.primary && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-emerald-400 animate-standby" />
                )}
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="p-3 border-t border-slate-700/50 space-y-1">
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors">
            <Bell size={18} className="flex-shrink-0" />
            {!collapsed && <span>Notifications</span>}
          </button>
          <button className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm text-slate-400 hover:text-white hover:bg-slate-800/60 transition-colors">
            <Settings size={18} className="flex-shrink-0" />
            {!collapsed && <span>Settings</span>}
          </button>
        </div>

        {/* Collapse */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          aria-label={collapsed ? "Expand sidebar" : "Collapse sidebar"}
          className="p-3 border-t border-slate-700/50 flex items-center justify-center text-slate-500 hover:text-white transition-colors"
        >
          <ChevronLeft
            size={18}
            className={`transition-transform duration-300 ${collapsed ? "rotate-180" : ""}`}
          />
        </button>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-y-auto">
        <header className="sticky top-0 z-10 bg-navy-950/80 backdrop-blur-md border-b border-slate-700/30 px-4 sm:px-8 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold heading-ai heading-ai-cyan">Ali Garments</h2>
              <p className="text-xs text-slate-400">Hyderabad, Pakistan · AI-Powered Workforce</p>
            </div>
            <div className="flex items-center gap-4">
              <div
                className="flex items-center gap-2"
                role="status"
                aria-live="polite"
                aria-label={workforceActive ? "AI workforce active" : "All agents online"}
              >
                {workforceActive ? (
                  <>
                    <Loader2 size={12} className="text-emerald-400 animate-spin" aria-hidden />
                    <span className="text-xs text-emerald-400 font-medium">AI Workforce Active</span>
                    <span className="status-dot w-2 h-2 rounded-full bg-emerald-400 text-emerald-400" aria-hidden />
                  </>
                ) : (
                  <>
                    <span className="status-dot w-2 h-2 rounded-full bg-emerald-500 text-emerald-500" aria-hidden />
                    <span className="text-xs text-emerald-400 font-medium">All Agents Online</span>
                  </>
                )}
              </div>
              <button
                className="w-9 h-9 rounded-full bg-gradient-to-br from-amber-400 to-amber-600 flex items-center justify-center text-sm font-bold text-slate-900 transition-transform duration-200 hover:scale-105 ring-2 ring-transparent hover:ring-amber-500/30"
                aria-label="Account"
              >
                AA
              </button>
            </div>
          </div>
        </header>
        <div className="p-4 sm:p-8">{children}</div>
      </main>
    </div>
  );
}
