from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .database import engine, Base
from .api import health, dashboard, data, finance, inventory, marketing, support, bi, ceo, notifications, settings as settings_api
from .api.agents import router as agents_router

# Import agents to trigger registration
from . import agents as agent_modules  # noqa: F401

app = FastAPI(
    title="NexusAI API",
    description="AI Workforce platform for Pakistani SMEs",
    version="0.1.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create tables on startup
@app.on_event("startup")
async def startup():
    Base.metadata.create_all(bind=engine)

# Routes
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(dashboard.router, prefix="/api", tags=["dashboard"])
app.include_router(agents_router, prefix="/api", tags=["agents"])
app.include_router(data.router, prefix="/api", tags=["data"])
app.include_router(finance.router, prefix="/api", tags=["finance"])
app.include_router(inventory.router, prefix="/api", tags=["inventory"])
app.include_router(marketing.router, prefix="/api", tags=["marketing"])
app.include_router(support.router, prefix="/api", tags=["support"])
app.include_router(bi.router, prefix="/api", tags=["bi"])
app.include_router(ceo.router, prefix="/api", tags=["ceo"])
app.include_router(notifications.router, prefix="/api", tags=["notifications"])
app.include_router(settings_api.router, prefix="/api", tags=["settings"])

@app.get("/")
async def root():
    return {"message": "NexusAI API", "docs": "/docs"}
