import logging
from datetime import datetime, date, timezone

from db.connection import get_session
from db.models import Customer, ProductService, Revenue, Expense, Liability
from quickbooks.client import QuickBooksClient

logger = logging.getLogger(__name__)


def _upsert(session, model, qb_id_field, qb_id_value, data):
    existing = session.query(model).filter(qb_id_field == qb_id_value).first()
    if existing:
        for key, value in data.items():
            setattr(existing, key, value)
        existing.updated_at = datetime.now(timezone.utc)
        return existing
    else:
        record = model(**data)
        session.add(record)
        return record


def sync_customers(client=None):
    client = client or QuickBooksClient()
    customers = client.query("Customer")
    count = 0

    with get_session() as session:
        for c in customers:
            _upsert(session, Customer, Customer.qb_id, c["Id"], {
                "qb_id": c["Id"],
                "display_name": c.get("DisplayName", ""),
                "email": c.get("PrimaryEmailAddr", {}).get("Address", "") if c.get("PrimaryEmailAddr") else "",
                "balance": c.get("Balance", 0),
                "is_active": c.get("Active", True),
                "raw_data": c,
                "synced_at": datetime.now(timezone.utc),
            })
            count += 1

    logger.info(f"Synced {count} customers")
    return count


def sync_products_services(client=None):
    client = client or QuickBooksClient()
    items = client.query("Item")
    count = 0

    with get_session() as session:
        for item in items:
            _upsert(session, ProductService, ProductService.qb_id, item["Id"], {
                "qb_id": item["Id"],
                "name": item.get("Name", ""),
                "type": item.get("Type", ""),
                "unit_price": item.get("UnitPrice", 0),
                "cost": item.get("PurchaseCost", 0),
                "description": item.get("Description", ""),
                "is_active": item.get("Active", True),
                "raw_data": item,
                "synced_at": datetime.now(timezone.utc),
            })
            count += 1

    logger.info(f"Synced {count} products/services")
    return count


def _get_product_id(session, item_ref):
    if not item_ref:
        return None
    product = session.query(ProductService).filter_by(qb_id=item_ref.get("value", "")).first()
    return product.id if product else None


def _get_customer_id(session, customer_ref):
    if not customer_ref:
        return None
    customer = session.query(Customer).filter_by(qb_id=customer_ref.get("value", "")).first()
    return customer.id if customer else None


def sync_revenue(client=None, start_date=None, end_date=None):
    client = client or QuickBooksClient()
    count = 0

    for entity_type in ["Invoice", "SalesReceipt"]:
        where_parts = []
        if start_date:
            where_parts.append(f"TxnDate >= '{start_date}'")
        if end_date:
            where_parts.append(f"TxnDate <= '{end_date}'")

        where_clause = " AND ".join(where_parts) if where_parts else None
        records = client.query(entity_type, where_clause=where_clause)

        with get_session() as session:
            for record in records:
                txn_date = record.get("TxnDate", str(date.today()))
                customer_ref = record.get("CustomerRef")
                customer_id = _get_customer_id(session, customer_ref)

                for i, line in enumerate(record.get("Line", [])):
                    if line.get("DetailType") not in ("SalesItemLineDetail",):
                        continue

                    detail = line.get("SalesItemLineDetail", {})
                    item_ref = detail.get("ItemRef")
                    qb_line_id = f"{record['Id']}-{i}"

                    _upsert(session, Revenue, Revenue.qb_id, qb_line_id, {
                        "qb_id": qb_line_id,
                        "qb_type": entity_type,
                        "customer_id": customer_id,
                        "product_service_id": _get_product_id(session, item_ref),
                        "txn_date": txn_date,
                        "amount": line.get("Amount", 0),
                        "quantity": detail.get("Qty", 1),
                        "description": line.get("Description", ""),
                        "raw_data": line,
                        "synced_at": datetime.now(timezone.utc),
                    })
                    count += 1

    logger.info(f"Synced {count} revenue line items")
    return count


def sync_expenses(client=None, start_date=None, end_date=None):
    client = client or QuickBooksClient()
    count = 0

    for entity_type in ["Purchase", "Bill"]:
        where_parts = []
        if start_date:
            where_parts.append(f"TxnDate >= '{start_date}'")
        if end_date:
            where_parts.append(f"TxnDate <= '{end_date}'")

        where_clause = " AND ".join(where_parts) if where_parts else None
        records = client.query(entity_type, where_clause=where_clause)

        with get_session() as session:
            for record in records:
                txn_date = record.get("TxnDate", str(date.today()))
                vendor_name = ""
                if record.get("EntityRef"):
                    vendor_name = record["EntityRef"].get("name", "")

                for i, line in enumerate(record.get("Line", [])):
                    detail_type = line.get("DetailType", "")
                    if detail_type not in ("AccountBasedExpenseLineDetail", "ItemBasedExpenseLineDetail"):
                        continue

                    detail = line.get(detail_type, {})
                    account_name = detail.get("AccountRef", {}).get("name", "") if detail.get("AccountRef") else ""
                    item_ref = detail.get("ItemRef")
                    qb_line_id = f"{record['Id']}-{i}"

                    _upsert(session, Expense, Expense.qb_id, qb_line_id, {
                        "qb_id": qb_line_id,
                        "qb_type": entity_type,
                        "vendor_name": vendor_name,
                        "account_name": account_name,
                        "product_service_id": _get_product_id(session, item_ref),
                        "txn_date": txn_date,
                        "amount": line.get("Amount", 0),
                        "description": line.get("Description", ""),
                        "raw_data": line,
                        "synced_at": datetime.now(timezone.utc),
                    })
                    count += 1

    logger.info(f"Synced {count} expense line items")
    return count


def sync_liabilities(client=None):
    client = client or QuickBooksClient()
    today = date.today()

    liability_types = ("Credit Card", "Long Term Liability", "Other Current Liability")
    accounts = client.query("Account", where_clause=f"AccountType IN {liability_types!r}")
    count = 0

    with get_session() as session:
        for account in accounts:
            qb_account_id = account["Id"]
            existing = session.query(Liability).filter_by(
                qb_account_id=qb_account_id, balance_date=today
            ).first()

            data = {
                "qb_account_id": qb_account_id,
                "account_name": account.get("Name", ""),
                "account_type": account.get("AccountType", ""),
                "balance": account.get("CurrentBalance", 0),
                "balance_date": today,
                "raw_data": account,
                "synced_at": datetime.now(timezone.utc),
            }

            if existing:
                for key, value in data.items():
                    setattr(existing, key, value)
            else:
                session.add(Liability(**data))
            count += 1

    logger.info(f"Synced {count} liability accounts")
    return count


def full_sync(start_date=None, end_date=None):
    client = QuickBooksClient()
    logger.info("Starting full QuickBooks sync...")

    results = {
        "customers": sync_customers(client),
        "products_services": sync_products_services(client),
        "revenue": sync_revenue(client, start_date, end_date),
        "expenses": sync_expenses(client, start_date, end_date),
        "liabilities": sync_liabilities(client),
    }

    logger.info(f"Full sync complete: {results}")
    return results
