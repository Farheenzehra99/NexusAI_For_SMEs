"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  TrendingDown,
  TrendingUp,
  Package,
  AlertTriangle,
  ArrowRight,
  Minus,
  ShieldCheck,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { getDashboard, type DashboardData } from "@/lib/api";
import { formatPKR, formatDate } from "@/lib/format";

const RISK_STYLES: Record<string, { text: string; label: string }> = {
  low: { text: "text-emerald-400", label: "Low risk" },
  moderate: { text: "text-amber-400", label: "Moderate risk" },
  high: { text: "text-orange-400", label: "High risk" },
  critical: { text: "text-red-400", label: "Critical risk" },
};

const PRIORITY_BADGES: Record<string, string> = {
  urgent: "bg-red-500/20 text-red-400 border border-red-500/30",
  high: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  medium: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  low: "bg-slate-500/20 text-slate-300 border border-slate-500/30",
};

const DOMAIN_COLORS: Record<string, string> = {
  finance: "text-blue-400",
  inventory: "text-purple-400",
  marketing: "text-amber-400",
  support: "text-rose-400",
};

// Animation Variants
const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.1, delayChildren: 0.1 }
  }
};

const itemVariants = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0, transition: { type: "spring" as const, stiffness: 300, damping: 24 } }
};

export default function DashboardPage() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getDashboard()
      .then(setData)
      .catch((err) => setError(err.message));
  }, []);

  if (error) {
    return (
      <Sidebar>
        <div className="flex items-center justify-center h-64">
          <div className="bg-red-500/10 border border-red-500/30 rounded-2xl p-6 text-center shadow-[0_0_30px_rgba(239,68,68,0.1)]" role="alert">
            <p className="text-red-400 font-medium">Failed to load dashboard</p>
            <p className="text-xs text-red-400/70 mt-2">{error}</p>
          </div>
        </div>
      </Sidebar>
    );
  }

  if (!data) {
    return (
      <Sidebar>
        <div className="flex items-center justify-center h-64">
          <motion.div 
            animate={{ scale: [1, 1.1, 1], opacity: [0.5, 1, 0.5] }} 
            transition={{ repeat: Infinity, duration: 2 }}
            className="w-12 h-12 rounded-full border-4 border-emerald-500/30 border-t-emerald-500"
          />
        </div>
      </Sidebar>
    );
  }

  const health_score = data.health_score;
  const risk = data.risk_level ? RISK_STYLES[data.risk_level] : null;
  const circumference = 2 * Math.PI * 52;
  const offset = health_score !== null ? circumference - (health_score / 100) * circumference : circumference;
  const scoreColor =
    health_score === null
      ? "#475569"
      : health_score >= 80
        ? "#10b981"
        : health_score >= 60
          ? "#f59e0b"
          : health_score >= 40
            ? "#f97316"
            : "#f43f5e";

  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <Sidebar>
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="space-y-8"
      >
        {/* Welcome */}
        <motion.div variants={itemVariants} className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-emerald-100 to-emerald-400">
              {greeting}, {data.owner_name.split(" ")[0]}
            </h1>
            <p className="text-sm text-slate-400 mt-1.5 font-medium">
              Here&apos;s your business overview
              {data.as_of_date ? ` · data through ${formatDate(data.as_of_date)}` : ""}
            </p>
          </div>
          <Link href="/command-center">
            <motion.div 
              whileHover={{ scale: 1.05, boxShadow: "0 0 20px rgba(16,185,129,0.4)" }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-emerald-600 text-white text-sm font-semibold rounded-xl transition-colors border border-emerald-400/50"
            >
              Ask the CEO Agent
              <ArrowRight size={16} />
            </motion.div>
          </Link>
        </motion.div>

        {/* Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 lg:gap-5">
          {/* Health Score */}
          <motion.div 
            variants={itemVariants}
            whileHover={{ y: -5, boxShadow: "0 10px 30px -10px rgba(16,185,129,0.3)" }}
            className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl flex flex-col items-center justify-center py-6 shadow-xl relative overflow-hidden"
          >
            <div className="absolute inset-0 bg-emerald-500/5" />
            <p className="text-[10px] uppercase tracking-widest text-emerald-500/80 font-bold mb-3 relative z-10">Health Score</p>
            <div className="relative w-32 h-32 z-10">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#1e293b" strokeWidth="8" />
                <motion.circle 
                  initial={{ strokeDashoffset: circumference }}
                  animate={{ strokeDashoffset: offset }}
                  transition={{ duration: 1.5, ease: "easeOut", delay: 0.5 }}
                  cx="60" cy="60" r="52" fill="none" stroke={scoreColor} strokeWidth="8" strokeLinecap="round" strokeDasharray={circumference} 
                />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-white drop-shadow-md">
                  {health_score !== null ? health_score : "—"}
                </span>
              </div>
            </div>
            {risk ? (
              <p className={`mt-3 text-xs font-semibold flex items-center gap-1 ${risk.text} relative z-10`}>
                <ShieldCheck size={13} />
                {risk.label}
              </p>
            ) : null}
          </motion.div>

          {/* KPI Cards */}
          {data.metrics.map((m, idx) => (
            <motion.div 
              key={m.label} 
              variants={itemVariants}
              whileHover={{ y: -5, backgroundColor: "rgba(30,41,59,0.8)" }}
              className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-5 shadow-xl flex flex-col justify-between transition-colors"
            >
              <p className="text-xs font-medium text-slate-400">{m.label}</p>
              <div className="mt-2">
                <p className="text-2xl font-bold text-white tracking-tight drop-shadow-sm">
                  {m.prefix}{m.value >= 1000 ? formatPKR(m.value).replace("Rs ", "") : m.value.toLocaleString()}
                </p>
                {m.change !== null && m.change !== undefined ? (
                  <div className={`flex items-center gap-1 mt-2 text-xs font-semibold ${m.change >= 0 ? "text-emerald-400" : "text-rose-400"}`}>
                    {m.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                    <span>{Math.abs(m.change)}% {m.change_label || "vs last month"}</span>
                  </div>
                ) : m.note ? (
                  <div className="flex items-center gap-1 mt-2 text-[11px] font-medium text-slate-500">
                    <span>{m.note}</span>
                  </div>
                ) : null}
              </div>
            </motion.div>
          ))}
        </div>

        {/* Chart + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <motion.div variants={itemVariants} className="lg:col-span-2 bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-sm font-bold text-white tracking-wide">Revenue & Profit Trend</h2>
              <span className="text-xs font-medium text-emerald-500/70 bg-emerald-500/10 px-2 py-1 rounded-md">Last 6 months</span>
            </div>
            {data.sales_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={260}>
                <AreaChart data={data.sales_trend} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorProf" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.4} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.05)" vertical={false} />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} dy={10} />
                  <YAxis stroke="#64748b" fontSize={11} tickLine={false} axisLine={false} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: "rgba(15,23,42,0.9)", backdropFilter: "blur(8px)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "12px", boxShadow: "0 10px 25px -5px rgba(0,0,0,0.5)" }}
                    itemStyle={{ color: "#fff", fontSize: "13px", fontWeight: 600 }}
                    formatter={(value: any) => formatPKR(Number(value))} 
                  />
                  <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={3} fill="url(#colorRev)" name="Revenue" activeDot={{ r: 6, fill: "#10b981", stroke: "#0f172a", strokeWidth: 2 }} />
                  <Area type="monotone" dataKey="profit" stroke="#3b82f6" strokeWidth={3} fill="url(#colorProf)" name="Profit" activeDot={{ r: 6, fill: "#3b82f6", stroke: "#0f172a", strokeWidth: 2 }} />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[260px] text-sm text-slate-500">No sales history.</div>
            )}
          </motion.div>

          <motion.div variants={itemVariants} className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl flex flex-col">
            <div className="flex items-center gap-2 mb-6">
              <div className="p-1.5 bg-amber-500/10 rounded-lg">
                <Package size={16} className="text-amber-400" />
              </div>
              <h2 className="text-sm font-bold text-white tracking-wide">Inventory Alerts</h2>
            </div>
            {data.inventory_alerts.length > 0 ? (
              <div className="space-y-4 flex-1 overflow-y-auto pr-2 custom-scrollbar">
                {data.inventory_alerts.map((alert, i) => (
                  <motion.div 
                    key={i} 
                    whileHover={{ scale: 1.02, x: 2 }}
                    className="flex items-start justify-between p-3 rounded-xl bg-white/5 border border-white/5"
                  >
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 shadow-[0_0_8px_currentColor] ${alert.status === "critical" ? "bg-red-500 text-red-500" : alert.status === "low" ? "bg-amber-500 text-amber-500" : alert.status === "overstock" ? "bg-purple-500 text-purple-500" : "bg-blue-500 text-blue-500"}`} />
                        <span className="text-sm font-medium text-slate-200 truncate">{alert.item}</span>
                      </div>
                      {(alert.days_of_stock_remaining != null || alert.recommended_reorder_qty || alert.excess_stock_qty) && (
                        <p className="text-xs text-slate-400 mt-1.5 ml-4">
                          {alert.status === "overstock" && alert.excess_stock_qty ? `${alert.excess_stock_qty} excess` : alert.days_of_stock_remaining != null ? `${alert.days_of_stock_remaining.toFixed(1)} days left` : ""}
                        </p>
                      )}
                    </div>
                    <span className={`text-sm font-bold flex-shrink-0 ml-3 ${alert.status === "critical" ? "text-red-400" : alert.status === "low" ? "text-amber-400" : alert.status === "overstock" ? "text-purple-400" : "text-blue-400"}`}>{alert.qty}</span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center flex-1 text-sm text-slate-500">All good.</div>
            )}
          </motion.div>
        </div>

        {/* Bottom Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-5">
          <motion.div variants={itemVariants} className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-white mb-5 tracking-wide">AI Recommendations</h2>
            <div className="space-y-4">
              {data.recommendations.slice(0, 3).map((r, i) => (
                <motion.div 
                  key={i} 
                  whileHover={{ scale: 1.01, backgroundColor: "rgba(255,255,255,0.05)" }}
                  className="p-4 rounded-xl bg-white/5 border border-white/5 relative overflow-hidden group"
                >
                  <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald-400 to-emerald-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                  <div className="flex items-start gap-4">
                    <span className={`px-2 py-1 text-[10px] uppercase font-bold rounded flex-shrink-0 ${PRIORITY_BADGES[r.priority] || PRIORITY_BADGES.medium}`}>{r.priority}</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white">{r.title}</p>
                      <p className="text-xs text-slate-400 mt-1 leading-relaxed">{r.description}</p>
                      {r.expected_impact && (
                        <p className="text-xs font-medium text-emerald-400 mt-2 bg-emerald-400/10 inline-block px-2 py-1 rounded">Impact: {r.expected_impact}</p>
                      )}
                    </div>
                  </div>
                </motion.div>
              ))}
            </div>
          </motion.div>

          <motion.div variants={itemVariants} className="bg-[#0e1522]/60 backdrop-blur-md border border-white/5 rounded-2xl p-6 shadow-xl">
            <h2 className="text-sm font-bold text-white mb-5 tracking-wide">Live Workforce Activity</h2>
            <div className="space-y-0">
              {data.recent_activity.map((a, i) => (
                <div key={i} className="flex gap-4 group">
                  <div className="flex flex-col items-center">
                    <div className="w-2.5 h-2.5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.8)] relative z-10" />
                    {i !== data.recent_activity.length - 1 && <div className="w-px h-full bg-white/10 group-hover:bg-emerald-500/30 transition-colors" />}
                  </div>
                  <div className="pb-6">
                    <p className="text-xs font-bold text-emerald-400">{a.agent}</p>
                    <p className="text-sm text-slate-300 mt-0.5">{a.action}</p>
                    <p className="text-[10px] text-slate-500 mt-1 font-medium">{a.time}</p>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </motion.div>
    </Sidebar>
  );
}
