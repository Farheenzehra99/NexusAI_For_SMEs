# NexusAI for SMEs

AI workforce platform for Pakistani small and medium-sized retail businesses.

## Architecture

```
NexusAI_for_SMEs/
├── backend/          # FastAPI + SQLAlchemy + SQLite
│   ├── app/
│   │   ├── api/      # REST endpoints (health, dashboard, agents)
│   │   ├── agents/   # Modular AI agent stubs
│   │   ├── models/   # SQLAlchemy ORM models
│   │   ├── schemas/  # Pydantic response schemas
│   │   ├── config.py # Environment-based settings
│   │   ├── database.py
│   │   └── main.py
│   ├── seed.py       # Database seeder (Ali Garments demo data)
│   ├── .env          # Environment variables (copy from .env.example)
│   └── requirements.txt
├── frontend/         # Next.js 14 + Tailwind CSS
│   ├── app/          # Pages (Dashboard, Command Center, AI Employees)
│   ├── components/   # Shared components (Sidebar)
│   ├── lib/          # API client and types
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

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `sqlite:///./nexusai.db` | SQLAlchemy connection string |
| `ALLOWED_ORIGINS` | `http://localhost:3000` | CORS origins (comma-separated) |
| `GEMINI_API_KEY` | *(empty)* | Google Gemini API key — powers agent narration and sentiment classification |
| `GEMINI_MODEL` | `gemini-3.6-flash` | Gemini model for all LLM calls |
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

## Current Stage

This is the **foundation build**. The following are working:

- Next.js frontend with 3 pages (Dashboard, Command Center, AI Employees)
- FastAPI backend with REST API
- SQLite database with seeded Ali Garments data
- Six AI agents (Finance, Inventory, Marketing, Support, BI, CEO orchestrator)
  with deterministic calculations and Gemini narration
- Frontend-backend communication via API proxy
- Environment variable configuration

**Status:** Feature-complete. Deterministic business logic in code (finance,
inventory, marketing, support, BI health scoring), CEO orchestration across
agents, and Gemini-powered narration with deterministic fallbacks when the
LLM is unavailable. See `backend/.env.example` for required variables.
