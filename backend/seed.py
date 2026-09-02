"""
NexusAI Seed Script — Ali Garments Demo Data
==============================================

Seeds the database with a coherent data story for one Pakistani clothing retailer.

The Story
---------
- Best-selling product (Embroidered Kurti Set) has critically low stock (5 units)
- Revenue has declined 16% from peak (Rs 5.8M in Apr → Rs 4.85M in Aug)
- One marketing campaign (Khan Fabrics Counter) is severely underperforming
- Delivery complaints have surged — 12 complaints in the last 2 weeks
- Financial pressure: expenses flat at Rs 3.86M/month while revenue drops

Usage
-----
    python seed.py          # Seed (skips if already seeded)
    python seed.py --reset  # Drop all tables and re-seed
"""

import sys
import os
import argparse
import random
from datetime import datetime, timedelta, date

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models.business import (
    Business,
    Product,
    MonthlySale,
    DailySale,
    Expense,
    InventoryAlert,
    SupportTicket,
    MarketingCampaign,
    Customer,
    AgentActivity,
    UserSettings,
    Notification,
)


# ---------------------------------------------------------------------------
# Static seed data
# ---------------------------------------------------------------------------

BUSINESS = dict(
    name="Ali Garments",
    tagline="Premium Pakistani Clothing",
    owner_name="Ahmed Ali",
    location="Hyderabad, Pakistan",
    currency="PKR",
    established_year=2018,
    total_customers=847,
    health_score=72,
)

PRODUCTS = [
    # (sku, name, category, price, cost, stock, reorder_threshold, total_sales, total_revenue, trend)
    ("AG-LP-001", "Lawn Print — Bloom",      "Lawn",       5000, 2500, 150, 30, 145, 725000,  "up"),
    ("AG-LP-002", "Lawn Print — Azure",      "Lawn",       5000, 2400, 120, 30, 112, 560000,  "stable"),
    ("AG-LP-003", "Lawn Print — Sage",       "Lawn",       4800, 2500, 95,  25, 98,  470400,  "stable"),
    ("AG-KT-001", "Embroidered Kurti — White","Kurti",      5000, 2800, 5,   20, 218, 1090000, "up"),
    ("AG-KT-002", "Embroidered Kurti — Gold", "Kurti",     5500, 3000, 42,  20, 87,  478500,  "up"),
    ("AG-SK-001", "Formal Shalwar — Navy",    "Formal",    6000, 3200, 480, 30, 156, 936000,  "down"),
    ("AG-SK-002", "Formal Shalwar — Grey",    "Formal",    6000, 3100, 65,  25, 52,  312000,  "down"),
    ("AG-PR-001", "Summer Pret — Floral",     "Pret",      5000, 2600, 95,  25, 134, 670000,  "down"),
    ("AG-BW-001", "Bridal Wear — Red",        "Bridal",    25000, 12000, 35, 10, 43, 1075000, "up"),
    ("AG-BW-002", "Bridal Wear — Gold",       "Bridal",    30000, 14000, 22, 8,  28,  840000,  "stable"),
    ("AG-WS-001", "Winter Shawl — Pashmina",  "Accessories",3000, 1200, 200, 20, 12,  36000,  "down"),
    ("AG-KF-001", "Kids Festive — Boys",      "Kids",      3000, 1500, 85,  15, 8,   24000,   "down"),
    ("AG-KF-002", "Kids Festive — Girls",     "Kids",      3200, 1600, 78,  15, 6,   19200,   "down"),
    ("AG-DC-001", "Denim Jeans — Classic",    "Western",   3500, 1800, 120, 20, 15,  52500,   "down"),
    ("AG-DC-002", "Denim Jacket — Washed",    "Western",   4500, 2200, 55,  15, 11,  49500,   "down"),
]

MONTHLY_SALES = [
    # (year, month, revenue, profit, orders)
    (2026, "Mar", 5200000, 1100000, 118),
    (2026, "Apr", 5800000, 1250000, 128),
    (2026, "May", 5500000, 1150000, 121),
    (2026, "Jun", 5100000, 980000,  112),
    (2026, "Jul", 4600000, 850000,  102),
    (2026, "Aug", 4850000, 890000,  96),
]

# Monthly expenses (repeated for each of the 6 months, values in PKR)
_EXPENSE_TPL = [
    ("Salaries",    "Staff wages (8 employees)",    1800000, True),
    ("Rent",        "Shop rent — Shahi Bazaar",      650000,  True),
    ("Utilities",   "Electricity, gas, internet",   280000,  True),
    ("Marketing",   "Social media ads & promos",    155000,  True),
    ("Logistics",   "Courier & delivery charges",   320000,  True),
    ("Raw Materials","Fabric procurement",           450000,  True),
    ("Misc",        "Packaging, repairs, misc",     200000,  True),
]

CUSTOMERS = [
    # (name, phone, email, city, total_orders, total_spent, last_order_date)
    ("Fatima Zahra",     "+92-321-4567890", "fatima.z@gmail.com",   "Lahore",       24, 185000, date(2026, 8, 27)),
    ("Aisha Khan",       "+92-300-1234567", "aisha.k@outlook.com",  "Lahore",       18, 142000, date(2026, 8, 25)),
    ("Hassan Raza",      "+92-333-9876543", "hassan.r@gmail.com",   "Karachi",      15, 118000, date(2026, 8, 20)),
    ("Mariam Siddiqui",  "+92-345-6789012", "mariam.s@yahoo.com",   "Islamabad",    12, 95000,  date(2026, 8, 18)),
    ("Bilal Ahmed",      "+92-312-3456789", "bilal.a@gmail.com",    "Lahore",       10, 78000,  date(2026, 8, 26)),
    ("Sana Malik",       "+92-322-5678901", "sana.m@gmail.com",     "Faisalabad",   8,  62000,  date(2026, 8, 15)),
    ("Usman Tariq",      "+92-311-2345678", "usman.t@outlook.com",  "Rawalpindi",   7,  54000,  date(2026, 8, 10)),
    ("Zainab Noor",      "+92-346-8901234", "zainab.n@gmail.com",   "Lahore",       6,  48000,  date(2026, 8, 22)),
    ("Tariq Mehmood",    "+92-301-4567890", "tariq.m@gmail.com",    "Multan",       5,  38000,  date(2026, 7, 28)),
    ("Rabia Sultana",    "+92-334-7890123", "rabia.s@yahoo.com",    "Lahore",       4,  32000,  date(2026, 8, 5)),
    ("Imran Hussain",    "+92-323-0123456", "imran.h@gmail.com",    "Sialkot",      3,  24000,  date(2026, 7, 15)),
    ("Nadia Parveen",    "+92-347-2345678", "nadia.p@gmail.com",    "Lahore",       2,  15000,  date(2026, 8, 1)),
]

INVENTORY_ALERTS = [
    # (item_name, sku, status, qty, estimated_revenue_at_risk)
    ("Embroidered Kurti — White",  "AG-KT-001", "critical",  5,   25000),
    ("Lawn Print — Bloom Design A", "AG-LP-001", "low",      23,  115000),
    ("Formal Shalwar — Navy",      "AG-SK-001", "overstock", 480, 2880000),
    ("Summer Pret — Floral",       "AG-PR-001", "low",       31,  155000),
    ("Bridal Wear — Red",          "AG-BW-001", "adequate",  35,  0),
    ("Lawn Print — Azure",         "AG-LP-002", "adequate",  120, 0),
]

# created_at dates relative to Aug 2026
_SUPPORT_TICKETS = [
    # (customer_name, type, status, sentiment, description, channel, day_of_aug, resolved_day)
    ("Fatima Zahra",    "complaint", "resolved", "negative",
     "Delivery delayed by 3 days — order #AG-4521", "whatsapp", 3, 5),
    ("Hassan Raza",     "complaint", "resolved", "negative",
     "Wrong size delivered for Formal Shalwar — order #AG-4533", "phone", 5, 8),
    ("Mariam Siddiqui", "inquiry",   "resolved", "neutral",
     "When will Eid collection be available?", "whatsapp", 7, 7),
    ("Aisha Khan",      "return",    "resolved", "negative",
     "Color different from website image — Lawn Print Azure", "phone", 8, 12),
    ("Sana Malik",      "complaint", "resolved", "negative",
     "Delivery delayed by 5 days — order #AG-4601", "whatsapp", 12, 15),
    ("Bilal Ahmed",     "complaint", "resolved", "negative",
     "Package arrived damaged — Bridal Wear Red", "phone", 14, 18),
    ("Usman Tariq",     "inquiry",   "resolved", "neutral",
     "Do you offer COD for orders above Rs 10,000?", "whatsapp", 15, 15),
    ("Zainab Noor",     "complaint", "open",     "negative",
     "Delivery delayed by 7 days — order #AG-4678", "whatsapp", 19, None),
    ("Fatima Zahra",    "complaint", "open",     "negative",
     "Wrong item delivered — received Sage instead of Bloom", "phone", 20, None),
    ("Rabia Sultana",   "complaint", "open",     "negative",
     "Delivery delayed by 10 days — order #AG-4702", "whatsapp", 21, None),
    ("Aisha Khan",      "complaint", "open",     "negative",
     "Courier did not attempt delivery — no notification", "phone", 22, None),
    ("Hassan Raza",     "complaint", "open",     "negative",
     "Delivery delayed by 6 days — order #AG-4715", "whatsapp", 23, None),
    ("Mariam Siddiqui", "return",    "open",     "negative",
     "Fabric quality not as expected — Summer Pret Floral", "phone", 24, None),
    ("Nadia Parveen",   "complaint", "open",     "negative",
     "Delivery tracking shows delivered but not received", "whatsapp", 25, None),
    ("Tariq Mehmood",   "complaint", "open",     "negative",
     "Wrong color delivered — ordered Gold, received White", "phone", 26, None),
    ("Imran Hussain",   "inquiry",   "resolved", "neutral",
     "Can I exchange Kids Festive Wear for a larger size?", "whatsapp", 26, 28),
    ("Bilal Ahmed",     "complaint", "open",     "negative",
     "Delivery delayed by 4 days — order #AG-4740", "whatsapp", 27, None),
    ("Sana Malik",      "complaint", "open",     "negative",
     "Embroidery stitching is loose — Kurti White", "phone", 28, None),
]

_CAMPAIGNS = [
    # (name, channel, spend, impressions, clicks, conversions, revenue_generated, status, start_day, end_day)
    ("Summer Lawn Push",     "Instagram", 80000,  125000, 8500, 340, 1700000, "active",  1, 31),
    ("Eid Preview Teasers",  "Facebook",  45000,  89000,  4200, 180, 900000,  "active", 10, None),
    ("Khan Fabrics Counter", "Instagram", 30000,  67000, 6786, 95,  285000,  "paused",  5, 20),
    ("Digital Lookbook",     "Facebook",  25000,  45000,  2800, 142, 710000,  "active", 15, None),
]

_AGENT_ACTIVITIES = [
    # (agent_name, action, finding, data_points, minutes_ago)
    ("Finance Agent",
     "Flagged declining revenue trend",
     "Revenue declined 16.4% from peak. Apr revenue Rs 5.8M, Aug revenue Rs 4.85M. Profit margin compressed from 21.6% to 18.4%. Expenses flat at Rs 3.86M/month.",
     "months_analyzed=6, peak_month=Apr, peak_revenue=5800000, current_revenue=4850000, expense_avg=3855000",
     2),
    ("Inventory Agent",
     "Critical stock alert — best seller at 5 units",
     "Embroidered Kurti White (AG-KT-001) is the top revenue product (Rs 1.09M, 218 sales) but has only 5 units remaining. At current sell rate (~18/week), stock will deplete in 2 days. Estimated revenue at risk: Rs 25,000 per day of stockout.",
     "product_id=4, sku=AG-KT-001, stock=5, weekly_rate=18, days_until_stockout=2, revenue_at_risk_daily=25000",
     15),
    ("Marketing Agent",
     "Flagged underperforming campaign — Khan Fabrics Counter",
     "Khan Fabrics Counter campaign has conversion rate of 1.4% (platform avg 4.5%). Cost per conversion is Rs 316 vs Rs 235 for Summer Lawn Push. Recommendation: pause and reallocate Rs 30,000 budget to higher-performing channels.",
     "campaign=Khan Fabrics Counter, conversion_rate=1.4, platform_avg=4.5, cost_per_conversion=316, spend=30000",
     60),
    ("Customer Support Agent",
     "Surge in delivery complaints detected",
     "6 delivery-related complaints in the last 15 days, up from 2 in the prior 15-day period (+200%). Root cause: courier partner delays — 4 of the 6 recent complaints cite delays between 4 and 10 days, and all 6 remain unresolved. Overall complaints rose from 3 to 10 across the same periods.",
     "period_complaints=6, prior_period=2, delivery_delays=4, unresolved_critical=6, complaints_trend=3_to_10",
     180),
    ("BI Agent",
     "Identified overstock risk in Formal Shalwar line",
     "Formal Shalwar Navy has 480 units (6.2 months of supply at current sell rate of 13/week). This ties up Rs 2.88M in retail value. Recommend clearance pricing or bundle offers before winter season.",
     "product=Formal Shalwar Navy, stock=480, weekly_rate=13, months_supply=6.2, value_at_risk=2880000",
     360),
]


# ---------------------------------------------------------------------------
# Seed function
# ---------------------------------------------------------------------------

def seed(*, reset: bool = False):
    """Seed the database with Ali Garments demo data."""
    if reset:
        print("Dropping all tables (--reset)...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Idempotency check
        if db.query(Business).first():
            print("Database already seeded. Use --reset to re-seed.")
            db.close()
            return

        rng = random.Random(42)  # deterministic seed for reproducibility

        # --- Business ---
        biz = Business(**BUSINESS)
        db.add(biz)
        db.flush()

        # --- Products ---
        product_map = {}  # sku -> Product
        for sku, name, cat, price, cost, stock, reorder, sales, rev, trend in PRODUCTS:
            p = Product(
                business_id=biz.id, sku=sku, name=name, category=cat,
                price=price, cost=cost, stock_qty=stock, reorder_threshold=reorder,
                total_sales=sales, total_revenue=rev, trend=trend,
            )
            db.add(p)
            product_map[sku] = p
        db.flush()

        # --- Monthly Sales ---
        for year, month, revenue, profit, orders in MONTHLY_SALES:
            db.add(MonthlySale(
                business_id=biz.id, year=year, month=month,
                revenue=revenue, profit=profit, orders=orders,
            ))

        # --- Expenses (same categories each month) ---
        months_list = [m[1] for m in MONTHLY_SALES]
        for year, month, _, _, _ in MONTHLY_SALES:
            for cat, desc, amount, recurring in _EXPENSE_TPL:
                db.add(Expense(
                    business_id=biz.id, category=cat, description=desc,
                    amount=amount, year=year, month=month,
                    is_recurring=1 if recurring else 0,
                ))

        # --- Daily Sales (August 2026 — last 31 days) ---
        aug_start = date(2026, 8, 1)
        aug_days = 31
        aug_revenue = 4850000
        avg_daily_rev = aug_revenue / aug_days

        # Build product weight map (higher-selling products get more daily entries)
        sku_list = [p[0] for p in PRODUCTS]
        for day_offset in range(aug_days):
            current_date = aug_start + timedelta(days=day_offset)
            # Slightly less sales on weekends (Fri/Sat in Pakistan)
            is_weekend = current_date.weekday() in (4, 5)  # Fri, Sat
            daily_factor = 0.7 if is_weekend else 1.0

            for sku in sku_list:
                p = product_map[sku]
                avg_units_per_day = (p.total_sales / 183) * daily_factor  # ~6 months
                qty = max(0, int(round(avg_units_per_day + rng.uniform(-0.8, 0.8))))
                if qty > 0:
                    db.add(DailySale(
                        business_id=biz.id,
                        product_id=p.id,
                        date=current_date,
                        qty_sold=qty,
                        revenue=round(qty * p.price, 2),
                    ))

        # --- Customers ---
        for name, phone, email, city, orders, spent, last_order in CUSTOMERS:
            db.add(Customer(
                business_id=biz.id, name=name, phone=phone, email=email,
                city=city, total_orders=orders, total_spent=spent,
                last_order_date=last_order,
            ))

        # --- Inventory Alerts ---
        for item_name, sku, status, qty, risk in INVENTORY_ALERTS:
            p = product_map.get(sku)
            db.add(InventoryAlert(
                business_id=biz.id,
                product_id=p.id if p else None,
                item_name=item_name,
                status=status,
                qty=qty,
                estimated_revenue_at_risk=risk,
                created_at=datetime(2026, 8, 28, 10, 0, 0),
            ))

        # --- Support Tickets ---
        for cust, ttype, status, sent, desc, channel, day, resolved in _SUPPORT_TICKETS:
            created = datetime(2026, 8, day, rng.randint(9, 18), rng.randint(0, 59))
            resolved_dt = None
            if resolved is not None:
                resolved_dt = datetime(2026, 8, resolved, rng.randint(10, 17), rng.randint(0, 59))
            db.add(SupportTicket(
                business_id=biz.id, customer_name=cust,
                ticket_type=ttype, status=status, sentiment=sent,
                description=desc, channel=channel,
                created_at=created, resolved_at=resolved_dt,
            ))

        # --- Marketing Campaigns ---
        for name, channel, spend, impr, clicks, conv, rev_gen, status, start_d, end_d in _CAMPAIGNS:
            db.add(MarketingCampaign(
                business_id=biz.id, name=name, channel=channel,
                spend=spend, impressions=impr, clicks=clicks,
                conversions=conv, revenue_generated=rev_gen, status=status,
                start_date=date(2026, 8, start_d),
                end_date=date(2026, 8, end_d) if end_d else None,
            ))

        # --- Agent Activities ---
        now = datetime.utcnow()
        for agent, action, finding, data_pts, mins_ago in _AGENT_ACTIVITIES:
            db.add(AgentActivity(
                business_id=biz.id, agent_name=agent,
                action=action, finding=finding, data_points=data_pts,
                created_at=now - timedelta(minutes=mins_ago),
            ))

        # --- Settings and Notifications ---
        db.add(UserSettings(
            business_id=biz.id, language="en", email_notifications=1, proactive_actions=1
        ))
        db.add(Notification(
            business_id=biz.id, type="alert", title="Critical Inventory Alert", 
            message="Embroidered Kurti White (AG-KT-001) stock is down to 5 units.",
            is_read=0, created_at=now - timedelta(minutes=10)
        ))
        db.add(Notification(
            business_id=biz.id, type="info", title="Marketing Campaign Paused", 
            message="Khan Fabrics Counter campaign was automatically paused by the Marketing Agent due to low ROI.",
            is_read=0, created_at=now - timedelta(hours=1)
        ))
        db.add(Notification(
            business_id=biz.id, type="success", title="Weekly Report Generated", 
            message="Your customized business health report for week 34 is ready.",
            is_read=1, created_at=now - timedelta(hours=3)
        ))

        db.commit()
        print("Database seeded successfully with Ali Garments data.")
        print(f"  Products: {len(PRODUCTS)}")
        print(f"  Monthly sales: {len(MONTHLY_SALES)} months")
        print(f"  Daily sales: Aug 2026 ({aug_days} days × {len(PRODUCTS)} products)")
        print(f"  Expense categories: {len(_EXPENSE_TPL)} × {len(MONTHLY_SALES)} months")
        print(f"  Customers: {len(CUSTOMERS)}")
        print(f"  Inventory alerts: {len(INVENTORY_ALERTS)}")
        print(f"  Support tickets: {len(_SUPPORT_TICKETS)}")
        print(f"  Marketing campaigns: {len(_CAMPAIGNS)}")
        print(f"  Agent activities: {len(_AGENT_ACTIVITIES)}")

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed NexusAI database with Ali Garments data")
    parser.add_argument("--reset", action="store_true", help="Drop all tables and re-seed")
    args = parser.parse_args()
    seed(reset=args.reset)
