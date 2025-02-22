"""Seed the database with sample data for development and testing."""

import logging
from datetime import date, datetime, timezone
from decimal import Decimal

from db.connection import get_session
from db.models import Customer, ProductService, Revenue, Expense, Liability

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

SAMPLE_PRODUCTS = [
    {"qb_id": "1", "name": "Individual Tax Return", "type": "Service", "unit_price": 150, "cost": 20},
    {"qb_id": "2", "name": "Business Tax Return", "type": "Service", "unit_price": 350, "cost": 45},
    {"qb_id": "3", "name": "Bookkeeping Monthly", "type": "Service", "unit_price": 200, "cost": 30},
    {"qb_id": "4", "name": "Equipment Rental - Printer", "type": "Service", "unit_price": 75, "cost": 15},
    {"qb_id": "5", "name": "Mail Processing", "type": "Service", "unit_price": 25, "cost": 8},
    {"qb_id": "6", "name": "Notary Service", "type": "Service", "unit_price": 15, "cost": 2},
    {"qb_id": "7", "name": "Tax Prep Premium Add-On", "type": "Service", "unit_price": 50, "cost": 5},
    {"qb_id": "8", "name": "Payroll Service", "type": "Service", "unit_price": 125, "cost": 20},
]

SAMPLE_CUSTOMERS = [
    {"qb_id": "100", "display_name": "Smith Family", "email": "smith@example.com", "balance": 150},
    {"qb_id": "101", "display_name": "Johnson LLC", "email": "johnson@example.com", "balance": 700},
    {"qb_id": "102", "display_name": "Williams Corp", "email": "williams@example.com", "balance": 0},
    {"qb_id": "103", "display_name": "Brown & Associates", "email": "brown@example.com", "balance": 350},
    {"qb_id": "104", "display_name": "Davis Tax Client", "email": "davis@example.com", "balance": 0},
]


def seed():
    with get_session() as session:
        logger.info("Seeding products/services...")
        for p in SAMPLE_PRODUCTS:
            session.add(ProductService(**p, synced_at=datetime.now(timezone.utc)))

        logger.info("Seeding customers...")
        for c in SAMPLE_CUSTOMERS:
            session.add(Customer(**c, synced_at=datetime.now(timezone.utc)))

    logger.info("Seeding revenue and expense records...")
    with get_session() as session:
        products = {p.qb_id: p.id for p in session.query(ProductService).all()}
        customers = {c.qb_id: c.id for c in session.query(Customer).all()}

        import random
        random.seed(42)
        rev_count = 0

        for month in range(1, 13):
            for prod_qb_id, prod_id in products.items():
                volume = random.randint(5, 30)
                for i in range(volume):
                    day = random.randint(1, 28)
                    cust_id = random.choice(list(customers.values()))
                    product = session.query(ProductService).get(prod_id)
                    price = float(product.unit_price) * random.uniform(0.9, 1.1)

                    session.add(Revenue(
                        qb_id=f"REV-2024-{month:02d}-{prod_qb_id}-{i}",
                        qb_type="Invoice",
                        customer_id=cust_id,
                        product_service_id=prod_id,
                        txn_date=date(2024, month, day),
                        amount=round(price, 2),
                        quantity=1,
                        synced_at=datetime.now(timezone.utc),
                    ))
                    rev_count += 1

        logger.info(f"Seeded {rev_count} revenue records")

        exp_count = 0
        expense_categories = ["Office Supplies", "Rent", "Software", "Insurance", "Utilities", "Marketing"]
        for month in range(1, 13):
            for category in expense_categories:
                amount = random.uniform(200, 2000)
                day = random.randint(1, 28)
                session.add(Expense(
                    qb_id=f"EXP-2024-{month:02d}-{category}",
                    qb_type="Purchase",
                    vendor_name=f"{category} Vendor",
                    account_name=category,
                    txn_date=date(2024, month, day),
                    amount=round(amount, 2),
                    synced_at=datetime.now(timezone.utc),
                ))
                exp_count += 1

        logger.info(f"Seeded {exp_count} expense records")

        session.add(Liability(
            qb_account_id="CC-001",
            account_name="Business Credit Card",
            account_type="Credit Card",
            balance=8500,
            balance_date=date.today(),
            synced_at=datetime.now(timezone.utc),
        ))
        session.add(Liability(
            qb_account_id="LOAN-001",
            account_name="Equipment Loan",
            account_type="Long Term Liability",
            balance=15000,
            balance_date=date.today(),
            synced_at=datetime.now(timezone.utc),
        ))

    logger.info("Database seeded successfully!")


if __name__ == "__main__":
    seed()
