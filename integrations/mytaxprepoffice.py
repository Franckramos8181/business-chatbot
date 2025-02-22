import logging
from datetime import datetime, date, timezone

import requests

from config.settings import settings
from db.connection import get_session
from db.models import OperationalData

logger = logging.getLogger(__name__)


class MyTaxPrepOfficeClient:
    def __init__(self):
        self.base_url = settings.MYTAXPREPOFFICE_BASE_URL.rstrip("/")
        self.api_key = settings.MYTAXPREPOFFICE_API_KEY

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}"
        response = requests.get(url, headers=self._headers(), params=params or {})
        response.raise_for_status()
        return response.json()

    def get_returns_summary(self, tax_year=None):
        params = {}
        if tax_year:
            params["tax_year"] = tax_year
        return self._get("returns/summary", params)

    def get_clients(self, page=1):
        return self._get("clients", {"page": page})

    def get_return_counts_by_type(self, tax_year=None):
        params = {}
        if tax_year:
            params["tax_year"] = tax_year
        return self._get("returns/counts", params)


def sync_tax_prep_data(tax_year=None):
    if not settings.MYTAXPREPOFFICE_API_KEY:
        logger.info("MyTaxPrepOffice not configured, skipping")
        return 0

    client = MyTaxPrepOfficeClient()
    today = date.today()
    if not tax_year:
        tax_year = today.year

    try:
        summary = client.get_returns_summary(tax_year)
    except Exception as e:
        logger.error(f"Failed to fetch MyTaxPrepOffice data: {e}")
        return 0

    count = 0

    with get_session() as session:
        returns_data = summary.get("summary", {})

        record = OperationalData(
            source="mytaxprepoffice",
            data_type="returns_summary",
            reference_date=today,
            amount=returns_data.get("total_revenue", 0),
            quantity=returns_data.get("total_returns", 0),
            metadata={
                "tax_year": tax_year,
                "total_returns": returns_data.get("total_returns", 0),
                "individual_returns": returns_data.get("individual_returns", 0),
                "business_returns": returns_data.get("business_returns", 0),
                "amended_returns": returns_data.get("amended_returns", 0),
                "avg_fee": returns_data.get("avg_fee", 0),
                "total_revenue": returns_data.get("total_revenue", 0),
            },
            synced_at=datetime.now(timezone.utc),
        )
        session.add(record)
        count += 1

        try:
            counts = client.get_return_counts_by_type(tax_year)
            for return_type, type_count in counts.get("counts", {}).items():
                record = OperationalData(
                    source="mytaxprepoffice",
                    data_type=f"return_type_{return_type}",
                    reference_date=today,
                    quantity=type_count,
                    metadata={"tax_year": tax_year, "return_type": return_type},
                    synced_at=datetime.now(timezone.utc),
                )
                session.add(record)
                count += 1
        except Exception as e:
            logger.warning(f"Could not fetch return type breakdown: {e}")

    logger.info(f"Synced {count} MyTaxPrepOffice records for tax year {tax_year}")
    return count
