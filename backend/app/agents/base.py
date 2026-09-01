from abc import ABC, abstractmethod
from typing import Dict

from ..schemas.agents import AgentInfo


class BaseAgent(ABC):
    """Base class for all AI agents in the NexusAI workforce."""

    name: str = ""
    role: str = ""
    description: str = ""
    icon: str = "sparkles"
    color: str = "blue"
    status: str = "active"

    @abstractmethod
    def tasks(self) -> list[str]:
        """Return the list of tasks this agent handles."""
        ...

    def info(self) -> AgentInfo:
        return AgentInfo(
            name=self.name,
            role=self.role,
            description=self.description,
            status=self.status,
            icon=self.icon,
            color=self.color,
            tasks=self.tasks(),
        )


# Agent registry — populated by importing all agent modules
AGENT_REGISTRY: Dict[str, BaseAgent] = {}


def register_agent(agent: BaseAgent) -> None:
    key = agent.name.lower().replace(" ", "_")
    AGENT_REGISTRY[key] = agent
