import logging
from datetime import date

import gspread
from google.oauth2.service_account import Credentials

from config.settings import settings
from db.connection import get_session
from db.models import AnalysisSnapshot

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def _get_client():
    creds = Credentials.from_service_account_file(settings.GOOGLE_SHEETS_CREDS_FILE, scopes=SCOPES)
    return gspread.authorize(creds)


def _get_or_create_sheet(gc, title):
    if settings.GOOGLE_SHEETS_SPREADSHEET_ID:
        return gc.open_by_key(settings.GOOGLE_SHEETS_SPREADSHEET_ID)
    try:
        return gc.open(title)
    except gspread.SpreadsheetNotFound:
        return gc.create(title)


def export_to_sheet(snapshot_date=None):
    if not settings.GOOGLE_SHEETS_CREDS_FILE:
        logger.warning("Google Sheets credentials not configured, skipping export")
        return

    with get_session() as session:
        if snapshot_date:
            snapshot = session.query(AnalysisSnapshot).filter_by(snapshot_date=snapshot_date).first()
        else:
            snapshot = session.query(AnalysisSnapshot).order_by(AnalysisSnapshot.snapshot_date.desc()).first()

        if not snapshot:
            logger.warning("No snapshot available for export")
            return

        gc = _get_client()
        spreadsheet = _get_or_create_sheet(gc, f"Business Analysis - {snapshot.snapshot_date}")

        _write_summary(spreadsheet, snapshot)
        _write_products(spreadsheet, snapshot)
        _write_opportunities(spreadsheet, snapshot)

        logger.info(f"Exported snapshot {snapshot.snapshot_date} to Google Sheets")


def _get_or_create_worksheet(spreadsheet, title, rows=100, cols=20):
    try:
        return spreadsheet.worksheet(title)
    except gspread.WorksheetNotFound:
        return spreadsheet.add_worksheet(title=title, rows=rows, cols=cols)


def _write_summary(spreadsheet, snapshot):
    ws = _get_or_create_worksheet(spreadsheet, "Summary")
    ws.clear()

    data = [
        ["Financial Summary", f"As of {snapshot.snapshot_date}"],
        [],
        ["Metric", "Amount"],
        ["Total Revenue", f"${float(snapshot.total_revenue or 0):,.2f}"],
        ["Total Expenses", f"${float(snapshot.total_expenses or 0):,.2f}"],
        ["Net Profit", f"${float(snapshot.net_profit or 0):,.2f}"],
        ["Total Liabilities", f"${float(snapshot.total_liabilities or 0):,.2f}"],
    ]

    if snapshot.net_profit and snapshot.total_revenue:
        margin = float(snapshot.net_profit) / float(snapshot.total_revenue) * 100
        data.append(["Profit Margin", f"{margin:.1f}%"])

    ws.update(range_name="A1", values=data)


def _write_products(spreadsheet, snapshot):
    ws = _get_or_create_worksheet(spreadsheet, "Products")
    ws.clear()

    headers = ["Product/Service", "Revenue", "Expenses", "Net Profit", "Margin %", "Volume", "Avg Price"]
    rows = [headers]

    for p in (snapshot.product_breakdown or []):
        rows.append([
            p.get("name", ""),
            f"${p.get('total_revenue', 0):,.2f}",
            f"${p.get('total_expenses', 0):,.2f}",
            f"${p.get('net_profit', 0):,.2f}",
            f"{p.get('margin_pct', 0):.1f}%",
            f"{p.get('total_quantity', 0):.0f}",
            f"${p.get('avg_price', 0):,.2f}",
        ])

    ws.update(range_name="A1", values=rows)


def _write_opportunities(spreadsheet, snapshot):
    ws = _get_or_create_worksheet(spreadsheet, "Opportunities")
    ws.clear()

    headers = ["Type", "Product/Category", "Suggestion", "Potential Impact"]
    rows = [headers]

    for o in (snapshot.insights or []):
        rows.append([
            o.get("type", ""),
            o.get("product", o.get("category", "")),
            o.get("suggestion", ""),
            f"${o.get('potential_impact', 0):,.2f}" if o.get("potential_impact") else "",
        ])

    ws.update(range_name="A1", values=rows)
