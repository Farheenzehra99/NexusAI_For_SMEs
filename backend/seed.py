import sys
import os
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, SessionLocal, Base
from app.models.business import Business
from app.core.security import hash_password
from app.services.seeder import seed_business_data

BUSINESS = dict(
    name="Ahmed Clothing Store",
    tagline="Premium Pakistani Clothing & Retail",
    owner_name="Ahmed Ali",
    email="ahmed@clothingstore.com",
    password_hash=hash_password("password123"),
    location="Hyderabad, Pakistan",
    currency="PKR",
    established_year=2018,
    total_customers=847,
    health_score=72,
)


def seed(*, reset: bool = False):
    """Seed the database with Ali Garments demo data."""
    if reset:
        print("Dropping all tables (--reset)...")
        Base.metadata.drop_all(bind=engine)

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        existing = db.query(Business).filter(Business.email == BUSINESS["email"]).first()
        if existing:
            print("Database already seeded with demo user. Use --reset to re-seed.")
            return

        biz = Business(**BUSINESS)
        db.add(biz)
        db.commit()
        db.refresh(biz)

        seed_business_data(db, biz)
        print("Database seeded successfully with Ali Garments demo data.")
        print(f"Login Credentials:")
        print(f"  Email: {BUSINESS['email']}")
        print(f"  Password: password123")
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
