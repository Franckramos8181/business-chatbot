import logging
from datetime import datetime, date, timezone

import requests

from config.settings import settings
from db.connection import get_session
from db.models import OperationalData

logger = logging.getLogger(__name__)


class EZRentOutClient:
    def __init__(self):
        self.base_url = settings.EZRENTOUT_BASE_URL.rstrip("/")
        self.api_key = settings.EZRENTOUT_API_KEY

    def _headers(self):
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    def _get(self, endpoint, params=None):
        url = f"{self.base_url}/{endpoint}.json"
        response = requests.get(url, headers=self._headers(), params=params or {})
        response.raise_for_status()
        return response.json()

    def get_assets(self, page=1):
        return self._get("assets", {"page": page})

    def get_orders(self, page=1, status="all"):
        return self._get("orders", {"page": page, "status": status})

    def get_asset_utilization(self):
        assets = []
        page = 1
        while True:
            data = self.get_assets(page=page)
            batch = data.get("assets", [])
            if not batch:
                break
            assets.extend(batch)
            page += 1

        utilization = []
        for asset in assets:
            utilization.append({
                "asset_id": asset.get("id"),
                "name": asset.get("name", ""),
                "status": asset.get("status", ""),
                "rental_rate": asset.get("rental_rate"),
                "total_rentals": asset.get("total_orders", 0),
                "is_available": asset.get("status") == "available",
            })

        return utilization


def sync_equipment_data():
    if not settings.EZRENTOUT_API_KEY:
        logger.info("EZRentOut not configured, skipping")
        return 0

    client = EZRentOutClient()

    try:
        utilization = client.get_asset_utilization()
    except Exception as e:
        logger.error(f"Failed to fetch EZRentOut data: {e}")
        return 0

    today = date.today()
    count = 0

    with get_session() as session:
        for asset in utilization:
            record = OperationalData(
                source="ezrentout",
                data_type="equipment_utilization",
                reference_date=today,
                amount=asset.get("rental_rate"),
                quantity=asset.get("total_rentals", 0),
                metadata=asset,
                synced_at=datetime.now(timezone.utc),
            )
            session.add(record)
            count += 1

    logger.info(f"Synced {count} EZRentOut asset records")
    return count
