import logging
import xml.etree.ElementTree as ET
from datetime import datetime, date, timezone

import requests

from config.settings import settings
from db.connection import get_session
from db.models import OperationalData

logger = logging.getLogger(__name__)

USPS_BASE_URL = "https://secure.shippingapis.com/ShippingAPI.dll"


class USPSClient:
    def __init__(self):
        self.user_id = settings.USPS_USERID

    def _request(self, api, xml_payload):
        response = requests.get(USPS_BASE_URL, params={"API": api, "XML": xml_payload})
        response.raise_for_status()
        return ET.fromstring(response.text)

    def get_rate(self, origin_zip, dest_zip, weight_oz, service="PRIORITY"):
        xml = f"""<RateV4Request USERID="{self.user_id}">
            <Revision>2</Revision>
            <Package ID="1">
                <Service>{service}</Service>
                <ZipOrigination>{origin_zip}</ZipOrigination>
                <ZipDestination>{dest_zip}</ZipDestination>
                <Pounds>{weight_oz // 16}</Pounds>
                <Ounces>{weight_oz % 16}</Ounces>
                <Container>VARIABLE</Container>
                <Width></Width>
                <Length></Length>
                <Height></Height>
            </Package>
        </RateV4Request>"""

        root = self._request("RateV4", xml)
        postage = root.find(".//Postage/Rate")
        return float(postage.text) if postage is not None else None

    def track_package(self, tracking_number):
        xml = f"""<TrackRequest USERID="{self.user_id}">
            <TrackID ID="{tracking_number}"></TrackID>
        </TrackRequest>"""

        root = self._request("TrackV2", xml)
        summary = root.find(".//TrackSummary")
        return summary.text if summary is not None else None


def sync_shipping_data(shipping_records=None):
    """Sync shipping cost data. Accepts a list of shipping records
    (typically from an internal system or CSV) since USPS doesn't
    provide a historical shipment API."""

    if not shipping_records:
        logger.info("No shipping records provided, skipping USPS sync")
        return 0

    today = date.today()
    count = 0

    with get_session() as session:
        for record in shipping_records:
            op_data = OperationalData(
                source="usps",
                data_type="shipment",
                reference_date=record.get("date", today),
                amount=record.get("cost", 0),
                quantity=record.get("pieces", 1),
                metadata={
                    "tracking_number": record.get("tracking_number"),
                    "service": record.get("service", ""),
                    "origin_zip": record.get("origin_zip", ""),
                    "dest_zip": record.get("dest_zip", ""),
                    "weight_oz": record.get("weight_oz", 0),
                    "cost": record.get("cost", 0),
                },
                synced_at=datetime.now(timezone.utc),
            )
            session.add(op_data)
            count += 1

    logger.info(f"Synced {count} USPS shipping records")
    return count


def estimate_monthly_shipping_cost(avg_daily_shipments, avg_cost_per_shipment):
    monthly_volume = avg_daily_shipments * 22
    monthly_cost = monthly_volume * avg_cost_per_shipment
    annual_cost = monthly_cost * 12

    return {
        "avg_daily_shipments": avg_daily_shipments,
        "avg_cost_per_shipment": avg_cost_per_shipment,
        "estimated_monthly_volume": monthly_volume,
        "estimated_monthly_cost": round(monthly_cost, 2),
        "estimated_annual_cost": round(annual_cost, 2),
    }
