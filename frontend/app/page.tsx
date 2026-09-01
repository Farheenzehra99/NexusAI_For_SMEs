"use client";

import { useEffect, useState } from "react";
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
          <div className="card border-red-500/30 text-center" role="alert">
            <p className="text-red-400 text-sm font-medium">Failed to load dashboard</p>
            <p className="text-xs text-slate-400 mt-2">{error}</p>
            <p className="text-xs text-slate-500 mt-1">Ensure the backend is running and seeded.</p>
          </div>
        </div>
      </Sidebar>
    );
  }

  if (!data) {
    return (
      <Sidebar>
        <div className="flex items-center justify-center h-64" role="status" aria-live="polite">
          <p className="text-slate-400 text-sm animate-pulse">Loading dashboard...</p>
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

  // Time-aware greeting — the dashboard should never say "Good morning" at 9 PM.
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? "Good morning" : hour < 17 ? "Good afternoon" : "Good evening";

  return (
    <Sidebar>
      <div className="space-y-8 animate-slide-up">
        {/* Welcome */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold heading-ai heading-ai-emerald">
              {greeting}, {data.owner_name.split(" ")[0]}
            </h1>
            <p className="text-sm text-slate-400 mt-1">
              Here&apos;s your business overview
              {data.as_of_date ? ` · data through ${formatDate(data.as_of_date)}` : ""}
            </p>
          </div>
          <Link
            href="/command-center"
            className="ai-btn flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-emerald-500 hover:from-emerald-500 hover:to-emerald-400 text-white text-sm font-semibold rounded-xl transition-all shadow-lg shadow-emerald-900/30"
          >
            Ask the CEO Agent
            <ArrowRight size={16} className="ai-btn-icon" />
          </Link>
        </div>

        {/* Metrics Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 lg:gap-5">
          {/* Health Score — computed live by the BI Agent */}
          <div className="card glow-emerald flex flex-col items-center justify-center py-6">
            <p className="text-xs uppercase tracking-wider text-slate-400 mb-3">Business Health Score</p>
            <div className="relative w-32 h-32">
              <svg className="w-full h-full -rotate-90" viewBox="0 0 120 120">
                <circle cx="60" cy="60" r="52" fill="none" stroke="#1e293b" strokeWidth="8" />
                <circle cx="60" cy="60" r="52" fill="none" stroke={scoreColor} strokeWidth="8" strokeLinecap="round" strokeDasharray={circumference} strokeDashoffset={offset} className="transition-all duration-1000 ease-out" />
              </svg>
              <div className="absolute inset-0 flex flex-col items-center justify-center">
                <span className="text-3xl font-bold text-white">
                  {health_score !== null ? health_score : "—"}
                </span>
                <span className="text-[10px] text-slate-400">/ 100</span>
              </div>
            </div>
            {risk ? (
              <p className={`mt-3 text-xs font-medium flex items-center gap-1 ${risk.text}`}>
                <ShieldCheck size={13} />
                {risk.label}
                {data.weakest_domain ? ` · weakest: ${data.weakest_domain}` : ""}
              </p>
            ) : (
              <p className="mt-3 text-xs text-slate-500 font-medium">Analysis unavailable</p>
            )}
            {data.domain_scores.length > 0 && (
              <div className="flex flex-wrap justify-center gap-1.5 mt-3">
                {data.domain_scores.map((d) => (
                  <span
                    key={d.domain}
                    title={`${d.label}: ${d.score}/100 (weight ${Math.round(d.weight * 100)}%)`}
                    className={`text-[10px] px-2 py-0.5 rounded-full bg-slate-800/80 border border-slate-700/50 ${DOMAIN_COLORS[d.domain] || "text-slate-300"}`}
                  >
                    {d.label} {d.score}
                  </span>
                ))}
              </div>
            )}
            {data.health_formula && (
              <p className="mt-2 text-[10px] text-slate-500 text-center leading-relaxed" title={data.health_formula}>
                weighted formula by the BI Agent
              </p>
            )}
          </div>

          {/* KPI Cards */}
          {data.metrics.map((m) => (
            <div key={m.label} className="card">
              <p className="text-xs text-slate-400 mb-1">{m.label}</p>
              <p className="text-2xl font-bold text-white">
                {m.prefix}{m.value >= 1000 ? formatPKR(m.value).replace("Rs ", "") : m.value.toLocaleString()}
              </p>
              {m.change !== null && m.change !== undefined ? (
                <div className={`flex items-center gap-1 mt-2 text-xs font-medium ${m.change >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {m.change >= 0 ? <TrendingUp size={14} /> : <TrendingDown size={14} />}
                  <span>{Math.abs(m.change)}% {m.change_label || "vs last month"}</span>
                </div>
              ) : m.note ? (
                <div className="flex items-center gap-1 mt-2 text-xs font-medium text-slate-400">
                  <Minus size={14} />
                  <span>{m.note}</span>
                </div>
              ) : (
                <div className="flex items-center gap-1 mt-2 text-xs font-medium text-slate-500">
                  <Minus size={14} />
                  <span>no comparison available</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Chart + Alerts */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">Revenue & Profit Trend</h2>
              <span className="text-xs text-slate-400">Last 6 months</span>
            </div>
            {data.sales_trend.length > 0 ? (
              <ResponsiveContainer width="100%" height={240}>
                <AreaChart data={data.sales_trend}>
                  <defs>
                    <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                    <linearGradient id="colorProf" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                  <XAxis dataKey="month" stroke="#64748b" fontSize={12} />
                  <YAxis stroke="#64748b" fontSize={11} tickFormatter={(v) => `${(v / 1000000).toFixed(1)}M`} />
                  <Tooltip contentStyle={{ backgroundColor: "#1e293b", border: "1px solid #334155", borderRadius: "8px", fontSize: "12px", color: "#fff" }} formatter={(value: any) => formatPKR(Number(value))} />
                  <Area type="monotone" dataKey="revenue" stroke="#10b981" strokeWidth={2} fill="url(#colorRev)" name="Revenue" />
                  <Area type="monotone" dataKey="profit" stroke="#3b82f6" strokeWidth={2} fill="url(#colorProf)" name="Profit" />
                </AreaChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-[240px] text-sm text-slate-500">
                No sales history recorded yet.
              </div>
            )}
          </div>

          <div className="card">
            <div className="flex items-center gap-2 mb-4">
              <Package size={16} className="text-amber-400" />
              <h2 className="text-sm font-semibold text-white">Inventory Alerts</h2>
            </div>
            {data.inventory_alerts.length > 0 ? (
              <div className="space-y-3">
                {data.inventory_alerts.map((alert, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-slate-700/40 last:border-0">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${alert.status === "critical" ? "bg-red-500" : alert.status === "low" ? "bg-amber-500" : alert.status === "overstock" ? "bg-purple-500" : "bg-blue-500"}`} />
                        <span className="text-xs text-slate-300 truncate">{alert.item}</span>
                      </div>
                      {(alert.days_of_stock_remaining != null || alert.recommended_reorder_qty || alert.excess_stock_qty) && (
                        <p className="text-[10px] text-slate-500 mt-0.5 ml-4">
                          {alert.status === "overstock" && alert.excess_stock_qty
                            ? `${alert.excess_stock_qty} units excess`
                            : alert.days_of_stock_remaining != null
                              ? `${alert.days_of_stock_remaining.toFixed(1)} days of stock left`
                              : ""}
                          {alert.recommended_reorder_qty ? ` · reorder ${alert.recommended_reorder_qty}` : ""}
                        </p>
                      )}
                    </div>
                    <span className={`text-xs font-semibold flex-shrink-0 ml-2 ${alert.status === "critical" ? "text-red-400" : alert.status === "low" ? "text-amber-400" : alert.status === "overstock" ? "text-purple-400" : "text-blue-400"}`}>{alert.qty}</span>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-slate-500">
                No inventory alerts — stock levels look healthy.
              </div>
            )}
          </div>
        </div>

        {/* Products */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <div className="card">
            <h2 className="text-sm font-semibold text-white mb-4">Top Products</h2>
            {data.top_products.length > 0 ? (
              <div className="space-y-3">
                {data.top_products.map((p, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b border-slate-700/40 last:border-0">
                    <div className="flex items-center gap-3">
                      <span className="text-xs text-slate-500 w-5">{i + 1}.</span>
                      <div>
                        <p className="text-sm text-white">{p.name}</p>
                        <p className="text-xs text-slate-400">{p.sales} units sold</p>
                      </div>
                    </div>
                    <div className="text-right flex items-center gap-2">
                      <span className="text-sm font-semibold text-white">{formatPKR(p.revenue)}</span>
                      {p.trend === "up" ? <TrendingUp size={14} className="text-emerald-400" /> : p.trend === "down" ? <TrendingDown size={14} className="text-red-400" /> : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-slate-500">
                No product sales recorded yet.
              </div>
            )}
          </div>

          <div className="card border-red-500/10">
            <div className="flex items-center gap-2 mb-4">
              <AlertTriangle size={16} className="text-red-400" />
              <h2 className="text-sm font-semibold text-white">Underperforming Products</h2>
            </div>
            {data.weak_products.length > 0 ? (
              <div className="space-y-3">
                {data.weak_products.map((p, i) => (
                  <div key={i} className="py-2 border-b border-slate-700/40 last:border-0">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-white">{p.name}</p>
                      <span className="text-xs text-slate-400">{p.sales} units</span>
                    </div>
                    {p.reason && <p className="text-xs text-red-400/80 mt-1">{p.reason}</p>}
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-slate-500">
                No underperforming products detected.
              </div>
            )}
          </div>
        </div>

        {/* Recommendations + Activity */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 card">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-sm font-semibold text-white">AI Recommendations</h2>
              <span className="text-xs text-slate-500">prioritized by the CEO Agent</span>
            </div>
            {data.recommendations.length > 0 ? (
              <div className="space-y-3">
                {data.recommendations.map((r, i) => (
                  <div key={i} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30 hover:border-emerald-500/20 transition-colors">
                    <div className="flex items-start gap-3">
                      <span className={`badge mt-0.5 uppercase tracking-wide flex-shrink-0 ${PRIORITY_BADGES[r.priority] || PRIORITY_BADGES.medium}`}>{r.priority}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-white">{r.title}</p>
                        <p className="text-xs text-slate-400 mt-1">{r.description}</p>
                        {r.evidence && r.evidence.length > 0 && (
                          <ul className="mt-1.5 space-y-0.5">
                            {r.evidence.slice(0, 2).map((e, j) => (
                              <li key={j} className="text-[11px] text-slate-500 flex items-start gap-1.5">
                                <span className="text-emerald-500/70 mt-px">•</span>
                                {e}
                              </li>
                            ))}
                          </ul>
                        )}
                        {r.expected_impact && (
                          <p className="text-[11px] text-emerald-400/70 mt-1.5">Impact: {r.expected_impact}</p>
                        )}
                        <p className="text-[10px] text-slate-500 mt-1.5">via {r.agent}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-slate-500">
                No recommendations available right now.
              </div>
            )}
          </div>

          <div className="card">
            <h2 className="text-sm font-semibold text-white mb-4">AI Workforce Activity</h2>
            {data.recent_activity.length > 0 ? (
              <div className="space-y-3">
                {data.recent_activity.map((a, i) => (
                  <div key={i} className="pb-3 border-b border-slate-700/30 last:border-0">
                    <p className="text-xs font-medium text-emerald-400">{a.agent}</p>
                    <p className="text-xs text-slate-300 mt-1">{a.action}</p>
                    <p className="text-[10px] text-slate-500 mt-1">{a.time}</p>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex items-center justify-center h-32 text-sm text-slate-500">
                No agent activity recorded yet.
              </div>
            )}
          </div>
        </div>
      </div>
    </Sidebar>
  );
}
