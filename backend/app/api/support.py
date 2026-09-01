"""
Customer Support Agent API endpoints.

Error handling contract:
    - 422: invalid analysis window (days out of the allowed range)
    - 404: business not found or no customer feedback (database not seeded)
    - 503: database failure
    - LLM failure never fails the request — the agent falls back to a
      deterministic interpretation and heuristic sentiment.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.support import SupportAnalysisResponse
from ..agents.base import AGENT_REGISTRY
from ..services.support import (
    BusinessNotFoundError,
    InvalidRangeError,
    NoTicketDataError,
)

router = APIRouter()

SUPPORT_AGENT_KEY = "customer_support_agent"


def _get_support_agent():
    agent = AGENT_REGISTRY.get(SUPPORT_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="Customer Support Agent is not registered")
    return agent


@router.get("/support/analysis", response_model=SupportAnalysisResponse)
async def support_analysis(
    days: int = Query(
        default=30,
        ge=7,
        le=90,
        description="Analysis window in days, counting back from the most recent ticket.",
    ),
    db: Session = Depends(get_db),
):
    agent = _get_support_agent()

    try:
        return agent.analyze(db, days=days)
    except InvalidRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (BusinessNotFoundError, NoTicketDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
