# NexusAI for SMEs — Implementation Specification

> **Version:** 1.0  
> **Date:** September 2026  
> **Stage:** Pre-MVP (prototype complete, specification for production build)  
> **Status:** Not yet implemented — this document defines what to build next.

---

## 1. Product Goal

NexusAI for SMEs gives a Pakistani small/medium enterprise **an AI workforce** that:

1. Continuously monitors the business's operational data.
2. Presents a clear, real-time picture of business health.
3. Answers the owner's business questions by coordinating specialized AI agents.
4. Delivers **evidence-based, prioritized action plans** — not generic advice.

The owner should feel they have a **team of competent AI employees** working together, not a chatbot.

---

## 2. Target User

### Business Type (MVP Scope)

**One business type only:** Pakistani clothing / retail SME.

### Demo Business

**Ali Garments** — a fictional mid-size clothing retailer based in Lahore, Pakistan.

| Field      | Value               |
|------------|---------------------|
| Name       | Ali Garments        |
| Tagline    | Premium Pakistani Clothing |
| Owner      | Ahmed Ali           |
| Location   | Lahore, Pakistan    |
| Currency   | PKR (Rs)            |
| Products   | Lawn, Kurti, Shalwar Kameez, Pret, Bridal Wear |

### Owner Persona

- Small business owner, not technically sophisticated.
- Needs clear, actionable guidance — not dashboards full of raw data.
- Asks questions in plain language (e.g., "Why are my sales going down?").
- Wants to know **what to do next** and **why**.

---

## 3. AI Workforce

### 3.1 Agent Definitions

Each agent has a **clearly bounded responsibility**. Agents do not overlap or duplicate.

#### CEO Agent — Chief Coordinator

| Aspect     | Definition |
|------------|------------|
| **Role**   | Orchestrates all other agents. Single point of contact for the business owner. |
| **Responsibilities** | Parse owner questions, determine which agents to involve, coordinate parallel analysis, synthesize findings into a prioritized action plan. |
| **Boundaries** | Does NOT analyze data directly. Does NOT make domain-specific recommendations. Only coordinates and prioritizes. |
| **Input**  | Owner's natural-language question. |
| **Output** | Final action plan with prioritized actions, assigned agents, and evidence references. |

#### Finance Agent — Financial Analyst

| Aspect     | Definition |
|------------|------------|
| **Role**   | Owns all financial analysis for the business. |
| **Responsibilities** | Revenue trend analysis, profit margin tracking, cost breakdown, cash flow monitoring, financial anomaly detection. |
| **Boundaries** | Does NOT touch inventory levels, marketing metrics, or customer data. Only analyzes financial data. |
| **Input**  | Financial data (revenue, costs, margins, transactions). |
| **Output** | Financial findings with specific numbers and trend direction. |

#### Inventory Agent — Supply Chain Manager

| Aspect     | Definition |
|------------|------------|
| **Role**   | Owns stock management and supply chain analysis. |
| **Responsibilities** | Stock level monitoring, demand forecasting, reorder alerts, overstock/understock identification, supplier lead time tracking. |
| **Boundaries** | Does NOT make pricing decisions. Does NOT analyze marketing or financial projections. Only reports on inventory state and supply chain health. |
| **Input**  | Inventory data (stock levels, reorder points, sales velocity per SKU). |
| **Output** | Inventory findings with specific stock alerts, missed-sales estimates, and capital-at-risk figures. |

#### Marketing Agent — Growth Strategist

| Aspect     | Definition |
|------------|------------|
| **Role**   | Owns marketing performance and competitive intelligence. |
| **Responsibilities** | Ad spend analysis, channel performance (social media, in-store), campaign ROI, competitor activity monitoring, customer acquisition cost tracking. |
| **Boundaries** | Does NOT handle inventory, financial analysis, or customer complaints. Only analyzes marketing channels and competitive landscape. |
| **Input**  | Marketing data (ad spend, engagement metrics, campaign results, competitor intelligence). |
| **Output** | Marketing findings with channel performance data and competitive insights. |

#### Customer Support Agent — Customer Experience Lead

| Aspect     | Definition |
|------------|------------|
| **Role**   | Owns customer satisfaction and support intelligence. |
| **Responsibilities** | Complaint tracking, sentiment analysis, return/refund monitoring, delivery issue detection, customer retention metrics. |
| **Boundaries** | Does NOT handle marketing campaigns, financial analysis, or product pricing. Only monitors customer-facing experience. |
| **Input**  | Customer data (support tickets, reviews, return rates, delivery logs). |
| **Output** | Customer experience findings with complaint patterns, satisfaction scores, and issue volumes. |

#### Business Intelligence (BI) Agent — Cross-Domain Synthesizer

| Aspect     | Definition |
|------------|------------|
| **Role**   | Combines findings from all agents into a unified business picture. |
| **Responsibilities** | Cross-domain pattern recognition, seasonal trend analysis, competitive benchmarking, opportunity identification, macro-level business health assessment. |
| **Boundaries** | Does NOT make operational decisions. Does NOT replace domain agents. Only synthesizes and finds patterns across other agents' outputs. |
| **Input**  | Findings from all other agents + historical business data. |
| **Output** | Combined diagnosis with cross-domain insights and opportunity identification. |

### 3.2 Agent Collaboration Model

```
Owner Question
    │
    ▼
┌──────────────┐
│  CEO Agent   │ ← Parses question, selects relevant agents
└──────┬───────┘
       │ delegates
       ▼
┌──────────────────────────────────────────┐
│  Specialized Agents (parallel analysis)  │
│  ┌──────────┐ ┌───────────┐ ┌─────────┐ │
│  │ Finance  │ │ Inventory │ │Marketing│ │
│  └────┬─────┘ └─────┬─────┘ └────┬────┘ │
│  ┌────┴──────┐ ┌────┴────┐               │
│  │  Customer │ │   BI    │               │
│  │  Support  │ │ Agent   │               │
│  └─────┬─────┘ └────┬────┘               │
│        ▼            ▼                    │
│   Agent Findings (each reports back)     │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────────┐
│  BI Agent combines findings into         │
│  unified business picture                │
└──────────────────┬───────────────────────┘
                   │
                   ▼
┌──────────────┐
│  CEO Agent   │ ← Prioritizes actions, assigns owners
└──────┬───────┘
       │
       ▼
   Action Plan → Owner
```

**Rules:**

- CEO Agent decides which agents to involve based on the question. Not every question requires all 6 agents.
- Specialized agents analyze in parallel (not sequentially).
- BI Agent always participates last in the analysis phase to synthesize.
- CEO Agent always produces the final output — the owner never talks directly to specialized agents.
- Each action in the plan has a **priority** (High / Medium / Low) and an **assigned agent**.

---

## 4. Core Business Flow

### 4.1 Data Layer

Business data is ingested and stored. For MVP, the data schema covers:

| Data Domain   | Key Entities |
|---------------|-------------|
| Sales         | Orders, line items, revenue per product, revenue per period |
| Products      | SKU, name, category, price, cost, stock quantity, reorder threshold |
| Customers     | Customer ID, name, order history, support tickets |
| Marketing     | Campaign, channel, spend, impressions, clicks, conversions |
| Finance       | Revenue, COGS, gross profit, net profit, expenses by category |
| Support       | Ticket ID, type, status, sentiment, resolution time |

**For MVP:** Data is seeded from a structured dataset (JSON/CSV import or seed script). No live integrations with Shopify, Daraz, Facebook, or payment gateways.

### 4.2 Application Flow

```
Business Data (seeded)
    │
    ▼
Dashboard
  - Health Score (composite metric)
  - Revenue, Profit, Orders, Customers (KPI cards with trends)
  - Sales/Profit trend chart (6-month window)
  - Top products / Underperforming products
  - Inventory alerts (critical / low / overstock)
  - AI Recommendations (proactive, from agents)
  - Recent AI Workforce Activity feed
    │
    │  owner clicks "Ask the CEO Agent"
    ▼
AI Command Center
  - Owner types or selects a question
  - CEO Agent acknowledges and explains delegation
  - Specialized agents analyze their domains (shown in real-time)
  - BI Agent synthesizes cross-domain findings
  - CEO Agent delivers prioritized action plan
    │
    │  owner reviews
    ▼
Action Plan
  - Each action has: priority, description, assigned agent, evidence
  - Owner can accept/dismiss actions (MVP: accept only)
```

---

## 5. Critical Demo Scenario

### Question: "Why are my sales going down?"

This is the **primary demo path**. The system MUST handle this scenario end-to-end with a coherent, data-backed explanation.

### Required Data Story

The demo data must support ALL FOUR of the following causal factors:

| Factor | Supporting Data | Agent Responsible |
|--------|----------------|-------------------|
| **Declining sales** | Revenue down 8.3% MoM (Rs 5.1M → Rs 4.6M → Rs 4.85M). Formal Shalwar Kameez -18%, Summer Pret -22%. | Finance Agent |
| **Low stock of bestseller** | Embroidered Kurti White at 5 units (critical). Estimated Rs 150K+ in missed sales. Lawn Print Design A at 23 units (low). | Inventory Agent |
| **Underperforming marketing** | Social media ad spend cut 30% in July. Instagram engagement down 15%. Competitor "Khan Fabrics" running aggressive summer sale. | Marketing Agent |
| **Increasing delivery complaints** | Customer Support detected 12 delivery delay complaints this week (up from 3 previous week). Return rate increased to 4.2%. | Customer Support Agent |

### Additional Context (BI Agent)

- Seasonal trend: 12% industry-wide formal wear decline during summer.
- Ali Garments' Lawn segment outperforms market average by 8%.
- Opportunity: Eid collection pre-launch timing.

### Expected Action Plan Output

| Priority | Action | Assigned Agent |
|----------|--------|----------------|
| **High** | Restock Embroidered Kurti White — rush order 200 units from supplier | Inventory Agent |
| **High** | Launch targeted Instagram campaign for Lawn Collection (Rs 50,000 budget) | Marketing Agent |
| **High** | Investigate delivery partner performance — escalate or switch courier | Customer Support Agent |
| **Medium** | Clearance sale on Formal Shalwar Navy (480 units) at 20% discount | Inventory Agent |
| **Medium** | Pre-launch Eid collection marketing 3 weeks early | Marketing Agent |
| **Low** | Evaluate discontinuing Kids Festive Wear — reallocate budget | Finance Agent |

### Demo Flow Timing (for hackathon presentation)

The full flow should complete in under 15 seconds:

1. Owner question appears (0s)
2. CEO Agent acknowledges and delegates (1–2s)
3. Agent findings appear progressively (3–8s)
4. BI Agent synthesizes (9–10s)
5. CEO Agent delivers action plan (11–14s)

---

## 6. Business Health Score

### Definition

A single composite score (0–100) that gives the owner an at-a-glance understanding of overall business condition.

### Calculation (MVP)

| Component | Weight | Source |
|-----------|--------|--------|
| Revenue trend (MoM change) | 25% | Finance Agent |
| Profit margin health | 20% | Finance Agent |
| Inventory health (stockout/overstock ratio) | 20% | Inventory Agent |
| Customer satisfaction (complaint rate) | 15% | Customer Support Agent |
| Marketing efficiency (ROAS trend) | 10% | Marketing Agent |
| Growth trajectory (vs market) | 10% | BI Agent |

### Display Rules

| Score Range | Color | Status Label |
|-------------|-------|--------------|
| 80–100 | Green (emerald) | Excellent |
| 60–79 | Yellow (amber) | Moderate — Action needed in N areas |
| 40–59 | Orange | Warning — Immediate attention required |
| 0–39 | Red | Critical — Multiple areas at risk |

### Update Frequency

Recalculated whenever new data is ingested. For MVP demo: recalculated on page load from seeded data.

---

## 7. Acceptance Criteria

### 7.1 Dashboard

- [ ] Dashboard loads in under 3 seconds on a standard connection.
- [ ] Displays Business Health Score as a circular gauge with correct color coding.
- [ ] Shows 4 KPI cards: Revenue, Profit, Orders, Customers — each with value, PKR formatting, and MoM trend arrow.
- [ ] Revenue & Profit trend chart renders a 6-month area chart with both series.
- [ ] Inventory alerts section shows at least 4 items with status indicators (critical/low/overstock).
- [ ] Top 5 products displayed with sales volume, revenue, and trend direction.
- [ ] Underperforming products section shows at least 3 items with diagnostic reasons.
- [ ] AI Recommendations section shows at least 4 items with impact levels (high/medium/low) and source agent.
- [ ] Recent AI Workforce Activity feed shows at least 5 entries with agent name, action, and relative timestamp.
- [ ] All currency values formatted in PKR (Rs X, Rs XK, Rs XM).

### 7.2 Business Data

- [ ] Seed data contains at minimum: 50 products, 6 months of sales data, 10 customers, 3 marketing campaigns, 20 support tickets.
- [ ] Data is internally consistent (e.g., revenue totals match sum of order values).
- [ ] Data supports the critical demo scenario (all 4 causal factors present and linked).
- [ ] Product catalog includes Pakistani clothing categories (Lawn, Kurti, Shalwar Kameez, Pret, Bridal).
- [ ] All data values are realistic for a mid-size Lahore clothing retailer.

### 7.3 Each AI Employee

- [ ] All 6 agents are listed on the AI Employees page with name, role, description, and task list.
- [ ] Each agent shows an online/offline status indicator.
- [ ] Each agent has a distinct visual identity (icon + color).
- [ ] Agent detail view shows: recent actions, last analysis timestamp, key metrics monitored.
- [ ] The 6 agents are: CEO Agent, Finance Agent, Inventory Agent, Marketing Agent, Customer Support Agent, BI Agent.

### 7.4 Agent Collaboration

- [ ] CEO Agent correctly identifies which agents to involve based on the question category.
- [ ] At minimum 4 question types are supported with distinct agent combinations:
  - Revenue/sales questions → Finance + Inventory + Marketing + BI
  - Inventory questions → Inventory + Finance + BI
  - Customer questions → Customer Support + BI + Marketing
  - Strategy questions → CEO + all agents + BI
- [ ] Agent findings are displayed with agent name, icon, and domain-specific data.
- [ ] BI Agent always participates in the synthesis phase after specialized agents report.
- [ ] CEO Agent's final output references specific findings from specific agents.

### 7.5 Business Health Score

- [ ] Score is calculated as a weighted composite of 6 components.
- [ ] Score updates when underlying data changes.
- [ ] Visual gauge correctly reflects the score with appropriate color coding.
- [ ] Status label below gauge accurately describes the score range and number of problem areas.
- [ ] Score is between 0–100 and displayed as an integer.

### 7.6 AI Command Center

- [ ] Input field accepts free-text questions.
- [ ] At least 4 suggested questions are displayed as clickable chips.
- [ ] The flow visualization shows all stages: Question → CEO → Agents → Synthesis → Action Plan.
- [ ] Each stage is visually connected with animated flow indicators.
- [ ] Agent response cards appear progressively (not all at once).
- [ ] The complete flow finishes in under 15 seconds.
- [ ] The critical demo question ("Why are my sales going down?") produces the full 4-factor analysis and 6-item action plan.
- [ ] Action plan items have: priority badge, description, assigned agent name.
- [ ] "Execute Plan" button is visible (functional in future stage, visual-only in MVP).

### 7.7 Actionable Recommendations

- [ ] Every recommendation has: title, description, impact level, source agent.
- [ ] Impact levels are: high, medium, low — with distinct visual styling.
- [ ] Recommendations are derived from agent analysis, not generic templates.
- [ ] Recommendations reference specific data points (e.g., "Rs 150K revenue at risk", "480 units overstocked").
- [ ] Dashboard shows at least 4 proactive recommendations.
- [ ] Command Center action plan shows at least 5 prioritized actions.

### 7.8 Error Handling

- [ ] If the AI backend is unreachable, show a clear error state — not a blank screen.
- [ ] If a question is completely unrecognized, CEO Agent responds: "I'm not sure how to help with that. Try asking about your sales, inventory, customers, or marketing."
- [ ] Network errors show a retry button.
- [ ] Invalid/empty input is rejected gracefully.
- [ ] Loading states exist for all async operations (question processing, data fetching).

### 7.9 Testing

- [ ] Unit tests cover Health Score calculation logic.
- [ ] Unit tests verify agent selection logic (which agents are chosen for which question type).
- [ ] Integration test: the critical demo scenario runs end-to-end and produces expected output.
- [ ] Visual regression: dashboard and command center render correctly at 1280px and 1440px widths.
- [ ] All tests pass in CI before merge.

### 7.10 Demo Readiness

- [ ] Application can be demonstrated in under 2 minutes without any manual setup.
- [ ] Opening the app loads the dashboard with pre-seeded Ali Garments data.
- [ ] Clicking "Ask the CEO Agent" navigates to the Command Center.
- [ ] Clicking the "Why are my sales going down?" chip runs the full critical demo flow.
- [ ] No console errors in production build.
- [ ] Build passes `tsc --noEmit` with zero errors.
- [ ] Lighthouse performance score ≥ 85 on desktop.

---

## 8. Out of Scope (Explicitly Excluded)

The following are **not part of the MVP** and must not be built:

| Excluded Item | Reason |
|---------------|--------|
| Mobile app (iOS/Android) | MVP is web-only. Responsive web covers mobile viewing. |
| Multiple industries / business types | MVP supports Pakistani clothing/retail only. |
| Payment processing system | No transactions. Advisory platform only. |
| Full WhatsApp integration | No messaging integrations in MVP. |
| Shopify / Daraz / Facebook integrations | Data is seeded, not fetched from live platforms. |
| Custom machine learning models | Use LLM-based agents with structured prompts. No training. |
| Large admin panel | Minimal settings only. No user management, no role-based access. |
| Real-time data streaming / WebSocket dashboards | Data refreshes on page load or manual trigger. |
| Multi-language / Urdu interface | English only for MVP. |
| Multi-tenant architecture | Single-business deployment for MVP. |
| Automated action execution | "Execute Plan" button is visual only — no actual order placement or campaign launching. |
| Historical data import tooling | Data is pre-seeded via seed script, not user-imported. |

---

## 9. Technical Stack (Recommended for MVP)

Based on the existing prototype, continue with:

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 18 + TypeScript | Already scaffolded |
| Styling | Tailwind CSS 3 | Dark theme with custom palette |
| Charts | Recharts | Already installed |
| Icons | Lucide React | Already installed |
| Routing | React Router v7 | Already configured |
| Backend | Node.js + Express (or Next.js API routes) | New — not in prototype |
| Database | PostgreSQL or SQLite | New — stores seeded business data |
| AI / Agents | OpenAI API (GPT-4) with structured prompts | New — each agent is a prompt template |
| State | React Context or Zustand | For Command Center flow state |
| Build | Vite 5 | Already configured |

---

## 10. Prototype → MVP Migration Notes

Items from the current prototype that need to be replaced or enhanced:

| Prototype Element | MVP Change |
|-------------------|-----------|
| `mockData.ts` (hardcoded) | Replace with database queries via API |
| `commandCenterFlow` (static) | Replace with real LLM agent calls |
| `setTimeout`-based animation | Replace with streaming/SSE from agent backend |
| Health Score (hardcoded `72`) | Calculate from real data using weighted formula |
| Suggestion chips (4 fixed) | Generate from data context or keep as curated set |
| "Execute Plan" button (no-op) | Remains visual-only in MVP |
| BrowserRouter | Keep, but add fallback routing for SPA deployment |
| No loading states | Add skeletons, spinners, and error boundaries |
| No backend | Add API layer (REST) for data + agent orchestration |

---

## Appendix A: Spec Review — Issues Found & Resolved

During specification review, the following issues were identified and addressed:

| # | Issue | Resolution |
|---|-------|-----------|
| 1 | Prototype Command Center uses the same flow for ALL questions | Spec requires at minimum 4 question categories with distinct agent routing (§7.4) |
| 2 | Customer Support Agent missing from Command Center demo flow | Added delivery complaints as 3rd required causal factor + action item in critical scenario (§5) |
| 3 | Health Score was hardcoded (72) with no calculation defined | Added weighted formula with 6 components (§6) |
| 4 | No error handling defined | Added error handling acceptance criteria (§7.8) |
| 5 | No data schema defined | Added data domain table with key entities (§4.1) |
| 6 | "Execute Plan" button ambiguous | Clarified as visual-only in MVP scope (§8) |
| 7 | No fallback for unrecognized questions | Added graceful fallback response in error handling (§7.8) |
| 8 | Agent routing logic undefined | Spec now defines which agents are involved per question category (§7.4) |
