"""
Inventory Agent API endpoints.

Error handling contract:
    - 422: invalid velocity window (days outside 7..90)
    - 404: business not found or no sales data (database not seeded)
    - 503: database failure
    - LLM failure never fails the request — the agent falls back to a
      deterministic interpretation.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ..database import get_db
from ..schemas.inventory import InventoryAnalysisResponse
from ..agents.base import AGENT_REGISTRY
from ..services.inventory import (
    InvalidRangeError,
    BusinessNotFoundError,
    NoSalesDataError,
)

from .dependencies import get_current_business
from ..models.business import Business

router = APIRouter()

INVENTORY_AGENT_KEY = "inventory_agent"


def _get_inventory_agent():
    agent = AGENT_REGISTRY.get(INVENTORY_AGENT_KEY)
    if not agent:
        raise HTTPException(status_code=500, detail="Inventory Agent is not registered")
    return agent


@router.get("/inventory/analysis", response_model=InventoryAnalysisResponse)
async def inventory_analysis(
    days: int = Query(30, ge=7, le=90, description="Velocity window in days (7-90)"),
    business: Business = Depends(get_current_business),
    db: Session = Depends(get_db),
):
    agent = _get_inventory_agent()

    try:
        return agent.analyze(db, days=days, business_id=business.id)
    except InvalidRangeError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    except (BusinessNotFoundError, NoSalesDataError) as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except SQLAlchemyError:
        raise HTTPException(status_code=503, detail="Database unavailable. Try again shortly.")
