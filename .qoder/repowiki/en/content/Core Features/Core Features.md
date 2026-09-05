# Core Features

<cite>
**Referenced Files in This Document**
- [backend/app/agents/ceo.py](file://backend/app/agents/ceo.py)
- [backend/app/agents/finance.py](file://backend/app/agents/finance.py)
- [backend/app/agents/inventory.py](file://backend/app/agents/inventory.py)
- [backend/app/agents/marketing.py](file://backend/app/agents/marketing.py)
- [backend/app/agents/customer_support.py](file://backend/app/agents/customer_support.py)
- [backend/app/agents/bi.py](file://backend/app/agents/bi.py)
- [backend/app/services/ceo.py](file://backend/app/services/ceo.py)
- [backend/app/services/bi.py](file://backend/app/services/bi.py)
- [frontend/app/page.tsx](file://frontend/app/page.tsx)
- [frontend/app/command-center/page.tsx](file://frontend/app/command-center/page.tsx)
- [frontend/app/ai-employees/page.tsx](file://frontend/app/ai-employees/page.tsx)
</cite>

## Table of Contents
1. Introduction
2. AI Workforce (6 Agents)
3. Business Health Score
4. Command Center (CEO Q&A)
5. Dashboard
6. Multilingual Support
7. Authentication & Authorization

## Introduction
NexusAI provides six AI agents that function as a complete autonomous workforce for SMEs. Each agent specializes in one business domain, computes deterministic findings, and optionally uses an LLM for plain-language narration. The agents collaborate through the CEO Agent's orchestration layer.

## AI Workforce (6 Agents)

### CEO Agent (Orchestrator)
- Role: Chief Executive Officer
- Routes owner questions to specialized agents via trilingual keyword rules
- Synthesizes cross-agent findings into root causes and prioritized actions
- Records collaboration logs for the UI
- Guarantees a valid response even when individual agents fail

### Finance Agent
- Role: Financial Analyst
- Computes: Revenue trends, profit margins, expense breakdowns, margin compression, MoM changes
- Detects: Revenue decline from peak, declining trends, unusual financial changes
- Identifies top revenue products and weak performers

### Inventory Agent
- Role: Supply Chain Manager
- Computes: Stock levels, sales velocity, days of cover, risk classification
- Risk levels: critical, high, medium, out_of_stock, overstock, stagnant
- Calculates: Recommended reorder quantities and estimated reorder costs

### Marketing Agent
- Role: Growth Strategist
- Computes: CTR, conversion rate, cost per conversion, ROAS per campaign
- Detects: Underperforming campaigns via explainable rules
- Suggests: Budget reallocation from worst to best performer

### Customer Support Agent
- Role: Customer Experience Lead
- Computes: Negative feedback percentage, recurring issue themes, delivery problems
- Classifies: Sentiment via LLM for unclassified tickets (with keyword heuristic fallback)
- Preserves: Original customer feedback verbatim (never rewrites or paraphrases)

### BI Agent
- Role: Business Intelligence Analyst
- Computes: The Business Health Score (0–100) from all four domain agents
- Aggregates: Key signals across domains
- Reports: Weakest and strongest domains, data coverage gaps

**Section sources**
- [backend/app/agents/ceo.py:34-215](file://backend/app/agents/ceo.py#L34-L215)
- [backend/app/agents/finance.py:27-132](file://backend/app/agents/finance.py#L27-L132)
- [backend/app/agents/inventory.py:28-130](file://backend/app/agents/inventory.py#L28-L130)
- [backend/app/agents/marketing.py:30-129](file://backend/app/agents/marketing.py#L30-L129)
- [backend/app/agents/customer_support.py:30-165](file://backend/app/agents/customer_support.py#L30-L165)
- [backend/app/agents/bi.py:50-140](file://backend/app/agents/bi.py#L50-L140)

## Business Health Score
A documented, deterministic, weighted composite score:

| Domain | Weight | Key Deduction Rules |
|--------|--------|-------------------|
| Finance | 35% | Revenue decline, margin compression, declining trend, profit drop |
| Inventory | 25% | Critical stockout, out of stock, high/medium risk, overstock, stagnant |
| Marketing | 20% | Underperforming campaigns, low ROAS |
| Support | 20% | Negative feedback, low resolution rate, complaint surge |

Risk bands: Low (80–100), Moderate (60–79), High (40–59), Critical (0–39).

**Section sources**
- [backend/app/services/bi.py:1-73](file://backend/app/services/bi.py#L1-L73)

## Command Center (CEO Q&A)
The Command Center page provides a conversational interface:
1. Owner types a question (in English, Urdu, or Roman Urdu)
2. Frontend calls `GET /api/ceo/route` to show routing decisions
3. Frontend calls each specialist agent's analysis endpoint (progress visualization)
4. Frontend calls `GET /api/ceo/analysis` for the complete answer
5. Response includes: routing decisions, consulted agents, health score, key findings, root causes, and prioritized actions

**Section sources**
- [backend/app/services/ceo.py:182-191](file://backend/app/services/ceo.py#L182-L191)

## Dashboard
The main dashboard displays:
- Health Score ring (SVG circle animation)
- KPI metric cards (revenue, profit, margin, expenses, customers)
- Revenue & Profit trend chart (Recharts AreaChart, last 6 months)
- Inventory alerts panel (critical, low, overstock)
- Top Revenue Drivers and Underperforming/Overstocked products
- AI Recommendations with priority badges
- Live Workforce Activity feed (agent collaboration logs)

**Section sources**
- [frontend/app/page.tsx:1-421](file://frontend/app/page.tsx#L1-L421)

## Multilingual Support
- Three languages: English, Urdu (اردو), Roman Urdu
- Backend routing keywords support all three scripts
- LLM prompts include a language-matching rule for the CEO Agent
- Frontend locale files provide translated UI strings
- Language preference persisted in backend `UserSettings`

**Section sources**
- [backend/app/services/llm.py:113-137](file://backend/app/services/llm.py#L113-L137)
- [frontend/context/LanguageContext.tsx:1-75](file://frontend/context/LanguageContext.tsx#L1-L75)

## Authentication & Authorization
- Login/Signup with email and password
- JWT tokens stored in `localStorage` (`nexusai_token`)
- Business profile stored/cached in `localStorage` (`nexusai_user`)
- Protected routes redirect to `/login` on 401
- Backend `get_current_business()` dependency validates Bearer token
