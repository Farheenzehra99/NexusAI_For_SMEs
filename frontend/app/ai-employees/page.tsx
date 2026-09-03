"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Crown,
  Calculator,
  Package,
  Megaphone,
  Headphones,
  BarChart3,
  Sparkles,
  Activity,
  CheckCircle2,
  Clock,
  ArrowRight,
  ShieldCheck,
  Zap,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import {
  getAgents,
  getAgentActivities,
  type AgentInfo,
  type AgentActivityItem,
} from "@/lib/api";

const iconMap: Record<string, React.ElementType> = {
  crown: Crown,
  calculator: Calculator,
  package: Package,
  megaphone: Megaphone,
  chart: BarChart3,
  headset: Headphones,
};

const gradientMap: Record<string, string> = {
  emerald: "from-emerald-400 to-emerald-600",
  blue: "from-blue-500 to-indigo-600",
  purple: "from-purple-500 to-violet-600",
  violet: "from-violet-500 to-fuchsia-600",
  gold: "from-amber-400 to-orange-500",
  rose: "from-rose-500 to-pink-600",
};

const badgeMap: Record<string, string> = {
  emerald: "bg-emerald-500/10 border-emerald-500/20 text-emerald-400",
  blue: "bg-blue-500/10 border-blue-500/20 text-blue-400",
  purple: "bg-purple-500/10 border-purple-500/20 text-purple-400",
  violet: "bg-violet-500/10 border-violet-500/20 text-violet-400",
  gold: "bg-amber-500/10 border-amber-500/20 text-amber-400",
  rose: "bg-rose-500/10 border-rose-500/20 text-rose-400",
};

function timeAgo(iso: string): string {
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return "unknown";
  const minutes = Math.max(0, Math.floor((Date.now() - then) / 60000));
  if (minutes < 1) return "just now";
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours} hour${hours > 1 ? "s" : ""} ago`;
  const days = Math.floor(hours / 24);
  return `${days} day${days > 1 ? "s" : ""} ago`;
}

export default function AIEmployeesPage() {
  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [activities, setActivities] = useState<AgentActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([getAgents(), getAgentActivities()])
      .then(([agentsRes, actRes]) => {
        setAgents(agentsRes.agents);
        setActivities(actRes.activities);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  const latestByAgent = new Map<string, AgentActivityItem>();
  for (const a of activities) {
    if (!latestByAgent.has(a.agent_name)) latestByAgent.set(a.agent_name, a);
  }

  const stats = [
    { label: "Active AI Employees", value: agents.length.toString() || "6", icon: Activity, color: "text-emerald-400" },
    { label: "Insights Discovered", value: activities.length.toString() || "5", icon: Sparkles, color: "text-amber-400" },
    { label: "Collaboration Rate", value: "100%", icon: Zap, color: "text-blue-400" },
    { label: "SME Domains Covered", value: "4 Domains", icon: CheckCircle2, color: "text-purple-400" },
  ];

  return (
    <Sidebar>
      <div className="space-y-8 max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <motion.div initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }}>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-extrabold tracking-tight text-white">
                AI Employees &amp; Workforce
              </h1>
              <span className="px-3 py-1 rounded-full text-xs font-bold bg-emerald-500/10 border border-emerald-500/30 text-emerald-400 flex items-center gap-1.5 shadow-[0_0_15px_rgba(16,185,129,0.2)]">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                6 Online
              </span>
            </div>
            <p className="text-sm text-slate-400 mt-1">
              Your autonomous business management team — continuously analyzing, collaborating, and executing.
            </p>
          </motion.div>

          <Link href="/command-center">
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-slate-950 font-bold rounded-xl text-sm shadow-[0_0_20px_rgba(16,185,129,0.3)] transition-all"
            >
              <span>Command Center</span>
              <ArrowRight size={16} />
            </motion.button>
          </Link>
        </div>

        {/* Stats Row */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stats.map((stat, idx) => (
            <motion.div
              key={stat.label}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.08 }}
              className="bg-[#0e1522]/80 border border-white/10 rounded-2xl p-5 backdrop-blur-xl flex items-center gap-4 hover:border-white/20 transition-all shadow-lg"
            >
              <div className="w-12 h-12 rounded-xl bg-black/40 border border-white/5 flex items-center justify-center flex-shrink-0">
                <stat.icon size={22} className={stat.color} />
              </div>
              <div>
                <p className="text-xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-slate-400">{stat.label}</p>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Error Notification */}
        {error && (
          <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-400 text-xs">
            {error}
          </div>
        )}

        {/* Agent Cards Grid */}
        {loading ? (
          <div className="text-center py-20 text-slate-400">Loading AI Workforce...</div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <AnimatePresence>
              {agents.map((agent, idx) => {
                const Icon = iconMap[agent.icon] || Sparkles;
                const grad = gradientMap[agent.color] || gradientMap.blue;
                const badgeStyle = badgeMap[agent.color] || badgeMap.blue;
                const last = latestByAgent.get(agent.name);
                const online = agent.status === "active";

                return (
                  <motion.div
                    key={agent.name}
                    initial={{ opacity: 0, y: 25 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.08, duration: 0.4 }}
                    whileHover={{ y: -4, borderColor: "rgba(255,255,255,0.2)" }}
                    className="bg-[#0e1522]/90 border border-white/10 rounded-3xl p-6 backdrop-blur-2xl flex flex-col justify-between shadow-[0_10px_30px_rgba(0,0,0,0.4)] group transition-all"
                  >
                    <div>
                      {/* Top Bar: Icon + Role + Status */}
                      <div className="flex items-start justify-between gap-4 mb-4">
                        <div className="flex items-center gap-3">
                          <div
                            className={`w-14 h-14 rounded-2xl bg-gradient-to-br ${grad} flex items-center justify-center shadow-lg group-hover:scale-105 transition-transform`}
                          >
                            <Icon size={26} className="text-white drop-shadow-md" />
                          </div>
                          <div>
                            <h3 className="font-bold text-lg text-white leading-tight">
                              {agent.name}
                            </h3>
                            <span className={`inline-block mt-1 px-2.5 py-0.5 rounded-full text-[11px] font-semibold border ${badgeStyle}`}>
                              {agent.role}
                            </span>
                          </div>
                        </div>

                        <span className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-black/40 border border-white/5 text-[11px] font-medium text-emerald-400">
                          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                          Online
                        </span>
                      </div>

                      {/* Description */}
                      <p className="text-xs text-slate-300 leading-relaxed mb-5">
                        {agent.description}
                      </p>

                      {/* Capabilities / Tasks */}
                      <div className="space-y-2 mb-6">
                        <p className="text-[11px] font-bold uppercase tracking-wider text-slate-500">
                          Primary Responsibilities
                        </p>
                        {agent.tasks.slice(0, 4).map((task) => (
                          <div key={task} className="flex items-center gap-2 text-xs text-slate-300">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                            <span className="truncate">{task}</span>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Bottom: Latest Insight + Deploy Button */}
                    <div className="pt-4 border-t border-white/5 space-y-3">
                      {last ? (
                        <div className="p-3 rounded-xl bg-black/40 border border-white/5">
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mb-1">
                            <span className="font-semibold text-slate-300">Recent Live Finding</span>
                            <span className="flex items-center gap-1">
                              <Clock size={10} />
                              {timeAgo(last.created_at)}
                            </span>
                          </div>
                          <p className="text-xs text-slate-200 line-clamp-2 leading-snug">
                            {last.action}
                          </p>
                        </div>
                      ) : (
                        <div className="text-[11px] text-slate-500 italic py-1">
                          Standing by in background
                        </div>
                      )}

                      <Link href="/command-center" className="block w-full">
                        <motion.button
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="w-full py-2.5 px-4 bg-white/5 hover:bg-white/10 border border-white/10 text-white rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-colors group-hover:border-emerald-500/30 group-hover:text-emerald-300"
                        >
                          <span>Ask in Command Center</span>
                          <ArrowRight size={14} />
                        </motion.button>
                      </Link>
                    </div>
                  </motion.div>
                );
              })}
            </AnimatePresence>
          </div>
        )}
      </div>
    </Sidebar>
  );
}
