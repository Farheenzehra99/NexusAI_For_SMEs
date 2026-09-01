"""Pydantic schemas for the CEO Agent (orchestration layer).

The CEO Agent answers the owner's business questions by routing the
question to the right specialized agents, combining their ALREADY-COMPUTED
findings (via the BI snapshot), and producing a prioritized action plan.

Design rules:
    - Every number in the answer comes verbatim from the structured
      outputs of the Finance, Inventory, Marketing, Customer Support, and
      BI agents. The CEO never queries raw tables and never invents
      business facts.
    - Root causes, findings, actions, and priorities are produced by
      deterministic, documented rules (app/services/ceo.py).
    - The LLM only narrates the already-computed plan; it never
      recalculates or invents actions or evidence.
    - Partial failures degrade gracefully: available agents' results are
      preserved and the answer is flagged incomplete.
"""

from typing import List, Optional

from pydantic import BaseModel

from .bi import HealthScore


class RoutingDecision(BaseModel):
    """Why one specialized agent was (or was not) consulted."""

    domain: str          # finance|inventory|marketing|support
    agent_name: str      # display name, e.g. "Finance Agent"
    reason: str          # deterministic routing reason
    consulted: bool      # False when the agent's data was unavailable


class RouteStep(BaseModel):
    """One specialist the CEO Agent decided to consult, and why.

    Emitted by GET /api/ceo/route BEFORE any data is loaded, so the
    Command Center can show the routing decision while the specialists
    run. ``consulted`` is unknown at this stage (it lives on
    RoutingDecision in the final answer).
    """

    domain: str          # finance|inventory|marketing|support
    agent_name: str
    reason: str


class CEORouteResponse(BaseModel):
    """The CEO Agent's routing decision for a question (no data loaded)."""

    agent: str
    question: str
    understood_as: str                 # plain-language restatement
    routing: List[RouteStep]


class KeyFinding(BaseModel):
    """One salient computed fact from a consulted agent."""

    domain: str
    agent_name: str
    statement: str       # quotes exact computed numbers
    severity: str        # negative|positive|neutral


class RootCause(BaseModel):
    """A verified driver of the problem the owner asked about."""

    title: str
    statement: str
    contributing_domains: List[str]
    evidence: List[str]  # exact numbers from the agents' structured output


class RecommendedAction(BaseModel):
    """One prioritized, grounded business action."""

    priority: str        # urgent|high|medium|low
    title: str
    description: str
    domain: str          # originating agent's domain
    agent_name: str
    evidence: List[str]  # exact numbers backing the action
    expected_impact: str


class CEOAnswer(BaseModel):
    """The complete grounded answer to the owner's question."""

    question: str
    understood_as: str                 # plain-language restatement
    routing: List[RoutingDecision]
    consulted_agents: List[str]        # display names that contributed
    missing_agents: List[str]          # display names that could not contribute
    incomplete_analysis: bool
    incomplete_reason: Optional[str] = None
    health_score: Optional[HealthScore] = None
    key_findings: List[KeyFinding]
    root_causes: List[RootCause]
    recommended_actions: List[RecommendedAction]   # sorted by priority


class CEOAnalysisResponse(BaseModel):
    """Full CEO Agent response: grounded answer + plain-language
    narrative (LLM or deterministic fallback)."""

    agent: str
    question: str
    answer: CEOAnswer
    interpretation: str
    interpretation_source: str      # "llm" | "fallback"
    generated_at: str
