import logging
from datetime import date, timedelta
from collections import defaultdict

import numpy as np
from sqlalchemy import func, extract

from db.connection import get_session
from db.models import Revenue, Expense, Liability

logger = logging.getLogger(__name__)


def _monthly_totals(session, model, amount_col, months_back=24):
    cutoff = date.today() - timedelta(days=months_back * 30)
    results = session.query(
        extract("year", model.txn_date).label("year"),
        extract("month", model.txn_date).label("month"),
        func.sum(amount_col).label("total"),
    ).filter(
        model.txn_date >= cutoff,
    ).group_by("year", "month").order_by("year", "month").all()

    return [(int(r.year), int(r.month), float(r.total)) for r in results]


def _linear_forecast(monthly_data, months_ahead):
    if len(monthly_data) < 3:
        avg = np.mean([d[2] for d in monthly_data]) if monthly_data else 0
        return [{"month": i + 1, "value": round(float(avg), 2)} for i in range(months_ahead)]

    values = np.array([d[2] for d in monthly_data])
    x = np.arange(len(values))

    coeffs = np.polyfit(x, values, 1)
    slope, intercept = coeffs

    forecasted = []
    for i in range(months_ahead):
        future_x = len(values) + i
        predicted = slope * future_x + intercept
        predicted = max(predicted, 0)

        last_year, last_month = monthly_data[-1][0], monthly_data[-1][1]
        forecast_month = last_month + i + 1
        forecast_year = last_year + (forecast_month - 1) // 12
        forecast_month = ((forecast_month - 1) % 12) + 1

        forecasted.append({
            "year": forecast_year,
            "month": forecast_month,
            "value": round(float(predicted), 2),
            "trend": "up" if slope > 0 else "down" if slope < 0 else "flat",
        })

    return forecasted


def forecast_metric(metric_name, months_ahead=6):
    with get_session() as session:
        if metric_name == "revenue":
            monthly = _monthly_totals(session, Revenue, Revenue.amount)
        elif metric_name == "expenses":
            monthly = _monthly_totals(session, Expense, Expense.amount)
        elif metric_name == "net_profit":
            rev_monthly = _monthly_totals(session, Revenue, Revenue.amount)
            exp_monthly = _monthly_totals(session, Expense, Expense.amount)
            exp_by_month = {(y, m): t for y, m, t in exp_monthly}
            monthly = [
                (y, m, t - exp_by_month.get((y, m), 0))
                for y, m, t in rev_monthly
            ]
        else:
            return {"error": f"Unknown metric: {metric_name}. Use 'revenue', 'expenses', or 'net_profit'."}

    forecast = _linear_forecast(monthly, months_ahead)

    historical_avg = np.mean([d[2] for d in monthly]) if monthly else 0
    forecast_avg = np.mean([f["value"] for f in forecast]) if forecast else 0

    return {
        "metric": metric_name,
        "months_ahead": months_ahead,
        "historical_months": len(monthly),
        "historical_avg_monthly": round(float(historical_avg), 2),
        "forecast_avg_monthly": round(float(forecast_avg), 2),
        "forecast": forecast,
    }


def debt_payoff_forecast(monthly_payment, annual_interest_rate=0.20):
    with get_session() as session:
        latest_date = session.query(func.max(Liability.balance_date)).scalar()
        if not latest_date:
            return {"error": "No liability data available"}

        total_debt = session.query(func.sum(Liability.balance)).filter(
            Liability.balance_date == latest_date,
            Liability.account_type == "Credit Card",
        ).scalar()

        if not total_debt:
            return {"message": "No credit card debt found", "total_debt": 0}

        total_debt = float(total_debt)

    monthly_rate = annual_interest_rate / 12
    balance = total_debt
    months = 0
    total_interest = 0
    schedule = []

    while balance > 0 and months < 360:
        interest = balance * monthly_rate
        principal = min(monthly_payment - interest, balance)

        if principal <= 0:
            return {
                "error": f"Monthly payment of ${monthly_payment:,.2f} is less than the monthly interest of ${interest:,.2f}. Increase the payment amount.",
                "minimum_payment": round(interest + 1, 2),
            }

        balance -= principal
        total_interest += interest
        months += 1

        schedule.append({
            "month": months,
            "payment": round(monthly_payment if balance > 0 else principal + interest, 2),
            "principal": round(principal, 2),
            "interest": round(interest, 2),
            "remaining_balance": round(max(balance, 0), 2),
        })

    return {
        "total_debt": round(total_debt, 2),
        "monthly_payment": round(monthly_payment, 2),
        "annual_interest_rate": annual_interest_rate,
        "months_to_payoff": months,
        "total_interest_paid": round(total_interest, 2),
        "total_paid": round(total_debt + total_interest, 2),
        "payoff_date": str(date.today() + timedelta(days=months * 30)),
        "schedule_summary": schedule[:6] + (schedule[-3:] if len(schedule) > 6 else []),
    }
