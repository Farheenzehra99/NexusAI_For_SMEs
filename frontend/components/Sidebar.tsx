"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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

  useEffect(() => {
    if (window.matchMedia("(max-width: 767px)").matches) setCollapsed(true);
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-[#0a0f18] text-white">
      {/* Sidebar */}
      <motion.aside
        animate={{ width: collapsed ? 80 : 260 }}
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className="flex-shrink-0 bg-[#0e1522]/80 backdrop-blur-xl border-r border-white/5 flex flex-col relative z-20 shadow-2xl"
      >
        {/* Brand */}
        <div className="p-5 border-b border-white/5 flex items-center gap-3 h-[73px]">
          <motion.div 
            whileHover={{ scale: 1.05, rotate: 5 }}
            className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-400 to-emerald-600 flex items-center justify-center flex-shrink-0 shadow-[0_0_20px_rgba(16,185,129,0.3)]"
          >
            <Building2 size={20} className="text-white drop-shadow-md" />
          </motion.div>
          <AnimatePresence>
            {!collapsed && (
              <motion.div 
                initial={{ opacity: 0, x: -10 }} 
                animate={{ opacity: 1, x: 0 }} 
                exit={{ opacity: 0, x: -10 }}
                className="min-w-0 overflow-hidden whitespace-nowrap"
              >
                <div className="text-sm font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-100 to-emerald-400">NexusAI for SMEs</div>
                <p className="text-[11px] text-slate-400">AI-Powered Workforce</p>
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Nav */}
        <nav className="flex-1 p-4 space-y-2 overflow-y-auto overflow-x-hidden relative">
          {navItems.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link key={item.href} href={item.href} className="block relative outline-none">
                <motion.div
                  whileHover={{ scale: isActive ? 1 : 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`group relative flex items-center gap-3 px-3 py-3 rounded-xl text-sm font-medium transition-colors z-10 ${
                    isActive
                      ? item.primary ? "text-emerald-300" : "text-white"
                      : "text-slate-400 hover:text-white"
                  }`}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTab"
                      className={`absolute inset-0 rounded-xl ${item.primary ? 'bg-emerald-500/10 border border-emerald-500/20' : 'bg-white/5 border border-white/5'} shadow-inner backdrop-blur-md`}
                      initial={false}
                      transition={{ type: "spring", stiffness: 400, damping: 30 }}
                    />
                  )}
                  <item.icon
                    size={20}
                    className={`relative z-10 flex-shrink-0 transition-colors ${
                      isActive ? (item.primary ? "text-emerald-400" : "text-white") : "group-hover:text-white"
                    }`}
                  />
                  <AnimatePresence>
                    {!collapsed && (
                      <motion.span
                        initial={{ opacity: 0, width: 0 }}
                        animate={{ opacity: 1, width: "auto" }}
                        exit={{ opacity: 0, width: 0 }}
                        className="relative z-10 whitespace-nowrap overflow-hidden"
                      >
                        {item.label}
                      </motion.span>
                    )}
                  </AnimatePresence>
                  
                  {isActive && !collapsed && item.primary && (
                    <motion.span 
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      className="relative z-10 ml-auto w-2 h-2 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8)] animate-pulse" 
                    />
                  )}
                </motion.div>
              </Link>
            );
          })}
        </nav>

        {/* Bottom */}
        <div className="p-4 border-t border-white/5 space-y-2">
          <Link href="/notifications" className="block relative">
            <motion.div
              whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.05)" }}
              whileTap={{ scale: 0.98 }}
              className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm transition-colors ${pathname === '/notifications' ? 'bg-white/5 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              <div className="relative">
                <Bell size={20} className="flex-shrink-0" />
                <span className="absolute top-0 right-0 w-2 h-2 bg-rose-500 rounded-full border-2 border-[#0e1522]" />
              </div>
              <AnimatePresence>
                {!collapsed && (
                  <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="whitespace-nowrap overflow-hidden">
                    Notifications
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.div>
          </Link>

          <Link href="/settings" className="block relative">
            <motion.div
              whileHover={{ scale: 1.02, backgroundColor: "rgba(255,255,255,0.05)" }}
              whileTap={{ scale: 0.98 }}
              className={`flex items-center gap-3 px-3 py-3 rounded-xl text-sm transition-colors ${pathname === '/settings' ? 'bg-white/5 text-white' : 'text-slate-400 hover:text-white'}`}
            >
              <Settings size={20} className="flex-shrink-0" />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="whitespace-nowrap overflow-hidden">
                    Settings
                  </motion.span>
                )}
              </AnimatePresence>
            </motion.div>
          </Link>
        </div>

        {/* Collapse */}
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="absolute -right-3.5 top-8 w-7 h-7 bg-[#1a2235] border border-white/10 rounded-full flex items-center justify-center text-slate-400 hover:text-white hover:bg-[#232d45] shadow-lg transition-colors z-30"
        >
          <motion.div animate={{ rotate: collapsed ? 180 : 0 }} transition={{ type: "spring", stiffness: 200, damping: 20 }}>
            <ChevronLeft size={14} />
          </motion.div>
        </button>
      </motion.aside>

      {/* Main Content Area */}
      <main className="flex-1 overflow-y-auto relative bg-[#070b12]">
        {/* Subtle background glow effect */}
        <div className="absolute top-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-[120px] pointer-events-none" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-blue-500/5 rounded-full blur-[150px] pointer-events-none" />
        
        <header className="sticky top-0 z-10 bg-[#070b12]/80 backdrop-blur-xl border-b border-white/5 px-6 sm:px-10 py-4 h-[73px] flex items-center">
          <div className="flex items-center justify-between w-full">
            <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
              <h2 className="text-lg font-bold bg-clip-text text-transparent bg-gradient-to-r from-emerald-100 to-emerald-300">Ali Garments</h2>
              <p className="text-xs text-emerald-500/60 font-medium tracking-wide">HYDERABAD, PAKISTAN</p>
            </motion.div>
            
            <div className="flex items-center gap-6">
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/5 border border-white/5 backdrop-blur-md shadow-sm"
                role="status"
              >
                {workforceActive ? (
                  <>
                    <Loader2 size={14} className="text-emerald-400 animate-spin" />
                    <span className="text-xs text-emerald-400 font-semibold tracking-wide">Workforce Active</span>
                  </>
                ) : (
                  <>
                    <motion.div animate={{ scale: [1, 1.2, 1] }} transition={{ repeat: Infinity, duration: 2 }} className="w-2 h-2 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.6)]" />
                    <span className="text-xs text-slate-300 font-medium">Agents Online</span>
                  </>
                )}
              </motion.div>
              
              <motion.button
                whileHover={{ scale: 1.05, ring: 2 }}
                whileTap={{ scale: 0.95 }}
                className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-400 to-orange-500 flex items-center justify-center text-sm font-bold text-orange-950 shadow-[0_0_15px_rgba(245,158,11,0.2)] ring-2 ring-transparent hover:ring-amber-500/40 transition-shadow"
              >
                AA
              </motion.button>
            </div>
          </div>
        </header>
        
        <div className="p-6 sm:p-10 relative z-10 max-w-7xl mx-auto">{children}</div>
      </main>
    </div>
  );
}

