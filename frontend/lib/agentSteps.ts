/**
 * Command Center agent-step orchestration helpers.
 *
 * Design rule: every step's status label and detail line is DERIVED from
 * the specialist agent's actual structured response — never hardcoded.
 * A step only shows "stock risk detected" (etc.) when the Inventory
 * Agent's real facts actually flag that condition.
 */

import {
  getBIAnalysis,
  getFinanceAnalysis,
  getInventoryAnalysis,
  getMarketingAnalysis,
  getSupportAnalysis,
} from "./api";

export interface StepResult {
  statusLabel: string;
  detail: string;
}

/** Run one specialist agent's REAL analysis and derive its headline. */
export const DOMAIN_RUNNERS: Record<
  string,
  () => Promise<StepResult>
> = {
  finance: async () => {
    const r = await getFinanceAnalysis();
    const rev = r.facts.revenue;
    const prof = r.facts.profit;
    const parts: string[] = [];
    if (rev.decline_from_peak_percent <= -5) {
      parts.push(
        `revenue ${rev.decline_from_peak_percent.toFixed(1)}% below the ${rev.peak_month} peak`
      );
    } else {
      parts.push(`revenue ${rev.trend}`);
    }
    if (prof.margin_compression_pp >= 2) {
      parts.push(
        `margin ${prof.current_margin_percent.toFixed(1)}% vs ${prof.peak_margin_percent.toFixed(1)}% peak`
      );
    }
    return {
      statusLabel: "financial analysis complete",
      detail: parts.join(" · "),
    };
  },

  inventory: async () => {
    const r = await getInventoryAnalysis();
    const s = r.facts.summary;
    if (s.critical_count > 0) {
      return {
        statusLabel: "stock risk detected",
        detail:
          r.facts.risks[0]?.reason ??
          `${s.critical_count} product(s) at critical stock level`,
      };
    }
    if (s.at_risk_count > 0) {
      return {
        statusLabel: "stock risks found",
        detail:
          r.facts.risks[0]?.reason ??
          `${s.at_risk_count} of ${s.total_active_products} products need attention`,
      };
    }
    return {
      statusLabel: "stock analysis complete",
      detail: `${s.total_active_products} products reviewed — no risks flagged`,
    };
  },

  marketing: async () => {
    const r = await getMarketingAnalysis();
    const flagged = r.facts.underperforming_campaign_names;
    if (flagged.length > 0) {
      const worst = r.facts.campaigns.find(
        (c) => c.performance === "underperforming"
      );
      return {
        statusLabel: "campaign issue detected",
        detail:
          worst?.reason ??
          `${flagged.join(", ")} underperforming the benchmark`,
      };
    }
    return {
      statusLabel: "campaigns reviewed",
      detail: `Benchmark conversion rate ${r.facts.benchmark.conversion_rate_percent}%`,
    };
  },

  support: async () => {
    const r = await getSupportAnalysis();
    const f = r.facts;
    if (f.top_theme === "delivery_problems") {
      return {
        statusLabel: "delivery issue detected",
        detail: `${f.delivery.total_tickets} of ${f.summary.total_tickets} tickets are delivery issues (${f.delivery.share_percent}%), ${f.delivery.open_count} still open`,
      };
    }
    const top = f.themes[0];
    if (top) {
      return {
        statusLabel: "customer feedback analyzed",
        detail: `Top theme: ${top.label} — ${top.count} of ${f.summary.total_tickets} tickets`,
      };
    }
    return {
      statusLabel: "customer feedback analyzed",
      detail: `${f.summary.total_tickets} tickets reviewed`,
    };
  },
};

/** BI compiles the cross-domain business picture. */
export async function runBI(): Promise<StepResult> {
  const r = await getBIAnalysis();
  const hs = r.facts.health_score;
  return {
    statusLabel: "business picture compiled",
    detail: `Health Score ${hs.score}/100 (${hs.risk_level} risk)`,
  };
}

/** Minimum per-step display time so the collaboration is visible even
 *  when the backend answers instantly. Results are still 100% real —
 *  this only paces the reveal. */
export const STEP_DWELL_MS = 700;

export function withMinDelay<T>(p: Promise<T>, ms: number): Promise<T> {
  return Promise.all([p, new Promise((r) => setTimeout(r, ms))]).then(
    ([res]) => res
  );
}
