"""
CEO Agent API endpoints.

Error handling contract:
    - 422: empty/too-short question
    - 404: business not found, or every specialized agent failed
    - 503: database failure
    - A single agent failing NEVER fails the request — the answer is
      flagged incomplete and the remaining agents' results are preserved.
    - LLM failure never fails the request — the agent falls back to a
      deterministic narration of the already-computed plan.

GET /ceo/route is a pure routing decision (no database access): the
Command Center calls it first to show the CEO's real routing while the
specialist agents run.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.ceo import CEOAnalysisResponse, CEORouteResponse, RouteStep
from ..agents.base import AGENT_REGISTRY
from ..services.ceo import (
    AGENT_NAMES,
    BusinessNotFoundError,
    NoBIDataError,
    understand_question,
)

router = APIRouter()

CEO_AGENT_KEY = "ceo_agent"


def _get_ceo_agent():
    agent = AGENT_REGISTRY.get(CEO_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="CEO Agent is not registered")
    return agent


@router.get("/ceo/route", response_model=CEORouteResponse)
async def ceo_route(
    question: str = Query(
        default="Why are my sales down?",
        min_length=3,
        max_length=500,
        description="The owner's business question to route.",
    ),
):
    """The CEO Agent's routing decision — which specialists to consult.

    Pure keyword routing (app/services/ceo.py), no database access, so
    it answers instantly and can never 503.
    """
    routed, understood = understand_question(question)
    return CEORouteResponse(
        agent="CEO Agent",
        question=question,
        understood_as=understood,
        routing=[
            RouteStep(domain=d, agent_name=AGENT_NAMES[d], reason=routed[d])
            for d in routed
        ],
    )


@router.get("/ceo/analysis", response_model=CEOAnalysisResponse)
async def ceo_analysis(
    question: str = Query(
        default="Why are my sales down?",
        min_length=3,
        max_length=500,
        description="The owner's business question for the CEO Agent.",
    ),
    db: Session = Depends(get_db),
):
    agent = _get_ceo_agent()

    try:
        return agent.analyze(db, question=question)
    except (BusinessNotFoundError, NoBIDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
