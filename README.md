# NexusAI for SMEs

AI workforce platform for Pakistani small and medium-sized retail businesses.

**Demo business: Ali Garments** — a mid-size clothing retailer in Lahore. One owner + six AI agents = actionable business intelligence.

> **No API key required to run.** All numbers (Health Score, revenue trends,
> stockouts, recommendations) are computed deterministically in Python.
> The Gemini API key only adds LLM narration on top — without it, the app
> falls back to built-in interpretations and every feature still works.

## Quick Start

```bash
# Terminal 1 — backend
cd backend
python -m venv venv
venv\Scripts\activate        # Windows (source venv/bin/activate on Linux/Mac)
pip install -r requirements.txt
python seed.py                # seeds Ali Garments demo data
uvicorn app.main:app --reload --port 8000

# Terminal 2 — frontend
cd frontend
npm install
npm run dev                  # opens at http://localhost:3000
```

Optional: copy `backend/.env.example` to `backend/.env` and add a
`GEMINI_API_KEY` for richer AI narration. The app runs fine without it.

## Architecture

```
NexusAI_for_SMEs/
├── backend/          # FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/      # REST endpoints (dashboard, agents, CEO, BI, domains)
│   │   ├── agents/   # Six modular AI agents (CEO, Finance, Inventory, Marketing, Support, BI)
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic response schemas
│   │   ├── services/ # Deterministic calculations + Gemini client
│   │   ├── config.py # Environment-based settings
│   │   ├── database.py
│   │   └── main.py
│   ├── tests/        # 244+ pytest tests
│   ├── seed.py       # Database seeder (Ali Garments demo data)
│   ├── .env          # Environment variables (copy from .env.example)
│   └── requirements.txt
├── frontend/         # Next.js 14 + Tailwind CSS
│   ├── app/          # Pages (Dashboard, Command Center, AI Employees, Notifications, Settings)
│   ├── components/   # Shared components (Sidebar)
│   ├── lib/          # API client and types
│   ├── locales/      # English, Urdu, Roman Urdu translations
│   └── .env.local
├── docs/             # Project specification
└── _prototype/       # Original clickable prototype (Vite + React)
```

## Prerequisites

- **Python 3.11+** (tested on 3.13)
- **Node.js 18+** (tested on 20.11)
- **npm 9+**

## Setup

### 1. Backend

```bash
cd backend

# Create virtual environment (recommended)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Optional: configure environment (defaults work out of the box)
# copy .env.example .env     # add GEMINI_API_KEY for LLM narration

# Seed the database with Ali Garments demo data
python seed.py

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`.  
Interactive docs at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

The app will be available at `http://localhost:3000`.

### 3. Verify

1. Backend health check: `http://localhost:8000/api/health`
2. Dashboard API: `http://localhost:8000/api/dashboard`
3. Agents API: `http://localhost:8000/api/agents`
4. Open `http://localhost:3000` in your browser

### 4. Run the tests (optional)

```bash
cd backend
python -m pytest tests/ -q
```

244+ tests cover Health Score math, agent routing, the full CEO demo
scenario, partial-failure behavior, and LLM fallbacks.

## Demo Walkthrough (2 minutes)

1. **Dashboard** (`http://localhost:3000`) — Health Score gauge (75/100,
   moderate), KPI cards, revenue/profit trend, inventory alerts, AI
   recommendations, live workforce activity.
2. Click **"Ask the CEO Agent"** → opens the **AI Command Center**.
3. Type or click the suggested question: **"Why are my sales going down?"**
4. Watch the flow: CEO routes the question → Finance, Inventory, Marketing,
   and Support agents analyze in parallel → BI synthesizes → CEO delivers a
   prioritized action plan (4 root causes, 5 evidence-backed actions such as
   an urgent 66-unit reorder and a Rs 30,000 ad reallocation).
5. **AI Employees** page — meet all six agents and their responsibilities.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./nexusai.db` | SQLAlchemy connection string |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key — powers agent narration and sentiment classification |
| `GEMINI_MODEL` | `gemini-3.5-flash-lite` | Gemini model for all LLM calls (lite tier = higher free quota) |
| `DEBUG` | `true` | Enable debug logging |

### Frontend (`frontend/.env.local`)

| Variable | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Health check |
| GET | `/api/dashboard` | Full dashboard data |
| GET | `/api/agents` | List all AI agents |
| GET | `/api/agents/{name}` | Get specific agent details |
| GET | `/api/ceo/analysis?question=...` | CEO orchestration — routes the question, gathers agent findings, returns root causes + prioritized action plan |
| GET | `/api/ceo/route?question=...` | Show which agents the CEO would involve for a question |
| GET | `/api/bi/analysis` | Business Health Score (Finance 35% / Inventory 25% / Marketing 20% / Support 20%) |
| GET | `/api/finance/analysis?months=6` | Financial analysis (revenue, margins, expenses) |
| GET | `/api/inventory/analysis?days=30` | Inventory analysis (stockouts, overstock, reorder quantities) |
| GET | `/api/marketing/analysis` | Marketing analysis (campaign ROI, channel performance) |
| GET | `/api/support/analysis?days=30` | Customer support analysis (complaints, sentiment, delivery issues) |
| GET | `/api/notifications` | Notification list (SSE stream at `/api/notifications/stream`) |
| GET | `/api/expenses`, `/api/daily-sales`, `/api/customers`, `/api/campaigns`, `/api/support-tickets`, `/api/agent-activities` | Raw business data |

Interactive docs: `http://localhost:8000/docs`

## What's Built

Feature-complete MVP:

- Next.js frontend — Dashboard, AI Command Center, AI Employees, Notifications, Settings (English + Urdu)
- FastAPI backend — REST API with validation, CORS, SSE notifications, auth
- SQLite database with seeded Ali Garments data (coherent demo story: revenue
  decline, bestseller stockout, underperforming campaign, delivery complaints)
- Six AI agents (CEO, Finance, Inventory, Marketing, Support, BI):
  deterministic calculations in code, Gemini narration with fallbacks,
  partial-failure resilience (weights re-normalize if an agent fails)
- 244+ passing tests with exact-value assertions against seed data

**Architecture principle:** the LLM never computes numbers. Every metric,
score, and recommendation comes from auditable Python code; the LLM only
narrates pre-computed facts — and is optional.
