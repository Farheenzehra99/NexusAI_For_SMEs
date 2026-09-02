from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Date
from sqlalchemy.orm import relationship
from datetime import datetime

from ..database import Base


class Business(Base):
    __tablename__ = "businesses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    tagline = Column(String, default="")
    owner_name = Column(String, nullable=False)
    location = Column(String, default="")
    currency = Column(String, default="PKR")
    established_year = Column(Integer, default=2018)
    total_customers = Column(Integer, default=0)
    health_score = Column(Integer, default=72)
    created_at = Column(DateTime, default=datetime.utcnow)

    products = relationship("Product", back_populates="business")
    monthly_sales = relationship("MonthlySale", back_populates="business")
    daily_sales = relationship("DailySale", back_populates="business")
    expenses = relationship("Expense", back_populates="business")
    inventory_alerts = relationship("InventoryAlert", back_populates="business")
    support_tickets = relationship("SupportTicket", back_populates="business")
    campaigns = relationship("MarketingCampaign", back_populates="business")
    customers = relationship("Customer", back_populates="business")
    agent_activities = relationship("AgentActivity", back_populates="business")
    notifications = relationship("Notification", back_populates="business")
    settings = relationship("UserSettings", back_populates="business", uselist=False)

class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    sku = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    category = Column(String, default="")
    price = Column(Float, default=0)
    cost = Column(Float, default=0)
    stock_qty = Column(Integer, default=0)
    reorder_threshold = Column(Integer, default=20)
    total_sales = Column(Integer, default=0)
    total_revenue = Column(Float, default=0)
    trend = Column(String, default="stable")
    is_active = Column(Integer, default=1)

    business = relationship("Business", back_populates="products")
    daily_sales = relationship("DailySale", back_populates="product")


class MonthlySale(Base):
    __tablename__ = "monthly_sales"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    year = Column(Integer, nullable=False)
    month = Column(String, nullable=False)
    revenue = Column(Float, default=0)
    profit = Column(Float, default=0)
    orders = Column(Integer, default=0)

    business = relationship("Business", back_populates="monthly_sales")


class DailySale(Base):
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    product_id = Column(Integer, ForeignKey("products.id"))
    date = Column(Date, nullable=False)
    qty_sold = Column(Integer, default=0)
    revenue = Column(Float, default=0)

    business = relationship("Business", back_populates="daily_sales")
    product = relationship("Product", back_populates="daily_sales")


class Expense(Base):
    __tablename__ = "expenses"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    category = Column(String, nullable=False)
    description = Column(String, default="")
    amount = Column(Float, default=0)
    year = Column(Integer, nullable=False)
    month = Column(String, nullable=False)
    is_recurring = Column(Integer, default=1)

    business = relationship("Business", back_populates="expenses")


class InventoryAlert(Base):
    __tablename__ = "inventory_alerts"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    item_name = Column(String, nullable=False)
    status = Column(String, nullable=False)
    qty = Column(Integer, default=0)
    estimated_revenue_at_risk = Column(Float, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="inventory_alerts")


class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    customer_name = Column(String, default="")
    ticket_type = Column(String, default="complaint")
    status = Column(String, default="open")
    sentiment = Column(String, default="negative")
    description = Column(Text, default="")
    channel = Column(String, default="phone")
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    business = relationship("Business", back_populates="support_tickets")


class MarketingCampaign(Base):
    __tablename__ = "marketing_campaigns"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String, nullable=False)
    channel = Column(String, default="")
    spend = Column(Float, default=0)
    impressions = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    revenue_generated = Column(Float, default=0)
    status = Column(String, default="active")
    start_date = Column(Date, nullable=True)
    end_date = Column(Date, nullable=True)

    business = relationship("Business", back_populates="campaigns")


class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    name = Column(String, nullable=False)
    phone = Column(String, default="")
    email = Column(String, default="")
    city = Column(String, default="")
    total_orders = Column(Integer, default=0)
    total_spent = Column(Float, default=0)
    last_order_date = Column(Date, nullable=True)

    business = relationship("Business", back_populates="customers")


class AgentActivity(Base):
    __tablename__ = "agent_activities"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    agent_name = Column(String, nullable=False)
    action = Column(String, nullable=False)
    finding = Column(Text, default="")
    data_points = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="agent_activities")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"))
    type = Column(String, default="info") # alert, info, success
    title = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    business = relationship("Business", back_populates="notifications")


class UserSettings(Base):
    __tablename__ = "user_settings"

    id = Column(Integer, primary_key=True, index=True)
    business_id = Column(Integer, ForeignKey("businesses.id"), unique=True)
    language = Column(String, default="en") # en, ur, roman_ur
    email_notifications = Column(Integer, default=1)
    proactive_actions = Column(Integer, default=1)

    business = relationship("Business", back_populates="settings")

