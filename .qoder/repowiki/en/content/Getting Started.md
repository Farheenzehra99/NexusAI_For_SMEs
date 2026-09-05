# Getting Started

<cite>
**Referenced Files in This Document**
- [backend/app/main.py](file://backend/app/main.py)
- [backend/requirements.txt](file://backend/requirements.txt)
- [backend/seed.py](file://backend/seed.py)
- [backend/.env.example](file://backend/.env.example)
- [frontend/package.json](file://frontend/package.json)
- [frontend/.env.local](file://frontend/.env.local)
</cite>

## Table of Contents
1. Introduction
2. Prerequisites
3. Backend Setup
4. Frontend Setup
5. Running the Application
6. First Steps After Launch
7. Troubleshooting Guide

## Introduction
NexusAI for SMEs is a full-stack application with a Python FastAPI backend and a Next.js frontend. This guide walks you through setting up both from scratch. No external database is required — the app uses SQLite.

## Prerequisites
- Python 3.11+ installed
- Node.js 18+ and npm installed
- (Optional) Google Gemini API key for LLM narration — the app works fully without it using deterministic fallbacks

## Backend Setup

1. Navigate to the backend directory:
   ```
   cd backend
   ```

2. Create and activate a virtual environment:
   ```
   python -m venv venv
   venv\Scripts\activate       # Windows
   source venv/bin/activate    # Linux/Mac
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file (copy from `.env.example`):
   ```
   DATABASE_URL=sqlite:///./nexusai.db
   ALLOWED_ORIGINS=http://localhost:3000
   GEMINI_API_KEY=your_api_key_here
   GEMINI_MODEL=gemini-3.5-flash-lite
   LLM_TIMEOUT_SECONDS=30
   JWT_SECRET_KEY=your-secret-key
   JWT_ALGORITHM=HS256
   JWT_EXPIRATION_MINUTES=10080
   DEBUG=true
   ```

5. Seed the demo database:
   ```
   python seed.py
   ```
   This creates the SQLite database with "Ali Garments" demo data including products, sales, expenses, campaigns, and support tickets.

6. Start the backend server:
   ```
   uvicorn app.main:app --reload --port 8000
   ```

## Frontend Setup

1. Navigate to the frontend directory:
   ```
   cd frontend
   ```

2. Install dependencies:
   ```
   npm install
   ```

3. Create/update `.env.local`:
   ```
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. Start the development server:
   ```
   npm run dev
   ```
   The app will be available at `http://localhost:3000`.

## Running the Application
1. Start the backend first (port 8000)
2. Start the frontend second (port 3000)
3. Open `http://localhost:3000` in your browser
4. Log in with the demo credentials (check `seed.py` for the default account)

## First Steps After Launch
- **Dashboard**: View the Business Health Score, revenue trend, inventory alerts, and AI recommendations
- **Command Center**: Ask the CEO Agent a question like "Why are my sales declining?" or "meri sales kyun gir rahi hain?"
- **AI Employees**: Meet all six agents and see their activity logs
- **Settings**: Switch between English, Urdu, and Roman Urdu

## Troubleshooting Guide
- **Port 8000 in use**: Kill the existing process or change the port in the uvicorn command
- **Port 3000 in use**: Set a different port with `npm run dev -- -p 3001`
- **Module not found errors**: Ensure virtual environment is activated and dependencies are installed
- **Database errors**: Delete `nexusai.db` and re-run `python seed.py`
- **LLM errors**: The app works without a Gemini API key; all agents use deterministic fallbacks
