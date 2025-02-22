import logging
from datetime import datetime, date, timezone

import requests

from config.settings import settings
from db.connection import get_session
from db.models import OperationalData

logger = logging.getLogger(__name__)


class PictaMailClient:
    def __init__(self):
        self.base_url = settings.PICTAMAIL_BASE_URL.rstrip("/")
        self.api_key = settings.PICTAMAIL_API_KEY

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

    def get_campaigns(self, start_date=None, end_date=None):
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("campaigns", params)

    def get_mailing_stats(self, start_date=None, end_date=None):
        params = {}
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return self._get("stats/mailings", params)


def sync_mailing_data(start_date=None, end_date=None):
    if not settings.PICTAMAIL_API_KEY:
        logger.info("PictaMail not configured, skipping")
        return 0

    client = PictaMailClient()
    today = date.today()

    try:
        campaigns = client.get_campaigns(start_date, end_date)
    except Exception as e:
        logger.error(f"Failed to fetch PictaMail data: {e}")
        return 0

    count = 0

    with get_session() as session:
        for campaign in campaigns.get("campaigns", []):
            record = OperationalData(
                source="pictamail",
                data_type="campaign",
                reference_date=campaign.get("date", today),
                amount=campaign.get("cost", 0),
                quantity=campaign.get("pieces_mailed", 0),
                metadata={
                    "campaign_id": campaign.get("id"),
                    "name": campaign.get("name"),
                    "status": campaign.get("status"),
                    "pieces_mailed": campaign.get("pieces_mailed", 0),
                    "cost": campaign.get("cost", 0),
                    "response_rate": campaign.get("response_rate"),
                },
                synced_at=datetime.now(timezone.utc),
            )
            session.add(record)
            count += 1

    logger.info(f"Synced {count} PictaMail campaign records")
    return count
