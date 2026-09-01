"""
BI Agent API endpoints.

Error handling contract:
    - 404: business not found, or no agent data at all (database not
      seeded); a single missing domain does NOT fail the request — its
      weight is re-normalized and a coverage signal is emitted
    - 503: database failure
    - LLM failure never fails the request — the agent falls back to a
      deterministic interpretation of the already-computed score.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.bi import BIAnalysisResponse
from ..agents.base import AGENT_REGISTRY
from ..services.bi import BusinessNotFoundError, NoBIDataError

router = APIRouter()

BI_AGENT_KEY = "bi_agent"


def _get_bi_agent():
    agent = AGENT_REGISTRY.get(BI_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="BI Agent is not registered")
    return agent


@router.get("/bi/analysis", response_model=BIAnalysisResponse)
async def bi_analysis(db: Session = Depends(get_db)):
    agent = _get_bi_agent()

    try:
        return agent.analyze(db)
    except (BusinessNotFoundError, NoBIDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
