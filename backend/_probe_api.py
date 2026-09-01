import json
import urllib.request

BASE = "http://127.0.0.1:8000/api"

# 1) New routing endpoint
q = urllib.request.quote("Why are my sales down?")
route = json.load(urllib.request.urlopen(f"{BASE}/ceo/route?question={q}", timeout=30))
print("ROUTE agent:", route["agent"])
print("ROUTE understood_as:", route["understood_as"])
for s in route["routing"]:
    print("  ->", s["domain"], "|", s["agent_name"], "|", s["reason"])
print()

# 2) Fields consumed by the frontend headline extractors
fin = json.load(urllib.request.urlopen(f"{BASE}/finance/analysis", timeout=120))
r = fin["facts"]["revenue"]; p = fin["facts"]["profit"]
print("FINANCE:", r["decline_from_peak_percent"], r["peak_month"], r["trend"], "| margin", p["current_margin_percent"], p["peak_margin_percent"], p["margin_compression_pp"])

inv = json.load(urllib.request.urlopen(f"{BASE}/inventory/analysis", timeout=120))
s = inv["facts"]["summary"]
print("INVENTORY: critical", s["critical_count"], "at_risk", s["at_risk_count"], "products", s["total_active_products"])
print("  risk[0]:", inv["facts"]["risks"][0]["product"], "|", inv["facts"]["risks"][0]["reason"])

mk = json.load(urllib.request.urlopen(f"{BASE}/marketing/analysis", timeout=120))
print("MARKETING: underperforming:", mk["facts"]["underperforming_campaign_names"], "| benchmark conv:", mk["facts"]["benchmark"]["conversion_rate_percent"])
worst = [c for c in mk["facts"]["campaigns"] if c["performance"] == "underperforming"][0]
print("  worst reason:", worst["name"], "|", worst["reason"])

sup = json.load(urllib.request.urlopen(f"{BASE}/support/analysis", timeout=120))
f = sup["facts"]
print("SUPPORT: top_theme:", f["top_theme"], "| delivery:", f["delivery"]["total_tickets"], "of", f["summary"]["total_tickets"], f["delivery"]["share_percent"], "open:", f["delivery"]["open_count"])

bi = json.load(urllib.request.urlopen(f"{BASE}/bi/analysis", timeout=120))
hs = bi["facts"]["health_score"]
print("BI:", hs["score"], hs["risk_level"])
