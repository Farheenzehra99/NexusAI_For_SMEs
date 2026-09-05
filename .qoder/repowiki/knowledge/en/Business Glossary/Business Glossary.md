---
kind: business_term
name: Business Glossary
category: business_term
scope:
    - '**'
---

### NexusAI
- Definition: AI Workforce platform for Pakistani SMEs. Provides six specialized AI agents (CEO, Finance, Inventory, Marketing, Customer Support, BI) that function as a complete autonomous business operations team. The demo business is "Ali Garments", a Pakistani clothing retailer.
- Aliases: NexusAI for SMEs, SME Growth OS

### Business Health Score
- Definition: A 0–100 deterministic composite score computed by the BI Agent. Formula: 35% Finance + 25% Inventory + 20% Marketing + 20% Support. Each domain sub-score starts at 100 and applies documented deduction rules. Risk bands: Low (80–100), Moderate (60–79), High (40–59), Critical (0–39). Weights are re-normalized when a domain's data is unavailable.
- Aliases: Health Score, BHS

### CEO Agent
- Definition: The orchestration layer of the AI workforce. Routes owner questions to specialized agents via trilingual keyword rules (English, Urdu script, Roman Urdu), gathers findings through the BI snapshot, and synthesizes root causes and prioritized actions using fixed deterministic rules. The LLM only narrates the finished plan.
- Aliases: CEO, Orchestrator

### Finance Agent
- Definition: Monitors revenue, expenses, profit, and margins using deterministic calculations. Computes P&L analysis, expense breakdowns, profit margin tracking, financial anomaly detection, and cash flow monitoring. Never uses LLM for calculations.
- Aliases: Financial Analyst

### Inventory Agent
- Definition: Tracks stock levels, sales velocity, days of cover, and reorder needs. Classifies products into risk levels (critical, high, medium, out_of_stock, overstock, stagnant) and calculates recommended reorder quantities.
- Aliases: Supply Chain Manager

### Marketing Agent
- Definition: Analyzes campaign spend, impressions, clicks, conversions, CTR, conversion rate, cost per conversion, and ROAS. Detects underperforming campaigns via explainable rules and suggests budget reallocation.
- Aliases: Growth Strategist

### Customer Support Agent
- Definition: Analyzes customer feedback with deterministic counting, tracks negative sentiment, recurring issues, and delivery problems. Preserves original customer words verbatim. Uses LLM only for sentiment classification of unclassified tickets.
- Aliases: Customer Experience Lead

### BI Agent
- Definition: Combines the Finance, Inventory, Marketing, and Customer Support findings into one Business Health Score using a documented, deterministic formula. Does not query the database directly — consumes the four domain agents' snapshots.
- Aliases: Business Intelligence Analyst

### Command Center
- Definition: The conversational UI page where the business owner asks questions and the CEO Agent responds with routing decisions, specialist agent findings, health score, root causes, and prioritized action plans. Supports English, Urdu, and Roman Urdu.
- Aliases: CEO Q&A

### Agent Registry
- Definition: Global dictionary (`AGENT_REGISTRY`) that maps agent keys to agent instances. Populated at import time when each agent module calls `register_agent()`. Used by the API layer to list all available agents.
- Aliases: Registry

### Deterministic Fallback
- Definition: Template-based text generation that builds a plain-language interpretation from structured facts when the LLM is unavailable, unconfigured, or fails. Every agent implements `_fallback_interpretation()`. Guarantees the system always produces a valid response.
- Aliases: Fallback interpretation

### Route → Gather → Synthesize
- Definition: The three-step orchestration pattern used by the CEO Agent. (1) Route: keyword rules select which domain agents to consult. (2) Gather: BI snapshot loads all domain findings. (3) Synthesize: fixed rules produce key findings, root causes, and prioritized actions.
- Aliases: CEO orchestration pattern

### Ali Garments
- Definition: The demo business seeded in the database. A Pakistani clothing retailer with products, monthly/daily sales, expenses, marketing campaigns, support tickets, and customers. Used for development, testing, and demonstration.
- Aliases: Demo business
