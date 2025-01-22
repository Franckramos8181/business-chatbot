import logging
from collections import defaultdict
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import func

from db.connection import get_session
from db.models import Revenue, Expense, Liability, ProductService, AnalysisSnapshot

logger = logging.getLogger(__name__)


def summary_metrics(period_start, period_end):
    with get_session() as session:
        total_revenue = session.query(func.sum(Revenue.amount)).filter(
            Revenue.txn_date >= period_start,
            Revenue.txn_date <= period_end,
        ).scalar() or Decimal("0")

        total_expenses = session.query(func.sum(Expense.amount)).filter(
            Expense.txn_date >= period_start,
            Expense.txn_date <= period_end,
        ).scalar() or Decimal("0")

        total_liabilities = session.query(func.sum(Liability.balance)).filter(
            Liability.balance_date == session.query(func.max(Liability.balance_date)).scalar()
        ).scalar() or Decimal("0")

        net_profit = total_revenue - total_expenses

        return {
            "period_start": str(period_start),
            "period_end": str(period_end),
            "total_revenue": float(total_revenue),
            "total_expenses": float(total_expenses),
            "net_profit": float(net_profit),
            "profit_margin": float(net_profit / total_revenue * 100) if total_revenue else 0,
            "total_liabilities": float(total_liabilities),
        }


def product_metrics(period_start, period_end):
    with get_session() as session:
        products = session.query(ProductService).filter_by(is_active=True).all()
        results = []

        for product in products:
            revenue = session.query(
                func.sum(Revenue.amount),
                func.sum(Revenue.quantity),
            ).filter(
                Revenue.product_service_id == product.id,
                Revenue.txn_date >= period_start,
                Revenue.txn_date <= period_end,
            ).first()

            total_revenue = float(revenue[0] or 0)
            total_quantity = float(revenue[1] or 0)

            expenses = session.query(func.sum(Expense.amount)).filter(
                Expense.product_service_id == product.id,
                Expense.txn_date >= period_start,
                Expense.txn_date <= period_end,
            ).scalar() or Decimal("0")
            total_expenses = float(expenses)

            avg_price = total_revenue / total_quantity if total_quantity else float(product.unit_price or 0)
            unit_cost = float(product.cost or 0)
            margin = ((avg_price - unit_cost) / avg_price * 100) if avg_price else 0
            net_profit = total_revenue - total_expenses

            results.append({
                "product_id": product.id,
                "name": product.name,
                "type": product.type,
                "unit_price": float(product.unit_price or 0),
                "unit_cost": unit_cost,
                "total_revenue": total_revenue,
                "total_expenses": total_expenses,
                "total_quantity": total_quantity,
                "avg_price": round(avg_price, 2),
                "margin_pct": round(margin, 1),
                "net_profit": round(net_profit, 2),
            })

        results.sort(key=lambda x: x["total_revenue"], reverse=True)
        return results


def identify_opportunities(period_start=None, period_end=None):
    if not period_start:
        period_start = date(date.today().year, 1, 1).isoformat()
    if not period_end:
        period_end = date.today().isoformat()

    products = product_metrics(period_start, period_end)
    opportunities = []

    for p in products:
        if p["total_quantity"] == 0:
            continue

        if p["margin_pct"] < 30 and p["total_revenue"] > 0:
            opportunities.append({
                "type": "low_margin",
                "product": p["name"],
                "current_margin": p["margin_pct"],
                "suggestion": f"{p['name']} has a {p['margin_pct']}% margin. Consider raising the price or reducing costs.",
                "potential_impact": round(p["total_revenue"] * 0.05, 2),
            })

        if p["unit_cost"] > 0 and p["avg_price"] < p["unit_cost"] * 1.5:
            opportunities.append({
                "type": "underpriced",
                "product": p["name"],
                "avg_price": p["avg_price"],
                "unit_cost": p["unit_cost"],
                "suggestion": f"{p['name']} is priced at ${p['avg_price']:.2f} with a cost of ${p['unit_cost']:.2f}. A small price increase could significantly improve margins.",
                "potential_impact": round(p["total_quantity"] * 5, 2),
            })

        if p["total_quantity"] > 50 and p["margin_pct"] > 50:
            opportunities.append({
                "type": "premium_add_on",
                "product": p["name"],
                "volume": p["total_quantity"],
                "suggestion": f"{p['name']} has high volume ({p['total_quantity']:.0f} units) and strong margins. Consider offering a premium tier or add-on services.",
                "potential_impact": round(p["total_quantity"] * 10, 2),
            })

    with get_session() as session:
        expense_categories = session.query(
            Expense.account_name,
            func.sum(Expense.amount).label("total"),
        ).filter(
            Expense.txn_date >= period_start,
            Expense.txn_date <= period_end,
        ).group_by(Expense.account_name).order_by(func.sum(Expense.amount).desc()).limit(10).all()

        for category, total in expense_categories:
            if total and float(total) > 1000:
                opportunities.append({
                    "type": "expense_review",
                    "category": category or "Uncategorized",
                    "amount": float(total),
                    "suggestion": f"Review '{category}' expenses (${float(total):,.2f}) for potential savings.",
                })

    return opportunities


def save_snapshot(period_start=None, period_end=None):
    if not period_start:
        period_start = date(date.today().year, 1, 1).isoformat()
    if not period_end:
        period_end = date.today().isoformat()

    summary = summary_metrics(period_start, period_end)
    products = product_metrics(period_start, period_end)
    opps = identify_opportunities(period_start, period_end)

    today = date.today()

    with get_session() as session:
        existing = session.query(AnalysisSnapshot).filter_by(snapshot_date=today).first()
        data = {
            "snapshot_date": today,
            "total_revenue": summary["total_revenue"],
            "total_expenses": summary["total_expenses"],
            "net_profit": summary["net_profit"],
            "total_liabilities": summary["total_liabilities"],
            "product_breakdown": products,
            "insights": opps,
        }

        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
        else:
            session.add(AnalysisSnapshot(**data))

    logger.info(f"Saved analysis snapshot for {today}")
    return {"summary": summary, "products": products, "opportunities": opps}
