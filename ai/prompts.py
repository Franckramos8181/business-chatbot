SYSTEM_PROMPT = """You are a financial analyst for a multi-service business that includes tax preparation, equipment rentals, mailing services, and related offerings.

You have access to real financial data from QuickBooks Online and operational data from supporting systems (EZRentOut, PictaMail, MyTaxPrepOffice, USPS).

When answering questions:
- Always cite specific numbers from the data when available
- Keep answers concise and actionable
- Use plain English, no accounting jargon unless the user asks for it
- When discussing pricing changes, always mention both the revenue impact and the profit impact
- When identifying opportunities, focus on low-risk changes that won't significantly impact customer retention
- If you don't have enough data to answer confidently, say so

You can help with:
- Revenue, expense, and profit analysis by product or service
- Pricing scenario modeling (e.g., "What if I raise X by $Y?")
- Identifying underpriced services and hidden profit opportunities
- Revenue and expense forecasting
- Credit card debt payoff planning
- Comparing performance across products and time periods"""


def build_context_prompt(snapshot):
    if not snapshot:
        return "\n\nNo financial snapshot is currently available. Use the available tools to pull live data."

    lines = [
        "\n\nCurrent Financial Summary (Year-to-Date):",
        f"  Total Revenue: ${snapshot.get('total_revenue', 0):,.2f}",
        f"  Total Expenses: ${snapshot.get('total_expenses', 0):,.2f}",
        f"  Net Profit: ${snapshot.get('net_profit', 0):,.2f}",
        f"  Total Liabilities: ${snapshot.get('total_liabilities', 0):,.2f}",
    ]

    products = snapshot.get("product_breakdown", [])
    if products:
        lines.append("\n  Top Products/Services by Revenue:")
        for p in products[:5]:
            lines.append(f"    - {p['name']}: ${p['total_revenue']:,.2f} revenue, {p['margin_pct']}% margin, ${p['net_profit']:,.2f} profit")

    insights = snapshot.get("insights", [])
    if insights:
        lines.append(f"\n  {len(insights)} optimization opportunities identified (use get_opportunities tool for details)")

    return "\n".join(lines)


TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_summary_metrics",
            "description": "Get total revenue, expenses, net profit, profit margin, and liabilities for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "period_end": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                },
                "required": ["period_start", "period_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_metrics",
            "description": "Get per-product breakdown of revenue, margin, volume, expenses, and profit for a date range",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_start": {"type": "string", "description": "Start date (YYYY-MM-DD)"},
                    "period_end": {"type": "string", "description": "End date (YYYY-MM-DD)"},
                },
                "required": ["period_start", "period_end"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_pricing_scenario",
            "description": "Calculate the impact of changing a product or service price. Shows projected revenue and profit change.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {"type": "string", "description": "Name of the product or service"},
                    "price_change": {"type": "number", "description": "Dollar amount to change the price by (positive for increase, negative for decrease)"},
                    "period_months": {"type": "integer", "description": "Number of months to project (default 12)", "default": 12},
                },
                "required": ["product_name", "price_change"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_forecast",
            "description": "Get projected revenue, expenses, or net profit for future months based on historical trends",
            "parameters": {
                "type": "object",
                "properties": {
                    "metric_name": {"type": "string", "enum": ["revenue", "expenses", "net_profit"], "description": "Which metric to forecast"},
                    "months_ahead": {"type": "integer", "description": "Number of months to forecast (default 6)", "default": 6},
                },
                "required": ["metric_name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_debt_forecast",
            "description": "Project credit card debt payoff timeline given a monthly payment amount",
            "parameters": {
                "type": "object",
                "properties": {
                    "monthly_payment": {"type": "number", "description": "Monthly payment amount in dollars"},
                    "annual_interest_rate": {"type": "number", "description": "Annual interest rate as decimal (default 0.20 = 20%)", "default": 0.20},
                },
                "required": ["monthly_payment"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_opportunities",
            "description": "Identify hidden pricing and profit optimization opportunities including underpriced services, low margins, and expense savings",
            "parameters": {
                "type": "object",
                "properties": {
                    "period_start": {"type": "string", "description": "Start date (YYYY-MM-DD, optional)"},
                    "period_end": {"type": "string", "description": "End date (YYYY-MM-DD, optional)"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_customer_data",
            "description": "Get top customers ranked by revenue or outstanding balance",
            "parameters": {
                "type": "object",
                "properties": {
                    "sort_by": {"type": "string", "enum": ["revenue", "balance"], "description": "Sort customers by total revenue or outstanding balance", "default": "revenue"},
                    "limit": {"type": "integer", "description": "Number of customers to return (default 10)", "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_operational_data",
            "description": "Get operational data from EZRentOut (rentals), PictaMail (marketing), MyTaxPrepOffice (tax prep volume), or USPS (shipping costs)",
            "parameters": {
                "type": "object",
                "properties": {
                    "source": {"type": "string", "enum": ["ezrentout", "pictamail", "mytaxprepoffice", "usps"], "description": "Data source to query"},
                    "data_type": {"type": "string", "description": "Type of data to retrieve (e.g., 'equipment_utilization', 'campaign_spend')"},
                },
                "required": ["source"],
            },
        },
    },
]
