import json
import logging
import uuid
from datetime import date, datetime, timezone

from openai import OpenAI
from sqlalchemy import func

from config.settings import settings
from db.connection import get_session
from db.models import AnalysisSnapshot, ChatHistory, Customer, Revenue, OperationalData
from ai.prompts import SYSTEM_PROMPT, TOOL_DEFINITIONS, build_context_prompt

logger = logging.getLogger(__name__)

client = OpenAI(api_key=settings.OPENAI_API_KEY)

TOOL_HANDLERS = {}


def _register_handlers():
    from analysis.metrics import summary_metrics, product_metrics, identify_opportunities
    from analysis.pricing import run_scenario
    from analysis.forecast import forecast_metric, debt_payoff_forecast

    TOOL_HANDLERS["get_summary_metrics"] = lambda args: summary_metrics(
        args["period_start"], args["period_end"]
    )
    TOOL_HANDLERS["get_product_metrics"] = lambda args: product_metrics(
        args["period_start"], args["period_end"]
    )
    TOOL_HANDLERS["get_pricing_scenario"] = lambda args: run_scenario(
        args["product_name"],
        args["price_change"],
        args.get("period_months", 12),
    )
    TOOL_HANDLERS["get_forecast"] = lambda args: forecast_metric(
        args["metric_name"],
        args.get("months_ahead", 6),
    )
    TOOL_HANDLERS["get_debt_forecast"] = lambda args: debt_payoff_forecast(
        args["monthly_payment"],
        args.get("annual_interest_rate", 0.20),
    )
    TOOL_HANDLERS["get_opportunities"] = lambda args: identify_opportunities(
        args.get("period_start"),
        args.get("period_end"),
    )
    TOOL_HANDLERS["get_customer_data"] = _get_customer_data
    TOOL_HANDLERS["get_operational_data"] = _get_operational_data


def _get_customer_data(args):
    sort_by = args.get("sort_by", "revenue")
    limit = args.get("limit", 10)

    with get_session() as session:
        if sort_by == "balance":
            customers = session.query(Customer).filter(
                Customer.is_active == True
            ).order_by(Customer.balance.desc()).limit(limit).all()

            return [
                {
                    "name": c.display_name,
                    "email": c.email,
                    "balance": float(c.balance or 0),
                }
                for c in customers
            ]
        else:
            results = session.query(
                Customer.display_name,
                Customer.email,
                func.sum(Revenue.amount).label("total_revenue"),
            ).join(Revenue, Revenue.customer_id == Customer.id).group_by(
                Customer.id, Customer.display_name, Customer.email
            ).order_by(func.sum(Revenue.amount).desc()).limit(limit).all()

            return [
                {
                    "name": r.display_name,
                    "email": r.email,
                    "total_revenue": float(r.total_revenue),
                }
                for r in results
            ]


def _get_operational_data(args):
    source = args["source"]
    data_type = args.get("data_type")

    with get_session() as session:
        query = session.query(OperationalData).filter_by(source=source)
        if data_type:
            query = query.filter_by(data_type=data_type)
        records = query.order_by(OperationalData.reference_date.desc()).limit(50).all()

        return [
            {
                "source": r.source,
                "data_type": r.data_type,
                "date": str(r.reference_date) if r.reference_date else None,
                "amount": float(r.amount) if r.amount else None,
                "quantity": float(r.quantity) if r.quantity else None,
                "details": r.metadata,
            }
            for r in records
        ]


def _get_latest_snapshot():
    with get_session() as session:
        snapshot = session.query(AnalysisSnapshot).order_by(
            AnalysisSnapshot.snapshot_date.desc()
        ).first()

        if not snapshot:
            return None

        return {
            "total_revenue": float(snapshot.total_revenue or 0),
            "total_expenses": float(snapshot.total_expenses or 0),
            "net_profit": float(snapshot.net_profit or 0),
            "total_liabilities": float(snapshot.total_liabilities or 0),
            "product_breakdown": snapshot.product_breakdown or [],
            "insights": snapshot.insights or [],
        }


def _save_message(session_id, role, content, function_call=None):
    with get_session() as session:
        msg = ChatHistory(
            session_id=session_id,
            role=role,
            content=content,
            function_call=function_call,
        )
        session.add(msg)


def _load_history(session_id, limit=20):
    with get_session() as session:
        messages = session.query(ChatHistory).filter_by(
            session_id=session_id
        ).order_by(ChatHistory.created_at.desc()).limit(limit).all()

        return [
            {"role": m.role, "content": m.content}
            for m in reversed(messages)
        ]


def chat(user_message, session_id=None):
    if not TOOL_HANDLERS:
        _register_handlers()

    if session_id is None:
        session_id = uuid.uuid4()

    snapshot = _get_latest_snapshot()
    system_content = SYSTEM_PROMPT + build_context_prompt(snapshot)

    history = _load_history(session_id)

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})

    _save_message(session_id, "user", user_message)

    max_iterations = 5
    for _ in range(max_iterations):
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
        )

        choice = response.choices[0]

        if choice.finish_reason == "tool_calls":
            tool_results = []
            for tool_call in choice.message.tool_calls:
                fn_name = tool_call.function.name
                fn_args = json.loads(tool_call.function.arguments)

                logger.info(f"Tool call: {fn_name}({fn_args})")

                handler = TOOL_HANDLERS.get(fn_name)
                if handler:
                    try:
                        result = handler(fn_args)
                    except Exception as e:
                        logger.error(f"Tool error: {e}")
                        result = {"error": str(e)}
                else:
                    result = {"error": f"Unknown tool: {fn_name}"}

                tool_results.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, default=str),
                })

            messages.append(choice.message)
            messages.extend(tool_results)
            continue

        assistant_message = choice.message.content or ""
        _save_message(session_id, "assistant", assistant_message)

        return {
            "response": assistant_message,
            "session_id": str(session_id),
        }

    return {
        "response": "I wasn't able to complete the analysis. Please try rephrasing your question.",
        "session_id": str(session_id),
    }
