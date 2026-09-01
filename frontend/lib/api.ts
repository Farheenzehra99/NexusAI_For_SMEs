const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export async function fetchApi<T>(path: string, timeoutMs = 120000): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(`${API_BASE}${path}`, {
      cache: "no-store",
      signal: controller.signal,
    });
    if (!res.ok) {
      // FastAPI errors are {"detail": "..."} — surface them cleanly.
      let detail = "";
      try {
        const body = await res.json();
        if (body && typeof body.detail === "string") detail = body.detail;
      } catch {
        detail = await res.text().catch(() => "");
      }
      if (res.status === 404) {
        throw new ApiError(404, detail || "Not found. Is the backend seeded?");
      }
      if (res.status === 503) {
        throw new ApiError(503, detail || "Backend database unavailable. Try again shortly.");
      }
      throw new ApiError(res.status, detail || `Request failed (${res.status})`);
    }
    return res.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new ApiError(0, "The request timed out. Please try again.");
    }
    throw new ApiError(0, "Cannot reach the backend. Is it running on port 8000?");
  } finally {
    clearTimeout(timer);
  }
}

export async function checkHealth(): Promise<{
  status: string;
  service: string;
  version: string;
  database: string;
}> {
  return fetchApi("/api/health", 15000);
}

// ── Dashboard ───────────────────────────────────────────────────────────────

export interface MetricCard {
  label: string;
  value: number;
  change: number | null;
  prefix: string;
  change_label?: string;
  note?: string | null;
}

export interface SalesTrendPoint {
  month: string;
  revenue: number;
  profit: number;
}

export interface ProductSummary {
  name: string;
  sku?: string;
  sales: number;
  revenue: number;
  trend?: string | null;
  reason?: string | null;
  stock_qty?: number | null;
}

export interface InventoryAlertItem {
  item: string;
  status: string;
  qty: number;
  estimated_revenue_at_risk?: number;
  days_of_stock_remaining?: number | null;
  recommended_reorder_qty?: number | null;
  excess_stock_qty?: number | null;
}

export interface Recommendation {
  title: string;
  description: string;
  priority: string; // urgent|high|medium|low
  impact?: string;
  agent: string;
  evidence?: string[];
  expected_impact?: string;
}

export interface DomainScoreSummary {
  domain: string;
  label: string;
  score: number;
  weight: number;
}

export interface ActivityItem {
  agent: string;
  action: string;
  finding?: string;
  data_points?: string;
  time: string;
}

export interface DashboardData {
  business_name: string;
  owner_name: string;
  location: string;
  health_score: number | null;
  risk_level: string | null;
  health_formula: string | null;
  as_of_date: string | null;
  weakest_domain: string | null;
  strongest_domain: string | null;
  domain_scores: DomainScoreSummary[];
  missing_domains: string[];
  total_customers: number;
  established_year: number;
  metrics: MetricCard[];
  sales_trend: SalesTrendPoint[];
  top_products: ProductSummary[];
  weak_products: ProductSummary[];
  inventory_alerts: InventoryAlertItem[];
  support_ticket_summary: {
    total: number;
    open: number;
    resolved: number;
    complaints: number;
    negative: number;
  };
  campaign_summary: {
    total: number;
    active: number;
    paused: number;
    total_spend: number;
    total_revenue: number;
    underperforming: string[];
  };
  expense_summary: {
    total_monthly: number;
    categories: Record<string, number>;
  };
  recommendations: Recommendation[];
  recent_activity: ActivityItem[];
}

export async function getDashboard(): Promise<DashboardData> {
  return fetchApi("/api/dashboard");
}

// ── Agents ──────────────────────────────────────────────────────────────────

export interface AgentInfo {
  name: string;
  role: string;
  description: string;
  status: string;
  icon: string;
  color: string;
  tasks: string[];
}

export interface AgentListResponse {
  agents: AgentInfo[];
  total_active: number;
}

export async function getAgents(): Promise<AgentListResponse> {
  return fetchApi("/api/agents", 15000);
}

export interface AgentActivityItem {
  agent_name: string;
  action: string;
  finding: string;
  data_points: string;
  created_at: string;
}

export interface AgentActivityResponse {
  activities: AgentActivityItem[];
  total: number;
}

export async function getAgentActivities(): Promise<AgentActivityResponse> {
  return fetchApi("/api/agent-activities", 15000);
}

// ── CEO Agent (orchestration) ───────────────────────────────────────────────

export interface RoutingDecision {
  domain: string;
  agent_name: string;
  reason: string;
  consulted: boolean;
}

export interface KeyFinding {
  domain: string;
  agent_name: string;
  statement: string;
  severity: string; // negative|positive|neutral
}

export interface RootCause {
  title: string;
  statement: string;
  contributing_domains: string[];
  evidence: string[];
}

export interface RecommendedAction {
  priority: string; // urgent|high|medium|low
  title: string;
  description: string;
  domain: string;
  agent_name: string;
  evidence: string[];
  expected_impact: string;
}

export interface DomainScore {
  domain: string;
  label: string;
  score: number;
  weight: number;
  data_available: boolean;
  components: { rule: string; points: number; reason: string }[];
}

export interface HealthScore {
  score: number;
  risk_level: string; // low|moderate|high|critical
  formula: string;
  domain_scores: DomainScore[];
  weakest_domain: string | null;
  strongest_domain: string | null;
}

export interface CEOAnswer {
  question: string;
  understood_as: string;
  routing: RoutingDecision[];
  consulted_agents: string[];
  missing_agents: string[];
  incomplete_analysis: boolean;
  incomplete_reason: string | null;
  health_score: HealthScore | null;
  key_findings: KeyFinding[];
  root_causes: RootCause[];
  recommended_actions: RecommendedAction[];
}

export interface CEOAnalysisResponse {
  agent: string;
  question: string;
  answer: CEOAnswer;
  interpretation: string;
  interpretation_source: string; // "llm" | "fallback"
  generated_at: string;
}

export async function askCeo(question: string): Promise<CEOAnalysisResponse> {
  const res = await fetchApi<CEOAnalysisResponse>(
    `/api/ceo/analysis?question=${encodeURIComponent(question)}`
  );
  // Guard against malformed responses so the UI never crashes on bad data.
  if (!res || !res.answer || !Array.isArray(res.answer.recommended_actions)) {
    throw new ApiError(0, "The CEO Agent returned a malformed response.");
  }
  return res;
}

export interface RouteStep {
  domain: string;
  agent_name: string;
  reason: string;
}

export interface CEORouteResponse {
  agent: string;
  question: string;
  understood_as: string;
  routing: RouteStep[];
}

export async function routeCeoQuestion(question: string): Promise<CEORouteResponse> {
  const res = await fetchApi<CEORouteResponse>(
    `/api/ceo/route?question=${encodeURIComponent(question)}`,
    30000
  );
  if (!res || !Array.isArray(res.routing) || res.routing.length === 0) {
    throw new ApiError(0, "The CEO Agent returned a malformed routing decision.");
  }
  return res;
}

// ── Specialist agent analyses (Command Center progress) ─────────────────────
// Only the fields the Command Center's progress headlines consume are
// declared; the backend responses contain the full facts objects.

export interface FinanceAnalysisResponse {
  agent: string;
  facts: {
    revenue: {
      current_revenue: number;
      peak_month: string;
      decline_from_peak_percent: number;
      trend: string;
    };
    profit: {
      current_margin_percent: number;
      peak_margin_percent: number;
      margin_compression_pp: number;
    };
  };
}

export async function getFinanceAnalysis(): Promise<FinanceAnalysisResponse> {
  return fetchApi("/api/finance/analysis");
}

export interface InventoryAnalysisResponse {
  agent: string;
  facts: {
    summary: {
      total_active_products: number;
      at_risk_count: number;
      critical_count: number;
      overstock_count: number;
    };
    risks: Array<{ product: string; risk_level: string; reason: string }>;
  };
}

export async function getInventoryAnalysis(): Promise<InventoryAnalysisResponse> {
  return fetchApi("/api/inventory/analysis");
}

export interface MarketingAnalysisResponse {
  agent: string;
  facts: {
    benchmark: { conversion_rate_percent: number };
    campaigns: Array<{ name: string; performance: string; reason: string }>;
    underperforming_campaign_names: string[];
  };
}

export async function getMarketingAnalysis(): Promise<MarketingAnalysisResponse> {
  return fetchApi("/api/marketing/analysis");
}

export interface SupportAnalysisResponse {
  agent: string;
  facts: {
    summary: { total_tickets: number };
    top_theme: string | null;
    themes: Array<{
      theme: string;
      label: string;
      count: number;
      share_percent: number;
      open_count: number;
    }>;
    delivery: {
      total_tickets: number;
      share_percent: number;
      open_count: number;
    };
  };
}

export async function getSupportAnalysis(): Promise<SupportAnalysisResponse> {
  return fetchApi("/api/support/analysis");
}

export interface BIAnalysisResponse {
  agent: string;
  facts: {
    health_score: {
      score: number;
      risk_level: string;
      weakest_domain: string | null;
      strongest_domain: string | null;
    };
  };
}

export async function getBIAnalysis(): Promise<BIAnalysisResponse> {
  return fetchApi("/api/bi/analysis");
}
