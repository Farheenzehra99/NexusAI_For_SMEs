"""
Safe LLM interpreter.

The LLM's ONLY job is to explain already-computed facts in plain language.
It is explicitly instructed never to calculate or invent numbers, and every
failure mode (missing key, network error, timeout, quota exhaustion, bad
response) degrades gracefully to None, so callers fall back to a
deterministic template written by code.

Uses the Google Gemini API (gemini-3.5-flash-lite by default) through only
the Python standard library (urllib) — no extra dependency. The API key
is sent in the x-goog-api-key header, never in a URL, so it cannot leak
into logs or error messages.
"""

import json
import urllib.request
import urllib.error
from typing import Optional

from ..config import settings
from ..schemas.finance import FinanceFacts
from ..schemas.inventory import InventoryFacts
from ..schemas.marketing import MarketingFacts
from ..schemas.support import SupportFacts
from ..schemas.bi import BIFacts
from ..schemas.ceo import CEOAnalysisResponse

_SHARED_RULES = (
    "STRICT RULES: Use ONLY the numbers given in the facts. Never calculate "
    "new numbers, never estimate, never invent figures. If a number is not "
    "in the facts, do not mention it."
)

FINANCE_SYSTEM_PROMPT = (
    "You are the Finance Agent for a small Pakistani clothing retailer. "
    "You will receive a JSON object of financial facts that were computed "
    "by deterministic business logic. Your job is ONLY to explain those "
    "facts in clear, simple language for the shop owner. "
    + _SHARED_RULES
    + " Keep the explanation under 150 words, in 2-3 short paragraphs. "
    "Use Rs for amounts. Be direct and honest about problems, and end with "
    "the single most important action to take."
)

INVENTORY_SYSTEM_PROMPT = (
    "You are the Inventory Agent for a small Pakistani clothing retailer. "
    "You will receive a JSON object of inventory facts (stock levels, sales "
    "velocity, days of cover, risks, reorder quantities) that were computed "
    "by deterministic business logic. Your job is ONLY to explain those "
    "facts in clear, simple language for the shop owner. "
    + _SHARED_RULES
    + " Keep the explanation under 150 words, in 2-3 short paragraphs. "
    "Use Rs for amounts. Prioritise stock-out risks first, then overstock. "
    "End with the single most important action to take."
)

MARKETING_SYSTEM_PROMPT = (
    "You are the Marketing Agent for a small Pakistani clothing retailer. "
    "You will receive a JSON object of marketing facts (campaign spend, "
    "impressions, clicks, conversions, conversion rates, cost per "
    "conversion, ROAS, underperformance flags, reallocation suggestions) "
    "that were computed by deterministic business logic. Your job is ONLY "
    "to explain those facts in clear, simple language for the shop owner "
    "and suggest actions based on them. "
    + _SHARED_RULES
    + " Keep the explanation under 150 words, in 2-3 short paragraphs. "
    "Use Rs for amounts. Prioritise underperforming campaigns, then "
    "opportunities. End with the single most important action to take."
)

SUPPORT_SYSTEM_PROMPT = (
    "You are the Customer Support Agent for a small Pakistani clothing "
    "retailer. You will receive a JSON object of support facts (negative "
    "feedback percentage, recurring issue themes, delivery problems, "
    "product complaints, verbatim customer quotes) that were computed by "
    "deterministic business logic. Your job is ONLY to explain those facts "
    "in clear, simple language for the shop owner and suggest actions "
    "based on them. "
    + _SHARED_RULES
    + " You may quote a customer's words ONLY if they appear verbatim in "
    "the provided quotes. Never write new customer feedback. Keep the "
    "explanation under 150 words, in 2-3 short paragraphs. Prioritise "
    "delivery problems, then recurring issues. End with the single most "
    "important action to take."
)

# Classifier prompt: strict single-word labels, no free text.
_SENTIMENT_SYSTEM_PROMPT = (
    "You classify customer support messages by sentiment. Reply with ONLY "
    "a JSON array of labels, one per message, in the same order. Each "
    "label must be exactly one of: positive, neutral, negative. "
    "Output nothing else — no explanations."
)

BI_SYSTEM_PROMPT = (
    "You are the BI (Business Intelligence) Agent for a small Pakistani "
    "clothing retailer. You will receive a JSON object containing a "
    "Business Health Score (0-100), its risk level, the per-domain "
    "sub-scores with their documented deduction rules, key business "
    "signals, and the underlying findings from the Finance, Inventory, "
    "Marketing, and Customer Support agents. Everything was computed by "
    "deterministic, documented business logic. Your job is ONLY to "
    "explain the already-computed score and findings in clear, simple "
    "language for the shop owner. "
    + _SHARED_RULES
    + " NEVER recompute, adjust, second-guess, or estimate the score — "
    "state it exactly as given. Keep the explanation under 150 words, in "
    "2-3 short paragraphs. Start with the score and risk level, then the "
    "biggest drivers. End with the single most important action to take."
)

CEO_SYSTEM_PROMPT = (
    "You are the CEO Agent for a small Pakistani clothing retailer — the "
    "orchestrator of an AI workforce. You will receive a JSON object "
    "containing the owner's question and the ALREADY-COMPUTED answer: a "
    "Business Health Score with risk level, key findings, root causes, "
    "and a prioritized action plan with evidence, all produced by "
    "deterministic business logic over the specialized agents' findings. "
    "Your job is ONLY to present this finished plan to the owner in "
    "clear, simple, direct language — like a trusted business advisor "
    "summarizing the team's work. "
    + _SHARED_RULES
    + " NEVER recompute the score, invent findings, add actions, or "
    "change priorities — present exactly what is given, in the given "
    "order. If the analysis is incomplete, say so. Keep the answer under "
    "180 words: first answer the question directly (the main causes), "
    "then the health score and risk level, then the top actions in "
    "priority order. Use Rs for amounts. "
    "LANGUAGE RULE: You MUST reply in the SAME language and script as "
    "the owner's question. If the question is in Urdu script (e.g. "
    "میری سیلز کیوں گر رہی ہے), answer in clear Urdu script. If the "
    "question is in Roman Urdu (e.g. meri sales kyun gir rahi hain), "
    "answer in Roman Urdu. If in English, answer in English. Keep the "
    "same numbers, Rs amounts, and priorities — only the language "
    "changes."
)


def is_llm_configured() -> bool:
    """True when a Gemini API key is configured."""
    return bool((settings.gemini_api_key or "").strip())


_GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


def _chat(system_prompt: str, user_content: str) -> Optional[str]:
    """Call the Gemini generateContent API. Returns None on ANY failure."""
    if not is_llm_configured():
        return None

    payload = json.dumps({
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "contents": [
            {"role": "user", "parts": [{"text": user_content}]},
        ],
        "generationConfig": {
            "temperature": 0.2,
            # Generous budget: thinking models can spend many tokens on
            # internal reasoning before writing the answer — 1000 could
            # truncate the visible text.
            "maxOutputTokens": 2048,
        },
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{_GEMINI_BASE_URL}/{settings.gemini_model}:generateContent",
        data=payload,
        headers={
            "Content-Type": "application/json",
            # Header auth (not a query param) so the key never appears in
            # URLs, logs, or raised error messages.
            "x-goog-api-key": settings.gemini_api_key,
        },
        method="POST",
    )

    try:
        with urllib.request.urlopen(
            request, timeout=settings.llm_timeout_seconds
        ) as response:
            body = json.loads(response.read().decode("utf-8"))

        if not isinstance(body, dict):
            return None
        # Safety-blocked generations degrade to None.
        if body.get("promptFeedback", {}).get("blockReason"):
            return None
        candidates = body.get("candidates") or []
        if not candidates:
            return None
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(part.get("text", "") for part in parts).strip()
        return text if text else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError,
            KeyError, IndexError, ValueError, json.JSONDecodeError, OSError,
            AttributeError, TypeError):
        # Any LLM failure → caller falls back to the deterministic template.
        return None


def interpret_finance_facts(facts: FinanceFacts) -> Optional[str]:
    """Ask the LLM to explain the given finance facts. None on any failure."""
    return _chat(
        FINANCE_SYSTEM_PROMPT,
        "Explain these financial facts for the business owner. "
        "Facts (computed by code, verified):\n"
        + facts.model_dump_json(indent=2),
    )


def interpret_inventory_facts(facts: InventoryFacts) -> Optional[str]:
    """Ask the LLM to explain the given inventory facts. None on any failure."""
    return _chat(
        INVENTORY_SYSTEM_PROMPT,
        "Explain these inventory facts for the business owner. "
        "Facts (computed by code, verified):\n"
        + facts.model_dump_json(indent=2),
    )


def interpret_marketing_facts(facts: MarketingFacts) -> Optional[str]:
    """Ask the LLM to explain the given marketing facts. None on any failure."""
    return _chat(
        MARKETING_SYSTEM_PROMPT,
        "Explain these marketing facts for the business owner and suggest "
        "actions grounded only in these numbers. "
        "Facts (computed by code, verified):\n"
        + facts.model_dump_json(indent=2),
    )


def interpret_support_facts(facts: SupportFacts) -> Optional[str]:
    """Ask the LLM to explain the given support facts. None on any failure."""
    return _chat(
        SUPPORT_SYSTEM_PROMPT,
        "Explain these customer support facts for the business owner and "
        "suggest actions grounded only in these numbers. "
        "Facts (computed by code, verified):\n"
        + facts.model_dump_json(indent=2),
    )


def interpret_bi_facts(facts: BIFacts) -> Optional[str]:
    """Ask the LLM to explain the already-computed health score.

    The score itself is NEVER computed by the LLM — it arrives fully
    computed in ``facts`` and the prompt forbids recomputing it.
    None on any failure.
    """
    return _chat(
        BI_SYSTEM_PROMPT,
        "Explain this Business Health Score and the findings behind it "
        "for the business owner. The score is final — do not recompute "
        "it. Facts (computed by code, verified):\n"
        + facts.model_dump_json(indent=2),
    )


def interpret_ceo_answer(response: CEOAnalysisResponse) -> Optional[str]:
    """Ask the LLM to narrate the already-computed CEO action plan.

    The plan, priorities, and evidence are final — the prompt forbids
    inventing findings or actions. The LLM also replies in the same
    language and script as the owner's question (Urdu script, Roman
    Urdu, or English) so the narration is readable to the shop owner.
    None on any failure.
    """
    return _chat(
        CEO_SYSTEM_PROMPT,
        "Answer the owner's question using ONLY this finished, verified "
        "plan. Do not recompute, add, or reorder anything. Reply in the "
        "same language and script as the owner's question below. "
        f"The owner asked: {response.question}\n"
        "Plan (computed by code, verified):\n"
        + response.model_dump_json(indent=2),
    )


def classify_sentiments(messages: list[str]) -> Optional[list[str]]:
    """Classify a batch of customer messages by sentiment.

    Returns a list of "positive" | "neutral" | "negative" labels in the
    same order as ``messages``, or None on ANY failure (not configured,
    network error, timeout, quota, malformed or mis-sized response, or
    unknown labels). Callers must fall back to a heuristic when None.
    """
    if not messages:
        return []

    valid = {"positive", "neutral", "negative"}
    raw = _chat(
        _SENTIMENT_SYSTEM_PROMPT,
        "Classify these "
        + str(len(messages))
        + " customer messages:\n"
        + json.dumps(messages, ensure_ascii=False, indent=2),
    )
    if raw is None:
        return None

    # The model may wrap the array in a markdown fence; strip it.
    text = raw.strip()
    if text.startswith("```"):
        text = text.strip("`")
        # Drop an optional "json" language hint on the first line.
        if text.lower().startswith("json"):
            text = text[4:]
        text = text.strip()

    try:
        labels = json.loads(text)
    except (ValueError, json.JSONDecodeError):
        return None

    if (
        not isinstance(labels, list)
        or len(labels) != len(messages)
        or not all(isinstance(label, str) for label in labels)
        or not all(label.strip().lower() in valid for label in labels)
    ):
        return None

    return [label.strip().lower() for label in labels]
