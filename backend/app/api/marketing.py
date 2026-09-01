"""
Marketing Agent API endpoints.

Error handling contract:
    - 404: business not found or no campaign data (database not seeded)
    - 503: database failure
    - LLM failure never fails the request — the agent falls back to a
      deterministic interpretation.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.marketing import MarketingAnalysisResponse
from ..agents.base import AGENT_REGISTRY
from ..services.marketing import BusinessNotFoundError, NoCampaignDataError

router = APIRouter()

MARKETING_AGENT_KEY = "marketing_agent"


def _get_marketing_agent():
    agent = AGENT_REGISTRY.get(MARKETING_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="Marketing Agent is not registered")
    return agent


@router.get("/marketing/analysis", response_model=MarketingAnalysisResponse)
async def marketing_analysis(db: Session = Depends(get_db)):
    agent = _get_marketing_agent()

    try:
        return agent.analyze(db)
    except (BusinessNotFoundError, NoCampaignDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
