"use client";

import { useEffect, useState } from "react";
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
  emerald: "from-emerald-500 to-emerald-700",
  blue: "from-blue-500 to-blue-700",
  purple: "from-purple-500 to-purple-700",
  violet: "from-violet-500 to-violet-700",
  gold: "from-amber-500 to-amber-700",
  rose: "from-rose-500 to-rose-700",
};

const tagBgMap: Record<string, string> = {
  emerald: "bg-emerald-500/10 text-emerald-400",
  blue: "bg-blue-500/10 text-blue-400",
  purple: "bg-purple-500/10 text-purple-400",
  violet: "bg-violet-500/10 text-violet-400",
  gold: "bg-amber-500/10 text-amber-400",
  rose: "bg-rose-500/10 text-rose-400",
};

/** Hover glow matching each agent's theme color (from the backend registry). */
const glowMap: Record<string, string> = {
  emerald: "agent-glow-emerald",
  blue: "agent-glow-blue",
  purple: "agent-glow-purple",
  violet: "agent-glow-violet",
  gold: "agent-glow-gold",
  rose: "agent-glow-rose",
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
  const [error, setError] = useState<string | null>(null);
  const [activitiesError, setActivitiesError] = useState<string | null>(null);

  useEffect(() => {
    getAgents()
      .then((res) => setAgents(res.agents))
      .catch((err) => setError(err.message));
    getAgentActivities()
      .then((res) => setActivities(res.activities))
      .catch(() => setActivitiesError("Activity log unavailable"));
  }, []);

  if (error) {
    return (
      <Sidebar>
        <div className="flex items-center justify-center h-64">
          <div className="card border-red-500/30 text-center">
            <p className="text-red-400 text-sm font-medium">Failed to load agents</p>
            <p className="text-xs text-slate-400 mt-2">{error}</p>
          </div>
        </div>
      </Sidebar>
    );
  }

  // Real workforce stats from the activity log.
  const insightsLogged = activities.length;
  const latest = activities[0];

  const latestByAgent = new Map<string, AgentActivityItem>();
  for (const a of activities) {
    if (!latestByAgent.has(a.agent_name)) latestByAgent.set(a.agent_name, a);
  }

  const stats = [
    { label: "Active Agents", value: agents.length.toString(), icon: Activity, color: "text-emerald-400" },
    { label: "Insights Logged", value: insightsLogged.toString(), icon: Sparkles, color: "text-amber-400" },
    {
      label: "Latest Activity",
      value: latest ? timeAgo(latest.created_at) : "—",
      icon: Clock,
      color: "text-blue-400",
    },
    { label: "Specialist Domains", value: "4", icon: CheckCircle2, color: "text-purple-400" },
  ];

  return (
    <Sidebar>
      <div className="space-y-8 animate-slide-up">
        <div>
          <h1 className="text-2xl font-bold heading-ai heading-ai-purple">AI Employees</h1>
          <p className="text-sm text-slate-400 mt-1">
            Your dedicated AI workforce — each agent specializes in a key area of your business.
          </p>
        </div>

        {/* Stats — computed from the live agent registry and activity log */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {stats.map((stat) => (
            <div key={stat.label} className="card flex items-center gap-4">
              <stat.icon size={20} className={stat.color} />
              <div>
                <p className="text-xl font-bold text-white">{stat.value}</p>
                <p className="text-xs text-slate-400">{stat.label}</p>
              </div>
            </div>
          ))}
        </div>

        {activitiesError && (
          <p className="text-xs text-amber-400/80">{activitiesError}</p>
        )}

        {/* Agent Grid */}
        {agents.length === 0 ? (
          <div className="flex items-center justify-center h-32" role="status" aria-live="polite">
            <p className="text-slate-400 text-sm animate-pulse">Loading agents...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            {agents.map((agent) => {
              const Icon = iconMap[agent.icon] || Sparkles;
              const grad = gradientMap[agent.color] || gradientMap.blue;
              const tag = tagBgMap[agent.color] || tagBgMap.blue;
              const last = latestByAgent.get(agent.name);
              const online = agent.status === "active";
              return (
                <div
                  key={agent.name}
                  className={`glass-card glass-card-hover ${
                    glowMap[agent.color] || glowMap.blue
                  } p-5 group cursor-pointer`}
                >
                  <div className="flex items-center gap-3 mb-3">
                    <div
                      className={`w-12 h-12 rounded-xl bg-gradient-to-br ${grad} flex items-center justify-center shadow-lg transition-transform duration-200 group-hover:scale-105`}
                    >
                      <Icon size={22} className="text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-semibold text-white">{agent.name}</p>
                      <p className="text-xs text-slate-400">{agent.role}</p>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <span
                        className={`w-2 h-2 rounded-full ${
                          online ? "status-dot bg-emerald-500 text-emerald-500" : "bg-slate-500"
                        }`}
                        aria-hidden
                      />
                      <span className={`text-[10px] font-medium ${online ? "text-emerald-400" : "text-slate-500"}`}>
                        {online ? "Online" : "Idle"}
                      </span>
                    </div>
                  </div>
                  <p className="text-xs text-slate-400 leading-relaxed mb-4">{agent.description}</p>
                  <div className="space-y-1.5">
                    {agent.tasks.slice(0, 4).map((task) => (
                      <div key={task} className="flex items-center gap-2">
                        <span className={`w-1.5 h-1.5 rounded-full ${tag.split(" ")[1]}`} />
                        <span className="text-[11px] text-slate-300">{task}</span>
                      </div>
                    ))}
                  </div>
                  <div className="mt-4 pt-3 border-t border-slate-700/40">
                    {last ? (
                      <div>
                        <div className="flex items-center gap-1.5 min-w-0">
                          <span className="w-1 h-1 rounded-full bg-emerald-400 animate-standby flex-shrink-0" aria-hidden />
                          <p className="text-[11px] text-slate-300 truncate" title={last.action}>
                            Last: {last.action}
                          </p>
                        </div>
                        <p className="text-[10px] text-slate-500 mt-0.5">{timeAgo(last.created_at)}</p>
                      </div>
                    ) : (
                      <p className="text-[11px] text-slate-500">No recorded activity yet</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Sidebar>
  );
}
