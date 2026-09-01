"""Full clean-start E2E verification of the NexusAI demo scenario.

Hits every backend endpoint the frontend uses, checks the deterministic
business numbers, and proves the live Gemini integration works
(interpretation_source == "llm") on every agent.
"""
import json
import time
import urllib.parse
import urllib.request

BASE = "http://127.0.0.1:8000"
ok_count = 0
fail_count = 0


def check(label, condition, detail=""):
    global ok_count, fail_count
    if condition:
        ok_count += 1
        print(f"  [OK] {label}")
    else:
        fail_count += 1
        print(f"  [FAIL] {label} {('-- ' + str(detail)) if detail else ''}")


def get(path, timeout=60):
    with urllib.request.urlopen(BASE + path, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def post(path, body, timeout=180):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


print("=== 1. Health ===")
health = get("/api/health")
check("status healthy", health.get("status") == "healthy", health)
check("database connected", health.get("database") == "connected", health)

print("=== 2. Dashboard ===")
dash = get("/api/dashboard")
check("business = Ali Garments", dash.get("business_name") == "Ali Garments",
      dash.get("business_name"))
check("location = Hyderabad", "Hyderabad" in (dash.get("location") or ""),
      dash.get("location"))
recs = dash.get("recommendations", [])
check("5 AI recommendations", len(recs) == 5, len(recs))
check("recommendations have priority",
      all(r.get("priority") for r in recs), "missing priority")
check("recommendations cite evidence",
      all(r.get("evidence") for r in recs), "missing evidence")
check("recommendations attributed to agents",
      all(r.get("agent") for r in recs), "missing agent")

print("=== 3. Agents registry ===")
agents_resp = get("/api/agents")
agents = agents_resp.get("agents") or []
check("6 agents registered", len(agents) == 6, len(agents))
names = {a["name"] for a in agents}
expected = {"CEO Agent", "Finance Agent", "Inventory Agent",
            "Marketing Agent", "Customer Support Agent", "BI Agent"}
check("all expected agents present", names == expected, names ^ expected)
check("all agents active", agents_resp.get("total_active") == 6,
      agents_resp.get("total_active"))
check("agents carry theme colors",
      all(a.get("color") for a in agents), "missing color")

print("=== 4. Finance agent (live Gemini) ===")
fin = get("/api/finance/analysis")
check("finance interpretation from LLM",
      fin.get("interpretation_source") == "llm", fin.get("interpretation_source"))
check("interpretation non-trivial",
      len(fin.get("interpretation") or "") > 30, "too short")
changes = (fin.get("facts") or {}).get("unusual_changes") or []
check("revenue decline detected in code",
      len(changes) > 0, changes)

print("=== 5. Inventory agent (live Gemini) ===")
inv = get("/api/inventory/analysis")
check("inventory interpretation from LLM",
      inv.get("interpretation_source") == "llm", inv.get("interpretation_source"))
risks = (inv.get("facts") or {}).get("risks") or []
check("stock-out risks computed in code", len(risks) > 0, risks)

print("=== 6. Marketing agent (live Gemini) ===")
mkt = get("/api/marketing/analysis")
check("marketing interpretation from LLM",
      mkt.get("interpretation_source") == "llm", mkt.get("interpretation_source"))
under = (mkt.get("facts") or {}).get("underperforming_campaign_names") or []
check("underperforming campaigns flagged in code",
      len(under) > 0, under)

print("=== 7. Support agent (live Gemini) ===")
sup = get("/api/support/analysis")
check("support interpretation from LLM",
      sup.get("interpretation_source") == "llm", sup.get("interpretation_source"))
summary = (sup.get("facts") or {}).get("summary") or {}
check("negative feedback computed in code",
      (summary.get("negative_feedback_percent") or 0) > 50,
      summary.get("negative_feedback_percent"))

print("=== 8. BI agent (live Gemini) ===")
bi = get("/api/bi/analysis")
score = (bi.get("facts") or {}).get("health_score") or {}
check("health score = 75/100", score.get("score") == 75, score.get("score"))
check("risk level = moderate", score.get("risk_level") == "moderate", score.get("risk_level"))
check("BI interpretation from LLM",
      bi.get("interpretation_source") == "llm", bi.get("interpretation_source"))
check("per-domain sub-scores present",
      isinstance(score.get("domain_scores"), list) and len(score["domain_scores"]) == 4,
      score.get("domain_scores"))

print("=== 9. CEO routing ===")
route = get("/api/ceo/route?question="
           + urllib.parse.quote("Why are my sales going down?"))
routing = route.get("routing") or []
domains = [r.get("domain") for r in routing]
check("routes to 4 specialists", len(routing) == 4, domains)
check("finance routed first", bool(routing) and routing[0].get("domain") == "finance",
      domains)
check("understands the question",
      bool(route.get("understood_as")), route.get("understood_as"))

print("=== 10. CEO orchestration — full demo question ===")
t0 = time.time()
ceo = get("/api/ceo/analysis?question="
          + urllib.parse.quote("Why are my sales going down?"), timeout=240)
elapsed = time.time() - t0
answer = ceo.get("answer", {})
hs = answer.get("health_score", {})
check("CEO answers with health score 75", hs.get("score") == 75, hs.get("score"))
check("root causes grounded in agent data",
      len(answer.get("root_causes", [])) >= 3, answer.get("root_causes"))
check("5 prioritized actions",
      len(answer.get("recommended_actions", [])) == 5,
      len(answer.get("recommended_actions") or []))
acts = answer.get("recommended_actions", [])
check("actions carry priority + evidence",
      all(a.get("priority") and a.get("evidence") for a in acts), "missing fields")
check("CEO interpretation from LLM",
      ceo.get("interpretation_source") == "llm", ceo.get("interpretation_source"))
print(f"  (CEO orchestration took {elapsed:.1f}s end-to-end)")

print("=== 11. Collaboration activity log ===")
acts_resp = get("/api/agent-activities")
if isinstance(acts_resp, dict):
    acts_log = acts_resp.get("activities") or []
else:
    acts_log = acts_resp
check("collaboration activities recorded", len(acts_log) > 0, len(acts_log))
recent = acts_log[0] if acts_log else {}
check("activities carry agent attribution",
      bool(recent.get("agent_name")), recent)

print()
print(f"{'=' * 50}")
print(f"E2E RESULTS: {ok_count} passed, {fail_count} failed")
print(f"{'=' * 50}")
raise SystemExit(1 if fail_count else 0)
