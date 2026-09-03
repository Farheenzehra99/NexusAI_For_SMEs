import random
from datetime import datetime, timedelta, date
from sqlalchemy.orm import Session
from ..models.business import (
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
    ("Embroidered Kurti — White",  "AG-KT-001", "critical",  5,   25000),
    ("Lawn Print — Bloom Design A", "AG-LP-001", "low",      23,  115000),
    ("Formal Shalwar — Navy",      "AG-SK-001", "overstock", 480, 2880000),
    ("Summer Pret — Floral",       "AG-PR-001", "low",       31,  155000),
    ("Bridal Wear — Red",          "AG-BW-001", "adequate",  35,  0),
    ("Lawn Print — Azure",         "AG-LP-002", "adequate",  120, 0),
]

_SUPPORT_TICKETS = [
    ("Fatima Zahra",    "complaint", "resolved", "negative", "Stitching loose on kurti neckline", "WhatsApp", 3, 4),
    ("Hassan Raza",     "inquiry",   "resolved", "neutral",  "Delivery status for order #1042",   "Phone",    5, 5),
    ("Mariam Siddiqui", "return",    "resolved", "neutral",  "Size exchange for Lawn Print Azure", "Website",  8, 10),
    ("Bilal Ahmed",     "inquiry",   "resolved", "positive", "Bulk order query for corporate gift", "Email",  12, 13),
    ("Aisha Khan",      "complaint", "open",     "negative", "Late delivery: 6 days overdue",     "WhatsApp", 14, None),
    ("Zainab Noor",     "complaint", "open",     "negative", "Courier didn't attempt delivery",   "Phone",    18, None),
    ("Sana Malik",      "complaint", "open",     "negative", "Wrong color sent for Bridal Wear",  "WhatsApp", 20, None),
    ("Usman Tariq",     "complaint", "open",     "negative", "Courier parcel damaged on arrival",  "Website",  22, None),
    ("Rabia Sultana",   "complaint", "open",     "negative", "Delayed 5 days, no tracking update", "WhatsApp", 24, None),
    ("Imran Hussain",   "complaint", "open",     "negative", "Courier asked for extra delivery fee","Phone",   26, None),
]

_CAMPAIGNS = [
    ("Summer Lawn Push",     "Instagram", 80000,  125000, 8500, 340, 1700000, "active",  1, 31),
    ("Eid Preview Teasers",  "Facebook",  45000,  89000,  4200, 180, 900000,  "active", 10, None),
    ("Khan Fabrics Counter", "Instagram", 30000,  67000, 6786, 95,  285000,  "paused",  5, 20),
    ("Digital Lookbook",     "Facebook",  25000,  45000,  2800, 142, 710000,  "active", 15, None),
]

_AGENT_ACTIVITIES = [
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


def seed_business_data(db: Session, biz: Business):
    """Seed comprehensive realistic SME data for a specific business."""
    rng = random.Random(biz.id + 100)

    # For the primary demo business (ID 1), use exact blueprint numbers.
    # For any new business signup, scale organically so each tenant has unique data & analytics.
    scale = 1.0 if biz.id == 1 else (0.8 + ((biz.id * 17) % 10) * 0.08)

    # --- Products ---
    product_map = {}
    for sku, name, cat, price, cost, stock, reorder, sales, rev, trend in PRODUCTS:
        p_sku = f"{sku}-B{biz.id}"
        scaled_stock = stock if biz.id == 1 else max(3, int(stock * scale + rng.randint(-2, 5)))
        scaled_sales = sales if biz.id == 1 else int(sales * scale)
        scaled_rev = rev if biz.id == 1 else round(scaled_sales * price, 2)
        p = Product(
            business_id=biz.id, sku=p_sku, name=name, category=cat,
            price=price, cost=cost, stock_qty=scaled_stock, reorder_threshold=reorder,
            total_sales=scaled_sales, total_revenue=scaled_rev, trend=trend,
        )
        db.add(p)
        product_map[sku] = p
    db.flush()

    # --- Monthly Sales ---
    for year, month, revenue, profit, orders in MONTHLY_SALES:
        s_rev = revenue if biz.id == 1 else round(revenue * scale, -4)
        s_prof = profit if biz.id == 1 else round(profit * scale, -4)
        s_ord = orders if biz.id == 1 else max(10, int(orders * scale))
        db.add(MonthlySale(
            business_id=biz.id, year=year, month=month,
            revenue=s_rev, profit=s_prof, orders=s_ord,
        ))

    # --- Expenses ---
    for year, month, _, _, _ in MONTHLY_SALES:
        for cat, desc, amount, recurring in _EXPENSE_TPL:
            s_amount = amount if biz.id == 1 else round(amount * scale, -3)
            db.add(Expense(
                business_id=biz.id, category=cat, description=desc,
                amount=s_amount, year=year, month=month,
                is_recurring=1 if recurring else 0,
            ))

    # --- Daily Sales (August 2026) ---
    aug_start = date(2026, 8, 1)
    aug_days = 31
    sku_list = [p[0] for p in PRODUCTS]
    for day_offset in range(aug_days):
        current_date = aug_start + timedelta(days=day_offset)
        is_weekend = current_date.weekday() in (4, 5)
        daily_factor = 0.7 if is_weekend else 1.0

        for sku in sku_list:
            p = product_map[sku]
            avg_units_per_day = (p.total_sales / 183) * daily_factor
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
        s_spent = spent if biz.id == 1 else round(spent * scale, -2)
        s_orders = orders if biz.id == 1 else max(1, int(orders * scale))
        db.add(Customer(
            business_id=biz.id, name=name, phone=phone, email=f"b{biz.id}_{email}",
            city=city, total_orders=s_orders, total_spent=s_spent,
            last_order_date=last_order,
        ))

    # --- Inventory Alerts ---
    for item_name, sku, status, qty, risk in INVENTORY_ALERTS:
        p = product_map.get(sku)
        s_qty = qty if biz.id == 1 else max(1, int(qty * scale))
        s_risk = risk if biz.id == 1 else round(risk * scale, -2)
        db.add(InventoryAlert(
            business_id=biz.id,
            product_id=p.id if p else None,
            item_name=item_name,
            status=status,
            qty=s_qty,
            estimated_revenue_at_risk=s_risk,
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
        s_spend = spend if biz.id == 1 else round(spend * scale, -3)
        s_impr = impr if biz.id == 1 else int(impr * scale)
        s_clicks = clicks if biz.id == 1 else int(clicks * scale)
        s_conv = conv if biz.id == 1 else max(5, int(conv * scale))
        s_rev_gen = rev_gen if biz.id == 1 else round(rev_gen * scale, -3)
        db.add(MarketingCampaign(
            business_id=biz.id, name=name, channel=channel,
            spend=s_spend, impressions=s_impr, clicks=s_clicks,
            conversions=s_conv, revenue_generated=s_rev_gen, status=status,
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
        message=f"Low inventory alert for your top catalog item at {biz.name}.",
        is_read=0, created_at=now - timedelta(minutes=10)
    ))
    db.add(Notification(
        business_id=biz.id, type="info", title="Workforce Connected", 
        message=f"6 AI Specialists are now monitoring {biz.name} in real-time.",
        is_read=0, created_at=now - timedelta(hours=1)
    ))
    db.add(Notification(
        business_id=biz.id, type="success", title="Welcome to SME Growth OS", 
        message=f"Welcome {biz.owner_name}! Your AI workforce is ready in the Command Center.",
        is_read=1, created_at=now - timedelta(hours=3)
    ))

    db.commit()
