"use client";

import { useEffect, useRef, useState } from "react";
import {
  Crown,
  Sparkles,
  Send,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Lightbulb,
  Search,
  ShieldCheck,
  Loader2,
  Circle,
  Calculator,
  Package,
  Megaphone,
  Headphones,
  BarChart3,
} from "lucide-react";
import Sidebar from "@/components/Sidebar";
import {
  askCeo,
  routeCeoQuestion,
  type CEOAnalysisResponse,
  type RootCause,
} from "@/lib/api";
import {
  DOMAIN_RUNNERS,
  STEP_DWELL_MS,
  runBI,
  withMinDelay,
} from "@/lib/agentSteps";
import { formatDateTime } from "@/lib/format";

const sampleQuestions = [
  "Meri sales kam kyun ho rahi hain aur mujhe kya karna chahiye?",
  "Business ki current situation analyze karo",
  "Why are my sales going down?",
  "Meri delivery ki shikayat kyun hai?",
  "میری سیلز کیوں گر رہی ہے؟",
  "Which products should I promote more?",
];

const SEVERITY_DOT: Record<string, string> = {
  negative: "bg-red-500",
  positive: "bg-emerald-500",
  neutral: "bg-slate-500",
};

const PRIORITY_BADGES: Record<string, string> = {
  urgent: "bg-red-500/20 text-red-400 border border-red-500/30",
  high: "bg-amber-500/20 text-amber-400 border border-amber-500/30",
  medium: "bg-blue-500/20 text-blue-400 border border-blue-500/30",
  low: "bg-slate-500/20 text-slate-300 border border-slate-500/30",
};

const RISK_TEXT: Record<string, string> = {
  low: "text-emerald-400",
  moderate: "text-amber-400",
  high: "text-orange-400",
  critical: "text-red-400",
};

const DOMAIN_ICON: Record<string, React.ElementType> = {
  finance: Calculator,
  inventory: Package,
  marketing: Megaphone,
  support: Headphones,
  bi: BarChart3,
  ceo: Crown,
};

// ── Orchestration step model ────────────────────────────────────────────────

type StepStatus = "pending" | "active" | "done" | "failed";

interface AgentStep {
  key: string;
  agentName: string;
  status: StepStatus;
  statusLabel: string;
  detail?: string; // real finding from the agent's response
  error?: string;
}

interface Exchange {
  id: number;
  question: string;
  steps: AgentStep[];
  response?: CEOAnalysisResponse;
  fatal?: string; // routing or final call failed
}

const pending = (key: string, agentName: string): AgentStep => ({
  key,
  agentName,
  status: "pending",
  statusLabel: "waiting",
});

// ── Small shared pieces ─────────────────────────────────────────────────────

function HealthSummary({ hs }: { hs: NonNullable<CEOAnalysisResponse["answer"]["health_score"]> }) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs">
      <span className="font-semibold text-white">
        Business Health Score: {hs.score}/100
      </span>
      <span className={`font-medium flex items-center gap-1 ${RISK_TEXT[hs.risk_level] || "text-slate-300"}`}>
        <ShieldCheck size={13} />
        {hs.risk_level} risk
      </span>
      <span className="text-slate-500 hidden lg:inline">{hs.formula}</span>
    </div>
  );
}

/** Compact BI summary: real domain sub-scores from the BI formula. */
function BICompactSummary({ hs }: { hs: NonNullable<CEOAnalysisResponse["answer"]["health_score"]> }) {
  const available = hs.domain_scores.filter((d) => d.data_available);
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5 text-xs">
      <span className={`font-semibold flex items-center gap-1.5 ${RISK_TEXT[hs.risk_level] || "text-slate-300"}`}>
        <ShieldCheck size={14} />
        Business Health {hs.score}/100 · {hs.risk_level} risk
      </span>
      <span className="w-px h-4 bg-slate-700/60 hidden sm:block" aria-hidden />
      {available.map((d) => (
        <span
          key={d.domain}
          className={`px-2 py-0.5 rounded-full border ${
            d.domain === hs.weakest_domain
              ? "border-amber-500/40 text-amber-400"
              : "border-slate-700/50 text-slate-400"
          }`}
          title={d.domain === hs.weakest_domain ? "Weakest domain" : undefined}
        >
          {d.label} {d.score}
          {d.domain === hs.weakest_domain ? " ▾" : ""}
        </span>
      ))}
    </div>
  );
}

// ── Agent collaboration flow graph ──────────────────────────────────────────

function StepIcon({ status }: { status: StepStatus }) {
  if (status === "done") return <CheckCircle2 size={14} className="text-emerald-400 flex-shrink-0" />;
  if (status === "active") return <Loader2 size={14} className="text-emerald-400 animate-spin flex-shrink-0" />;
  if (status === "failed") return <XCircle size={14} className="text-red-400 flex-shrink-0" />;
  return <Circle size={14} className="text-slate-600 flex-shrink-0" />;
}

const STATUS_LABEL_COLOR: Record<StepStatus, string> = {
  done: "text-emerald-400",
  active: "text-emerald-300",
  failed: "text-red-400",
  pending: "text-slate-500",
};

function FlowNodeCard({
  step,
  iconKey,
  compact = false,
}: {
  step: AgentStep;
  iconKey: string;
  compact?: boolean;
}) {
  const Icon = DOMAIN_ICON[iconKey] || Sparkles;
  return (
    <div
      className={`flow-node is-${step.status} w-full ${compact ? "p-3" : "p-4"}`}
      aria-label={`${step.agentName}: ${step.statusLabel}`}
    >
      <div className="flex items-center gap-2.5">
        <span
          className={`${
            compact ? "w-8 h-8" : "w-9 h-9"
          } rounded-lg bg-gradient-to-br from-slate-700/80 to-slate-800 flex items-center justify-center flex-shrink-0`}
        >
          <Icon size={compact ? 15 : 17} className="flow-node-icon text-emerald-300" />
        </span>
        <div className="min-w-0 flex-1">
          <p className={`font-medium text-slate-100 truncate ${compact ? "text-xs" : "text-sm"}`}>
            {step.agentName}
          </p>
          <p className={`text-[11px] truncate ${STATUS_LABEL_COLOR[step.status]}`}>
            {step.statusLabel}
          </p>
        </div>
        <StepIcon status={step.status} />
      </div>
      {(step.detail || step.error) && (
        <p
          className={`mt-2 text-[11px] leading-snug line-clamp-3 ${
            step.error ? "text-red-400/80" : "text-slate-400"
          }`}
          title={step.error || step.detail}
        >
          {step.error || step.detail}
        </p>
      )}
    </div>
  );
}

function Connector({ status }: { status: StepStatus }) {
  return (
    <div className={`flow-connector is-${status} mx-auto`} aria-hidden>
      <span className="flow-particle" />
    </div>
  );
}

/** The current pipeline stage, DERIVED from the real step states. */
function currentStage(steps: AgentStep[]): { label: string; detail: string; done: boolean } {
  const route = steps.find((s) => s.key === "route");
  const specialists = steps.filter((s) => !["route", "bi", "final"].includes(s.key));
  const bi = steps.find((s) => s.key === "bi");
  const final = steps.find((s) => s.key === "final");

  if (route?.status === "active")
    return { label: "Stage 1 · CEO Agent Activated", detail: "Understanding business question…", done: false };
  if (specialists.some((s) => s.status === "active"))
    return { label: "Stage 2 · Calling AI Employees", detail: "Specialists analyzing your business data…", done: false };
  if (bi?.status === "active")
    return { label: "Stage 3 · BI Agent", detail: "Compiling cross-agent insights…", done: false };
  if (final?.status === "active")
    return { label: "Stage 4 · CEO Agent", detail: "Generating final action plan…", done: false };
  if (final?.status === "done")
    return { label: "Analysis Complete", detail: "Action plan ready", done: true };
  if (route?.status === "done" && specialists.length > 0)
    return { label: "Stage 2 · Calling AI Employees", detail: "Specialists standing by…", done: false };
  return { label: "Stage 1 · CEO Agent Activated", detail: "Understanding business question…", done: false };
}

function WorkforceGraph({ steps }: { steps: AgentStep[] }) {
  const route = steps.find((s) => s.key === "route") ?? steps[0];
  const specialists = steps.filter((s) => !["route", "bi", "final"].includes(s.key));
  const bi = steps.find((s) => s.key === "bi");
  const final = steps.find((s) => s.key === "final");
  const stage = currentStage(steps);
  const failedCount = steps.filter((s) => s.status === "failed").length;

  return (
    <div className="card" role="status" aria-live="polite">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <Sparkles size={14} className="text-emerald-400" />
          <h2 className="text-xs font-semibold text-white">AI Workforce Collaboration</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className={`w-1.5 h-1.5 rounded-full ${stage.done ? "bg-emerald-400" : "bg-emerald-400 animate-standby"}`} aria-hidden />
          <span className="text-[10px] font-medium text-emerald-300/90 uppercase tracking-wider">
            {stage.label}
          </span>
          <span className="text-[10px] text-slate-500 hidden sm:inline">· {stage.detail}</span>
        </div>
      </div>

      {/* CEO → specialists → BI → CEO */}
      <div className="max-w-3xl mx-auto">
        {route && (
          <div className="max-w-xs mx-auto w-full">
            <FlowNodeCard step={route} iconKey="ceo" />
          </div>
        )}

        {specialists.length > 0 && (
          <>
            <Connector status={route ? route.status : "pending"} />
            {/* Distribution bus (desktop only) */}
            <div
              className={`flow-bus hidden md:block ${route?.status === "done" ? "is-done" : ""}`}
              style={{ margin: "0 12.5%" }}
              aria-hidden
            />
            <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
              {specialists.map((s) => (
                <div key={s.key} className="flex flex-col">
                  <div className="hidden md:block">
                    <Connector status={s.status} />
                  </div>
                  <FlowNodeCard step={s} iconKey={s.key} compact />
                </div>
              ))}
            </div>
          </>
        )}

        {bi && (
          <>
            <Connector status={bi.status} />
            <div className="max-w-xs mx-auto w-full">
              <FlowNodeCard step={bi} iconKey="bi" />
            </div>
          </>
        )}

        {final && (
          <>
            <Connector status={final.status} />
            <div className="max-w-xs mx-auto w-full">
              <FlowNodeCard step={final} iconKey="ceo" />
            </div>
          </>
        )}
      </div>

      {failedCount > 0 && (
        <p className="mt-4 text-[11px] text-amber-400/90 text-center">
          {failedCount} step{failedCount > 1 ? "s" : ""} could not complete — results from the
          remaining agents are preserved below.
        </p>
      )}
    </div>
  );
}

// ── Final answer ────────────────────────────────────────────────────────────

/** Pair each root cause with the recommended action from its domain (real data). */
function actionForCause(cause: RootCause, res: CEOAnalysisResponse) {
  return res.answer.recommended_actions.find((a) =>
    cause.contributing_domains.includes(a.domain)
  );
}

function CEOInsightSummary({ res }: { res: CEOAnalysisResponse }) {
  const a = res.answer;
  const issues = a.root_causes;

  const scrollToActions = () => {
    document.getElementById("ceo-actions")?.scrollIntoView({ behavior: "smooth", block: "start" });
  };

  return (
    <div className="rounded-xl border border-emerald-500/25 bg-gradient-to-b from-emerald-500/10 to-slate-800/40 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles size={14} className="text-emerald-400" />
        <h3 className="text-xs font-bold text-emerald-300 uppercase tracking-wider">✦ CEO Insight</h3>
      </div>

      {issues.length > 0 ? (
        <>
          <p className="text-sm font-semibold text-white mb-3">
            {issues.length} key issue{issues.length === 1 ? "" : "s"} detected
          </p>
          <ol className="space-y-2.5">
            {issues.slice(0, 3).map((cause, i) => {
              const action = actionForCause(cause, res);
              return (
                <li key={i} className="flex items-start gap-2.5">
                  <span className="text-xs font-semibold text-emerald-400/80 mt-0.5 flex-shrink-0">
                    {i + 1}.
                  </span>
                  <div className="min-w-0">
                    <p className="text-sm text-white leading-snug">{cause.title}</p>
                    {action && (
                      <p className="text-xs text-slate-400 mt-0.5">
                        <span className="text-emerald-400/70">→ </span>
                        {action.title}
                      </p>
                    )}
                  </div>
                </li>
              );
            })}
          </ol>
          {issues.length > 3 && (
            <p className="text-[11px] text-slate-500 mt-2">+ {issues.length - 3} more in Root Causes below</p>
          )}
        </>
      ) : (
        <p className="text-sm text-slate-300">No critical issues were detected for this question.</p>
      )}

      {a.recommended_actions.length > 0 && (
        <div className="mt-4 pt-3 border-t border-slate-700/40">
          <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-2">Priority Actions</p>
          <div className="flex flex-wrap gap-2">
            {a.recommended_actions.map((action, i) => (
              <button
                key={i}
                onClick={scrollToActions}
                title={action.title}
                className={`badge text-[11px] max-w-[240px] truncate hover:brightness-125 transition-all cursor-pointer ${PRIORITY_BADGES[action.priority] || PRIORITY_BADGES.medium}`}
              >
                <span className="uppercase tracking-wide mr-1.5">{action.priority}</span>
                <span className="truncate font-normal">{action.title}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {a.health_score && (
        <div className="mt-4 pt-3 border-t border-slate-700/40">
          <BICompactSummary hs={a.health_score} />
        </div>
      )}
    </div>
  );
}

function CEOAnswerCard({ res }: { res: CEOAnalysisResponse }) {
  const a = res.answer;
  return (
    <div className="card space-y-5">
      {/* CEO INSIGHT — the headline summary, all from real agent outputs */}
      <CEOInsightSummary res={res} />

      {/* What the CEO understood + which agents it consulted */}
      <div className="space-y-2">
        <p className="text-xs italic text-slate-400">{a.understood_as}</p>
        <div className="flex flex-wrap items-center gap-1.5">
          {a.routing.map((r) => (
            <span
              key={r.domain}
              title={r.reason}
              className={`text-[10px] px-2 py-1 rounded-full border ${
                r.consulted
                  ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                  : "bg-red-500/10 border-red-500/30 text-red-400"
              }`}
            >
              {r.consulted ? <CheckCircle2 size={10} className="inline mr-1 -mt-0.5" /> : <XCircle size={10} className="inline mr-1 -mt-0.5" />}
              {r.agent_name}
            </span>
          ))}
        </div>
      </div>

      {a.incomplete_analysis && a.incomplete_reason && (
        <div className="flex items-start gap-2 p-3 rounded-lg bg-amber-500/10 border border-amber-500/30">
          <AlertTriangle size={14} className="text-amber-400 mt-0.5 flex-shrink-0" />
          <p className="text-xs text-amber-300/90">{a.incomplete_reason}</p>
        </div>
      )}

      {a.health_score && <HealthSummary hs={a.health_score} />}

      {/* The CEO's plain-language explanation */}
      <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30">
        <p className="text-[10px] uppercase tracking-wider text-slate-500 mb-1.5">CEO Agent</p>
        <p dir="auto" className="text-sm text-slate-200 leading-relaxed whitespace-pre-line">{res.interpretation}</p>
      </div>

      {/* Key findings */}
      {a.key_findings.length > 0 && (
        <div>
          <h3 className="flex items-center gap-1.5 text-xs font-semibold text-white mb-2">
            <Search size={13} className="text-blue-400" />
            Key Findings
          </h3>
          <div className="space-y-1.5">
            {a.key_findings.map((f, i) => (
              <div key={i} className="flex items-start gap-2 text-xs">
                <span className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${SEVERITY_DOT[f.severity] || SEVERITY_DOT.neutral}`} />
                <span className="text-slate-300">
                  <span className="text-slate-500">{f.agent_name}: </span>
                  {f.statement}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Root causes */}
      {a.root_causes.length > 0 && (
        <div>
          <h3 className="flex items-center gap-1.5 text-xs font-semibold text-white mb-2">
            <AlertTriangle size={13} className="text-amber-400" />
            Root Causes
          </h3>
          <div className="space-y-2">
            {a.root_causes.map((c, i) => (
              <div key={i} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30">
                <p className="text-sm font-medium text-white">{c.title}</p>
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{c.statement}</p>
                {c.evidence.length > 0 && (
                  <ul className="mt-2 space-y-0.5">
                    {c.evidence.map((e, j) => (
                      <li key={j} className="text-[11px] text-slate-500 flex items-start gap-1.5">
                        <span className="text-amber-500/70 mt-px">•</span>
                        {e}
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Prioritized recommendations */}
      {a.recommended_actions.length > 0 ? (
        <div id="ceo-actions" className="scroll-mt-20">
          <h3 className="flex items-center gap-1.5 text-xs font-semibold text-white mb-2">
            <Lightbulb size={13} className="text-emerald-400" />
            Recommended Actions
          </h3>
          <div className="space-y-2">
            {a.recommended_actions.map((action, i) => (
              <div key={i} className="p-3 rounded-lg bg-slate-800/40 border border-slate-700/30 hover:border-emerald-500/20 transition-colors">
                <div className="flex items-start gap-3">
                  <span className={`badge mt-0.5 uppercase tracking-wide flex-shrink-0 ${PRIORITY_BADGES[action.priority] || PRIORITY_BADGES.medium}`}>
                    {action.priority}
                  </span>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-white">
                      {i + 1}. {action.title}
                    </p>
                    <p className="text-xs text-slate-400 mt-1">{action.description}</p>
                    {action.evidence.length > 0 && (
                      <ul className="mt-1.5 space-y-0.5">
                        {action.evidence.map((e, j) => (
                          <li key={j} className="text-[11px] text-slate-500 flex items-start gap-1.5">
                            <span className="text-emerald-500/70 mt-px">•</span>
                            {e}
                          </li>
                        ))}
                      </ul>
                    )}
                    {action.expected_impact && (
                      <p className="text-[11px] text-emerald-400/70 mt-1.5">
                        Impact: {action.expected_impact}
                      </p>
                    )}
                    <p className="text-[10px] text-slate-500 mt-1.5">via {action.agent_name}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex items-center justify-center py-6 text-sm text-slate-500">
          No actions recommended for this question.
        </div>
      )}

      <p className="text-[10px] text-slate-400">
        Generated {formatDateTime(res.generated_at)} · narrative source: {res.interpretation_source === "llm" ? "LLM" : "deterministic fallback"}
      </p>
    </div>
  );
}

// ── Standby empty state ─────────────────────────────────────────────────────

function StandbyState() {
  const agents = ["CEO", "Finance", "Inventory", "Marketing", "Support", "BI"];
  return (
    <div className="card border-dashed border-slate-600/50 text-center py-16">
      <div className="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 mb-5">
        <Sparkles size={22} className="text-emerald-400 animate-standby" />
      </div>
      <p className="text-base font-semibold text-white">Your AI workforce is standing by</p>
      <p className="text-xs text-slate-500 mt-2 max-w-md mx-auto leading-relaxed">
        Ask the CEO Agent a business question and watch the right specialists
        collaborate — Finance, Inventory, Marketing, Customer Support, and BI —
        each contributing verified findings from your real business data.
      </p>
      <div className="flex items-center justify-center flex-wrap gap-2.5 mt-7" aria-label="Standing by agents">
        {agents.map((name, i) => (
          <span key={name} className="flex items-center gap-1.5 text-[10px] px-2.5 py-1 rounded-full bg-slate-800/70 text-slate-400 border border-slate-700/50">
            <span
              className="w-1 h-1 rounded-full bg-emerald-400 animate-standby"
              style={{ animationDelay: `${i * 300}ms` }}
              aria-hidden
            />
            {name}
          </span>
        ))}
      </div>
    </div>
  );
}

// ── Page ────────────────────────────────────────────────────────────────────

export default function CommandCenterPage() {
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(false);
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(0);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [exchanges, loading]);

  // Tell the app header when the workforce is processing (real state).
  useEffect(() => {
    window.dispatchEvent(
      new CustomEvent("nexusai:workforce", { detail: { active: loading } })
    );
    return () => {
      window.dispatchEvent(
        new CustomEvent("nexusai:workforce", { detail: { active: false } })
      );
    };
  }, [loading]);

  function patchExchange(id: number, patch: Partial<Exchange>) {
    setExchanges((prev) =>
      prev.map((x) => (x.id === id ? { ...x, ...patch } : x))
    );
  }

  function patchStep(id: number, key: string, patch: Partial<AgentStep>) {
    setExchanges((prev) =>
      prev.map((x) =>
        x.id === id
          ? {
              ...x,
              steps: x.steps.map((s) =>
                s.key === key ? { ...s, ...patch } : s
              ),
            }
          : x
      )
    );
  }

  async function ask(question: string) {
    const q = question.trim();
    if (!q || loading) return;

    const id = nextId.current++;
    setExchanges((prev) => [
      ...prev,
      {
        id,
        question: q,
        steps: [
          {
            key: "route",
            agentName: "CEO Agent",
            status: "active",
            statusLabel: "investigating your question…",
          },
        ],
      },
    ]);
    setInputValue("");
    setLoading(true);

    try {
      // 1) The CEO Agent routes the question to the right specialists.
      const route = await withMinDelay(routeCeoQuestion(q), STEP_DWELL_MS);
      const specialists = route.routing;
      patchExchange(id, {
        steps: [
          {
            key: "route",
            agentName: "CEO Agent",
            status: "done",
            statusLabel: "investigation routed",
            detail: `Consulting ${specialists.map((s) => s.agent_name).join(", ")}`,
          },
          ...specialists.map((s) => pending(s.domain, s.agent_name)),
          pending("bi", "BI Agent"),
          pending("final", "CEO Agent"),
        ],
      });

      // 2) Each consulted specialist runs its REAL analysis in turn.
      for (const s of specialists) {
        patchStep(id, s.domain, { status: "active", statusLabel: "analyzing…" });
        const runner = DOMAIN_RUNNERS[s.domain];
        if (!runner) {
          patchStep(id, s.domain, {
            status: "failed",
            statusLabel: "could not complete",
            error: "No analysis runner for this agent.",
          });
          continue;
        }
        try {
          const result = await withMinDelay(runner(), STEP_DWELL_MS);
          patchStep(id, s.domain, { status: "done", ...result });
        } catch (err) {
          patchStep(id, s.domain, {
            status: "failed",
            statusLabel: "could not complete",
            error: err instanceof Error ? err.message : "Unexpected error",
          });
        }
      }

      // 3) The BI Agent compiles the cross-domain business picture.
      patchStep(id, "bi", {
        status: "active",
        statusLabel: "compiling the business picture…",
      });
      try {
        const result = await withMinDelay(runBI(), STEP_DWELL_MS);
        patchStep(id, "bi", { status: "done", ...result });
      } catch (err) {
        patchStep(id, "bi", {
          status: "failed",
          statusLabel: "could not complete",
          error: err instanceof Error ? err.message : "Unexpected error",
        });
      }

      // 4) The CEO Agent turns everything into a prioritized action plan.
      patchStep(id, "final", {
        status: "active",
        statusLabel: "preparing the action plan…",
      });
      try {
        const res = await askCeo(q);
        patchStep(id, "final", {
          status: "done",
          statusLabel: "action plan ready",
          detail: `${res.answer.recommended_actions.length} prioritized action${res.answer.recommended_actions.length === 1 ? "" : "s"}`,
        });
        patchExchange(id, { response: res });
      } catch (err) {
        const message = err instanceof Error ? err.message : "Unexpected error";
        patchStep(id, "final", {
          status: "failed",
          statusLabel: "could not complete",
          error: message,
        });
        // Surface a retry affordance — the specialist results above are
        // still valid and worth keeping on screen.
        patchExchange(id, { fatal: message });
      }
    } catch (err) {
      // Routing itself failed — the exchange cannot proceed.
      const message = err instanceof Error ? err.message : "Unexpected error";
      patchExchange(id, {
        fatal: message,
        steps: [
          {
            key: "route",
            agentName: "CEO Agent",
            status: "failed",
            statusLabel: "could not route the question",
            error: message,
          },
        ],
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <Sidebar>
      <div className="max-w-4xl mx-auto space-y-6 animate-slide-up pb-8">
        {/* Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-medium mb-4">
            <Sparkles size={14} />
            AI Command Center
          </div>
          <h1 className="text-3xl font-bold heading-ai heading-ai-emerald">Ask the CEO Agent</h1>
          <p className="text-sm text-slate-400 mt-2 max-w-lg mx-auto">
            The control room of your AI workforce — the CEO Agent routes your
            question to the right specialists and returns an evidence-backed
            action plan.
          </p>
        </div>

        {/* Input */}
        <div className="card p-0 overflow-hidden">
          <form
            className="flex items-center gap-3 p-4"
            onSubmit={(e) => {
              e.preventDefault();
              ask(inputValue);
            }}
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-emerald-500 to-emerald-700 flex items-center justify-center flex-shrink-0 shadow-lg shadow-emerald-900/40">
              <Crown size={16} className="text-white" />
            </div>
            <input
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              maxLength={500}
              dir="auto"
              placeholder="Ask the CEO Agent anything — English, Urdu, or Roman Urdu..."
              aria-label="Business question for the CEO Agent"
              className="flex-1 bg-transparent text-white text-sm placeholder-slate-500 outline-none min-w-0"
            />
            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="ai-btn btn-energy p-2 rounded-lg bg-emerald-500 hover:bg-emerald-400 disabled:bg-slate-700 disabled:cursor-not-allowed text-white"
              aria-label="Ask the CEO Agent"
            >
              {loading ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} className="ai-btn-icon" />}
            </button>
          </form>
          <div className="px-4 pb-3 flex flex-wrap gap-2">
            {sampleQuestions.map((q) => (
              <button
                key={q}
                dir="auto"
                onClick={() => ask(q)}
                disabled={loading}
                className="chip text-xs px-3 py-1.5 rounded-full border border-slate-700/50 text-slate-400 hover:text-white disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {q}
              </button>
            ))}
          </div>
        </div>

        {/* Conversation */}
        {exchanges.length === 0 && !loading && <StandbyState />}

        <div className="space-y-6">
          {exchanges.map((x) => (
            <div key={x.id} className="space-y-3">
              {/* The owner's question */}
              <div className="flex justify-end">
                <div className="max-w-[85%] px-4 py-2.5 rounded-xl rounded-tr-sm bg-emerald-600/20 border border-emerald-500/30">
                  <p dir="auto" className="text-sm text-white text-right">{x.question}</p>
                </div>
              </div>

              {/* Live collaboration visualization */}
              {x.steps.length > 0 && <WorkforceGraph steps={x.steps} />}

              {/* The CEO Agent's final answer */}
              {x.response ? (
                <CEOAnswerCard res={x.response} />
              ) : x.fatal ? (
                <div className="card border-red-500/30 text-center py-8">
                  <XCircle size={24} className="mx-auto text-red-400 mb-2" />
                  <p className="text-sm text-red-400 font-medium">The CEO Agent could not answer</p>
                  <p className="text-xs text-slate-400 mt-1">{x.fatal}</p>
                  <button
                    onClick={() => ask(x.question)}
                    disabled={loading}
                    className="mt-4 px-4 py-1.5 text-xs rounded-lg bg-slate-700/60 hover:bg-slate-600 text-slate-200 transition-colors disabled:opacity-50"
                  >
                    Try again
                  </button>
                </div>
              ) : null}
            </div>
          ))}
          <div ref={bottomRef} />
        </div>
      </div>
    </Sidebar>
  );
}
