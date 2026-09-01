from fastapi import APIRouter

from ..schemas.agents import AgentInfo, AgentListResponse
from ..agents.base import AGENT_REGISTRY

router = APIRouter()


@router.get("/agents", response_model=AgentListResponse)
async def list_agents():
    agents = [agent.info() for agent in AGENT_REGISTRY.values()]
    active_count = sum(1 for a in agents if a.status == "active")
    return AgentListResponse(agents=agents, total_active=active_count)


@router.get("/agents/{agent_name}")
async def get_agent(agent_name: str):
    agent = AGENT_REGISTRY.get(agent_name)
    if not agent:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Agent '{agent_name}' not found")
    return agent.info()
