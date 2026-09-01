from pydantic import BaseModel
from typing import List


class AgentInfo(BaseModel):
    name: str
    role: str
    description: str
    status: str
    icon: str
    color: str
    tasks: List[str]


class AgentListResponse(BaseModel):
    agents: List[AgentInfo]
    total_active: int
