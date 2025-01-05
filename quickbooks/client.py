import logging
import time

import requests

from config.settings import settings
from quickbooks.auth import get_valid_token, get_realm_id

logger = logging.getLogger(__name__)

SANDBOX_BASE = "https://sandbox-quickbooks.api.intuit.com"
PRODUCTION_BASE = "https://quickbooks.api.intuit.com"

MAX_RESULTS = 1000
MIN_REQUEST_INTERVAL = 0.15


class QuickBooksClient:
    def __init__(self):
        self._last_request_time = 0

    @property
    def base_url(self):
        if settings.QBO_ENVIRONMENT == "production":
            return PRODUCTION_BASE
        return SANDBOX_BASE

    def _get_headers(self):
        token = get_valid_token()
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _throttle(self):
        elapsed = time.time() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            time.sleep(MIN_REQUEST_INTERVAL - elapsed)
        self._last_request_time = time.time()

    def _request(self, method, endpoint, **kwargs):
        self._throttle()
        realm_id = get_realm_id()
        url = f"{self.base_url}/v3/company/{realm_id}/{endpoint}"
        response = requests.request(method, url, headers=self._get_headers(), **kwargs)
        response.raise_for_status()
        return response.json()

    def query(self, entity, where_clause=None, order_by=None):
        all_results = []
        start_position = 1

        while True:
            sql = f"SELECT * FROM {entity}"
            if where_clause:
                sql += f" WHERE {where_clause}"
            if order_by:
                sql += f" ORDERBY {order_by}"
            sql += f" STARTPOSITION {start_position} MAXRESULTS {MAX_RESULTS}"

            data = self._request("GET", "query", params={"query": sql})
            response = data.get("QueryResponse", {})

            entities = response.get(entity, [])
            if not entities:
                break

            all_results.extend(entities)

            if len(entities) < MAX_RESULTS:
                break
            start_position += MAX_RESULTS

        logger.info(f"Queried {len(all_results)} {entity} records")
        return all_results

    def get(self, entity, entity_id):
        data = self._request("GET", f"{entity.lower()}/{entity_id}")
        return data.get(entity, data)

    def get_report(self, report_name, params=None):
        return self._request("GET", f"reports/{report_name}", params=params or {})
