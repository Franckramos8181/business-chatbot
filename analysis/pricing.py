import logging
from decimal import Decimal

from sqlalchemy import func

from db.connection import get_session
from db.models import Revenue, ProductService

logger = logging.getLogger(__name__)

DEFAULT_ELASTICITY = 0.02


def run_scenario(product_name, price_change, period_months=12, elasticity=None):
    if elasticity is None:
        elasticity = DEFAULT_ELASTICITY

    with get_session() as session:
        product = session.query(ProductService).filter(
            ProductService.name.ilike(f"%{product_name}%")
        ).first()

        if not product:
            return {"error": f"Product '{product_name}' not found"}

        revenue_data = session.query(
            func.sum(Revenue.amount),
            func.sum(Revenue.quantity),
            func.count(Revenue.id),
        ).filter(
            Revenue.product_service_id == product.id,
        ).first()

        total_revenue = float(revenue_data[0] or 0)
        total_quantity = float(revenue_data[1] or 0)
        txn_count = revenue_data[2] or 0

        if total_quantity == 0:
            return {
                "product": product.name,
                "error": "No sales data available for this product",
            }

        current_price = float(product.unit_price or 0)
        if current_price == 0:
            current_price = total_revenue / total_quantity

        new_price = current_price + price_change

        months_of_data = max(txn_count / max(total_quantity / 12, 1), 1)
        annual_volume = total_quantity / months_of_data * 12

        pct_change = abs(price_change) / current_price if current_price else 0
        volume_impact = 1.0 - (elasticity * pct_change * 100) if price_change > 0 else 1.0 + (elasticity * pct_change * 100)
        projected_volume = annual_volume * volume_impact

        current_annual_revenue = annual_volume * current_price
        projected_annual_revenue = projected_volume * new_price
        revenue_change = projected_annual_revenue - current_annual_revenue

        unit_cost = float(product.cost or 0)
        current_annual_profit = annual_volume * (current_price - unit_cost)
        projected_annual_profit = projected_volume * (new_price - unit_cost)
        profit_change = projected_annual_profit - current_annual_profit

        return {
            "product": product.name,
            "current_price": round(current_price, 2),
            "new_price": round(new_price, 2),
            "price_change": round(price_change, 2),
            "current_annual_volume": round(annual_volume, 0),
            "projected_annual_volume": round(projected_volume, 0),
            "volume_change_pct": round((volume_impact - 1) * 100, 1),
            "current_annual_revenue": round(current_annual_revenue, 2),
            "projected_annual_revenue": round(projected_annual_revenue, 2),
            "revenue_change": round(revenue_change, 2),
            "unit_cost": round(unit_cost, 2),
            "current_annual_profit": round(current_annual_profit, 2),
            "projected_annual_profit": round(projected_annual_profit, 2),
            "profit_change": round(profit_change, 2),
            "elasticity_assumption": elasticity,
        }


def find_safe_increases(min_margin=40, max_increase_pct=10):
    with get_session() as session:
        products = session.query(ProductService).filter_by(is_active=True).all()
        results = []

        for product in products:
            revenue_data = session.query(
                func.sum(Revenue.amount),
                func.sum(Revenue.quantity),
            ).filter(Revenue.product_service_id == product.id).first()

            total_quantity = float(revenue_data[1] or 0)
            if total_quantity == 0:
                continue

            current_price = float(product.unit_price or 0)
            unit_cost = float(product.cost or 0)

            if current_price == 0:
                current_price = float(revenue_data[0] or 0) / total_quantity

            margin = ((current_price - unit_cost) / current_price * 100) if current_price else 0

            if margin >= min_margin:
                max_increase = current_price * (max_increase_pct / 100)
                scenario = run_scenario(product.name, round(max_increase, 2))
                if "error" not in scenario:
                    results.append({
                        "product": product.name,
                        "current_price": current_price,
                        "current_margin": round(margin, 1),
                        "suggested_increase": round(max_increase, 2),
                        "projected_profit_change": scenario["profit_change"],
                    })

        results.sort(key=lambda x: x["projected_profit_change"], reverse=True)
        return results


def target_profit_analysis(target_annual_profit, current_annual_profit=None):
    if current_annual_profit is None:
        from analysis.metrics import summary_metrics
        from datetime import date
        start = date(date.today().year, 1, 1).isoformat()
        end = date.today().isoformat()
        summary = summary_metrics(start, end)
        current_annual_profit = summary["net_profit"]

    gap = target_annual_profit - current_annual_profit
    if gap <= 0:
        return {
            "message": f"Current profit (${current_annual_profit:,.2f}) already meets the target (${target_annual_profit:,.2f}).",
            "gap": 0,
            "suggestions": [],
        }

    safe_increases = find_safe_increases()
    suggestions = []
    remaining_gap = gap

    for product in safe_increases:
        if remaining_gap <= 0:
            break
        contribution = min(product["projected_profit_change"], remaining_gap)
        suggestions.append({
            "product": product["product"],
            "price_increase": product["suggested_increase"],
            "profit_contribution": round(contribution, 2),
        })
        remaining_gap -= contribution

    return {
        "current_annual_profit": round(current_annual_profit, 2),
        "target_annual_profit": round(target_annual_profit, 2),
        "gap": round(gap, 2),
        "achievable_through_pricing": round(gap - max(remaining_gap, 0), 2),
        "remaining_gap": round(max(remaining_gap, 0), 2),
        "suggestions": suggestions,
    }
