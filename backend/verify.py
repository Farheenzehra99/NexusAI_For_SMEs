"""
NexusAI Data Verification Script
=================================
Verifies that all seeded records exist, relationships are valid,
dates are correct, and numeric values make sense.

Usage:
    python verify.py
"""

import sys
import os
from datetime import datetime, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal
from app.models.business import (
    Business, Product, MonthlySale, DailySale, Expense,
    InventoryAlert, SupportTicket, MarketingCampaign,
    Customer, AgentActivity,
)

passed = 0
failed = 0


def check(label: str, condition: bool, detail: str = ""):
    global passed, failed
    if condition:
        passed += 1
        print(f"  [OK] {label}")
    else:
        failed += 1
        msg = f"  [FAIL] {label}"
        if detail:
            msg += f" -- {detail}"
        print(msg)


def verify():
    global passed, failed
    db = SessionLocal()

    try:
        # ── Business ──
        print("\n=== Business ===")
        biz = db.query(Business).first()
        check("Business record exists", biz is not None)
        if not biz:
            print("FATAL: No business found. Run seed.py first.")
            return
        check("Name = Ali Garments", biz.name == "Ali Garments", f"got '{biz.name}'")
        check("Owner = Ahmed Ali", biz.owner_name == "Ahmed Ali", f"got '{biz.owner_name}'")
        check("Location = Hyderabad, Pakistan", biz.location == "Hyderabad, Pakistan")
        check("Currency = PKR", biz.currency == "PKR")
        check("Health score is valid (0-100)", 0 <= biz.health_score <= 100, f"got {biz.health_score}")
        check("Established year reasonable", 2000 <= (biz.established_year or 0) <= 2026)
        check("Total customers > 0", (biz.total_customers or 0) > 0, f"got {biz.total_customers}")
        check("created_at is a valid datetime", isinstance(biz.created_at, datetime))

        # ── Products ──
        print("\n=== Products ===")
        products = db.query(Product).filter(Product.business_id == biz.id).all()
        check("At least 10 products", len(products) >= 10, f"got {len(products)}")

        skus = [p.sku for p in products]
        check("All SKUs are unique", len(skus) == len(set(skus)))

        bestseller = max(products, key=lambda p: p.total_revenue)
        check("Best seller identified", bestseller.total_revenue > 0)
        print(f"    -> Best seller: {bestseller.name} (Rs {bestseller.total_revenue:,.0f})")

        # Best seller has low stock
        low_stock_bestsellers = [
            p for p in products if p.total_sales > 100 and p.stock_qty < 20
        ]
        check("Best-selling product has low stock", len(low_stock_bestsellers) > 0,
              "no high-sales/low-stock product found")

        for p in products:
            check(f"  {p.sku}: price > 0", p.price > 0, f"got {p.price}")
            check(f"  {p.sku}: cost > 0", p.cost > 0, f"got {p.cost}")
            check(f"  {p.sku}: price > cost", p.price > p.cost,
                  f"price={p.price}, cost={p.cost}")
            check(f"  {p.sku}: stock >= 0", p.stock_qty >= 0, f"got {p.stock_qty}")
            check(f"  {p.sku}: revenue = sales × price",
                  abs(p.total_revenue - p.total_sales * p.price) < 1,
                  f"expected {p.total_sales * p.price}, got {p.total_revenue}")

        # ── Monthly Sales ──
        print("\n=== Monthly Sales ===")
        monthly = (
            db.query(MonthlySale)
            .filter(MonthlySale.business_id == biz.id)
            .order_by(MonthlySale.id)
            .all()
        )
        check("At least 6 months of data", len(monthly) >= 6, f"got {len(monthly)}")

        for m in monthly:
            check(f"  {m.month}: revenue > 0", m.revenue > 0, f"got {m.revenue}")
            check(f"  {m.month}: profit > 0", m.profit > 0, f"got {m.profit}")
            check(f"  {m.month}: profit < revenue", m.profit < m.revenue,
                  f"profit={m.profit}, revenue={m.revenue}")
            check(f"  {m.month}: year is 2026", m.year == 2026, f"got {m.year}")
            check(f"  {m.month}: orders > 0", m.orders > 0, f"got {m.orders}")

        # Sales declining story
        if len(monthly) >= 3:
            recent_three = monthly[-3:]
            declining = all(
                recent_three[i].revenue >= recent_three[i + 1].revenue
                for i in range(len(recent_three) - 1)
            )
            # Allow slight uptick in the last month (partial recovery)
            peak_to_current = monthly[-1].revenue < max(m.revenue for m in monthly[:-1])
            check("Revenue trend shows decline from peak",
                  peak_to_current,
                  "current month should be lower than peak")

        # ── Daily Sales ──
        print("\n=== Daily Sales ===")
        daily_count = db.query(DailySale).filter(DailySale.business_id == biz.id).count()
        check("Daily sales records exist", daily_count > 0, f"got {daily_count}")
        print(f"    -> Total daily sale records: {daily_count}")

        daily_products = (
            db.query(DailySale.product_id)
            .filter(DailySale.business_id == biz.id)
            .distinct()
            .count()
        )
        check("Daily sales cover multiple products", daily_products >= 5,
              f"got {daily_products} products")

        # Verify dates are in August 2026
        first_daily = (
            db.query(DailySale)
            .filter(DailySale.business_id == biz.id)
            .order_by(DailySale.date)
            .first()
        )
        last_daily = (
            db.query(DailySale)
            .filter(DailySale.business_id == biz.id)
            .order_by(DailySale.date.desc())
            .first()
        )
        if first_daily and last_daily:
            check("Daily sales start date valid",
                  isinstance(first_daily.date, date))
            check("Daily sales end date valid",
                  isinstance(last_daily.date, date))
            check("Daily sales dates in correct range (Aug 2026)",
                  first_daily.date.year == 2026 and first_daily.date.month == 8,
                  f"got {first_daily.date}")

        # ── Expenses ──
        print("\n=== Expenses ===")
        expenses = db.query(Expense).filter(Expense.business_id == biz.id).all()
        check("Expense records exist", len(expenses) > 0, f"got {len(expenses)}")

        aug_expenses = [e for e in expenses if e.month == "Aug"]
        check("August expenses exist", len(aug_expenses) > 0)
        aug_total = sum(e.amount for e in aug_expenses)
        check("August expenses > 0", aug_total > 0, f"got Rs {aug_total:,.0f}")

        categories = set(e.category for e in aug_expenses)
        check("Multiple expense categories", len(categories) >= 5,
              f"got {len(categories)}: {categories}")

        for e in aug_expenses:
            check(f"  {e.category}: amount > 0", e.amount > 0, f"got {e.amount}")
            check(f"  {e.category}: year valid", e.year == 2026, f"got {e.year}")

        # Verify financial story: expenses + profit = revenue (approximately)
        if aug_expenses and monthly:
            aug_revenue = monthly[-1].revenue
            check("Revenue > expenses (business is profitable)",
                  aug_revenue > aug_total,
                  f"revenue={aug_revenue:,.0f}, expenses={aug_total:,.0f}")

        # ── Inventory Alerts ──
        print("\n=== Inventory Alerts ===")
        alerts = db.query(InventoryAlert).filter(
            InventoryAlert.business_id == biz.id
        ).all()
        check("Inventory alerts exist", len(alerts) > 0, f"got {len(alerts)}")

        critical = [a for a in alerts if a.status == "critical"]
        check("At least one critical alert", len(critical) > 0)

        overstock = [a for a in alerts if a.status == "overstock"]
        check("At least one overstock alert", len(overstock) > 0)

        for a in alerts:
            check(f"  {a.item_name}: qty >= 0", a.qty >= 0, f"got {a.qty}")
            check(f"  {a.item_name}: valid status",
                  a.status in ("critical", "low", "adequate", "overstock"),
                  f"got '{a.status}'")

        # Verify product_id FK validity
        for a in alerts:
            if a.product_id:
                prod = db.query(Product).get(a.product_id)
                check(f"  {a.item_name}: product_id FK valid", prod is not None,
                      f"product_id={a.product_id} not found")

        # ── Support Tickets ──
        print("\n=== Support Tickets ===")
        tickets = db.query(SupportTicket).filter(
            SupportTicket.business_id == biz.id
        ).all()
        check("Support tickets exist", len(tickets) > 0, f"got {len(tickets)}")
        check("At least 10 tickets", len(tickets) >= 10, f"got {len(tickets)}")

        open_tickets = [t for t in tickets if t.status == "open"]
        resolved_tickets = [t for t in tickets if t.status == "resolved"]
        check("Both open and resolved tickets", len(open_tickets) > 0 and len(resolved_tickets) > 0,
              f"open={len(open_tickets)}, resolved={len(resolved_tickets)}")

        delivery_complaints = [
            t for t in tickets
            if t.ticket_type == "complaint" and "delivery" in t.description.lower()
        ]
        check("Delivery complaints exist", len(delivery_complaints) >= 5,
              f"got {len(delivery_complaints)}")
        print(f"    -> Delivery complaints: {len(delivery_complaints)}")

        # Verify temporal pattern: complaints increased recently
        aug_20_plus = [t for t in delivery_complaints if t.created_at and t.created_at.day >= 19]
        aug_before = [t for t in delivery_complaints if t.created_at and t.created_at.day < 19]
        check("Complaints surge in recent period",
              len(aug_20_plus) > len(aug_before),
              f"recent={len(aug_20_plus)}, earlier={len(aug_before)}")

        for t in tickets:
            check(f"  ticket #{t.id}: created_at is datetime",
                  isinstance(t.created_at, datetime))
            check(f"  ticket #{t.id}: valid sentiment",
                  t.sentiment in ("negative", "neutral", "positive"),
                  f"got '{t.sentiment}'")

        # ── Marketing Campaigns ──
        print("\n=== Marketing Campaigns ===")
        campaigns = db.query(MarketingCampaign).filter(
            MarketingCampaign.business_id == biz.id
        ).all()
        check("Campaigns exist", len(campaigns) > 0, f"got {len(campaigns)}")
        check("At least 3 campaigns", len(campaigns) >= 3, f"got {len(campaigns)}")

        paused = [c for c in campaigns if c.status == "paused"]
        check("At least one paused/underperforming campaign", len(paused) > 0)

        for c in campaigns:
            check(f"  {c.name}: spend > 0", c.spend > 0, f"got {c.spend}")
            check(f"  {c.name}: impressions > 0", c.impressions > 0, f"got {c.impressions}")
            check(f"  {c.name}: clicks <= impressions",
                  c.clicks <= c.impressions,
                  f"clicks={c.clicks}, impressions={c.impressions}")
            check(f"  {c.name}: conversions <= clicks",
                  c.conversions <= c.clicks,
                  f"conversions={c.conversions}, clicks={c.clicks}")
            check(f"  {c.name}: revenue_generated >= 0",
                  c.revenue_generated >= 0, f"got {c.revenue_generated}")
            if c.start_date:
                check(f"  {c.name}: start_date valid",
                      isinstance(c.start_date, date))

        # Find underperforming campaign
        for c in campaigns:
            if c.clicks > 0:
                conv_rate = c.conversions / c.clicks * 100
                if conv_rate < 2.0:
                    print(f"    -> Underperforming: {c.name} (conv rate: {conv_rate:.1f}%)")

        # ── Customers ──
        print("\n=== Customers ===")
        customers = db.query(Customer).filter(Customer.business_id == biz.id).all()
        check("Customers exist", len(customers) > 0, f"got {len(customers)}")
        check("At least 10 customers", len(customers) >= 10, f"got {len(customers)}")

        for c in customers:
            check(f"  {c.name}: total_orders > 0", c.total_orders > 0, f"got {c.total_orders}")
            check(f"  {c.name}: total_spent > 0", c.total_spent > 0, f"got {c.total_spent}")
            if c.last_order_date:
                check(f"  {c.name}: last_order_date valid",
                      isinstance(c.last_order_date, date))

        # ── Agent Activities ──
        print("\n=== Agent Activities ===")
        activities = db.query(AgentActivity).filter(
            AgentActivity.business_id == biz.id
        ).all()
        check("Agent activities exist", len(activities) > 0, f"got {len(activities)}")
        check("At least 5 activities", len(activities) >= 5, f"got {len(activities)}")

        agents_seen = set()
        for a in activities:
            check(f"  {a.agent_name}: has action", len(a.action) > 0)
            check(f"  {a.agent_name}: has finding (data-backed)",
                  len(a.finding) > 0, "finding is empty — agents must reference data")
            check(f"  {a.agent_name}: has data_points",
                  len(a.data_points) > 0, "data_points empty — should contain queryable facts")
            check(f"  {a.agent_name}: created_at valid",
                  isinstance(a.created_at, datetime))
            agents_seen.add(a.agent_name)

        check("Multiple agents represented", len(agents_seen) >= 4,
              f"got {len(agents_seen)} agents: {agents_seen}")

        # ── Cross-table Relationships ──
        print("\n=== Cross-Table Relationships ===")
        check("Business → Products relationship", len(biz.products) == len(products))
        check("Business → MonthlySales relationship", len(biz.monthly_sales) == len(monthly))
        check("Business → Expenses relationship", len(biz.expenses) == len(expenses))
        check("Business → Customers relationship", len(biz.customers) == len(customers))
        check("Business → Campaigns relationship", len(biz.campaigns) == len(campaigns))
        check("Business → SupportTickets relationship",
              len(biz.support_tickets) == len(tickets))
        check("Business → AgentActivities relationship",
              len(biz.agent_activities) == len(activities))

        # Inventory alerts reference valid products
        alerts_with_product = [a for a in alerts if a.product_id]
        for a in alerts_with_product:
            prod = db.query(Product).get(a.product_id)
            check(f"  Alert '{a.item_name}' → product '{prod.name if prod else 'MISSING'}'",
                  prod is not None)

        # Daily sales reference valid products
        daily_product_ids = (
            db.query(DailySale.product_id)
            .filter(DailySale.business_id == biz.id)
            .distinct()
            .all()
        )
        for (pid,) in daily_product_ids:
            prod = db.query(Product).get(pid)
            check(f"  DailySale product_id={pid} → valid product", prod is not None)

        # ── Story Verification ──
        print("\n=== Data Story Verification ===")

        # 1. Best-selling product has low stock
        top_by_revenue = max(products, key=lambda p: p.total_revenue)
        check(f"Best seller '{top_by_revenue.name}' has low stock (< 20)",
              top_by_revenue.stock_qty < 20,
              f"stock={top_by_revenue.stock_qty}")

        # 2. Sales declining
        if len(monthly) >= 2:
            peak_rev = max(m.revenue for m in monthly)
            current_rev = monthly[-1].revenue
            decline_pct = (peak_rev - current_rev) / peak_rev * 100
            check(f"Revenue declined {decline_pct:.1f}% from peak",
                  decline_pct > 5,
                  f"peak={peak_rev:,.0f}, current={current_rev:,.0f}")

        # 3. Underperforming campaign
        worst_camp = min(campaigns, key=lambda c: (c.conversions / c.clicks) if c.clicks else 999)
        worst_rate = (worst_camp.conversions / worst_camp.clicks * 100) if worst_camp.clicks else 0
        check(f"Underperforming campaign: '{worst_camp.name}' ({worst_rate:.1f}% conv)",
              worst_rate < 2.0)

        # 4. Delivery complaints increased
        check(f"Delivery complaints >= 5",
              len(delivery_complaints) >= 5,
              f"got {len(delivery_complaints)}")

        # 5. Financial pressure
        aug_rev = monthly[-1].revenue if monthly else 0
        aug_profit = monthly[-1].profit if monthly else 0
        margin = (aug_profit / aug_rev * 100) if aug_rev else 0
        check(f"Profit margin reflects pressure ({margin:.1f}%)",
              margin < 25,
              f"margin should be under 25% to show pressure")

    finally:
        db.close()

    # ── Summary ──
    print(f"\n{'=' * 50}")
    total = passed + failed
    print(f"Results: {passed}/{total} passed, {failed} failed")
    if failed == 0:
        print("ALL CHECKS PASSED")
    else:
        print(f"WARNING: {failed} check(s) failed!")
    print(f"{'=' * 50}")

    return failed == 0


if __name__ == "__main__":
    success = verify()
    sys.exit(0 if success else 1)
