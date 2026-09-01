"""
Finance Agent API endpoints.

Error handling contract:
    - 422: invalid data range (months outside 1..12)
    - 404: business not found (database not seeded)
    - 503: database failure
    - LLM failure never fails the request — the agent falls back to a
      deterministic interpretation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.finance import FinanceAnalysisResponse
from ..agents.base import AGENT_REGISTRY
from ..services.finance import InvalidRangeError, BusinessNotFoundError

router = APIRouter()

FINANCE_AGENT_KEY = "finance_agent"


def _get_finance_agent():
    agent = AGENT_REGISTRY.get(FINANCE_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="Finance Agent is not registered")
    return agent


@router.get("/finance/analysis", response_model=FinanceAnalysisResponse)
async def finance_analysis(
    months: int = Query(6, ge=1, le=12, description="Number of months to analyze (1-12)"),
    db: Session = Depends(get_db),
):
    agent = _get_finance_agent()

    try:
        return agent.analyze(db, months=months)
    except InvalidRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except BusinessNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
