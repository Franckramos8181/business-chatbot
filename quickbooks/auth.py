import logging
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import requests

from config.settings import settings
from db.connection import get_session
from db.models import ApiToken

logger = logging.getLogger(__name__)

AUTH_BASE_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

SCOPES = "com.intuit.quickbooks.accounting"


def get_authorization_url(state="random_state"):
    params = {
        "client_id": settings.QBO_CLIENT_ID,
        "response_type": "code",
        "scope": SCOPES,
        "redirect_uri": settings.QBO_REDIRECT_URI,
        "state": state,
    }
    return f"{AUTH_BASE_URL}?{urlencode(params)}"


def exchange_code_for_tokens(auth_code, realm_id):
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "authorization_code",
            "code": auth_code,
            "redirect_uri": settings.QBO_REDIRECT_URI,
        },
        auth=(settings.QBO_CLIENT_ID, settings.QBO_CLIENT_SECRET),
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    token_data = response.json()

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    with get_session() as session:
        existing = session.query(ApiToken).filter_by(provider="quickbooks").first()
        if existing:
            existing.access_token = token_data["access_token"]
            existing.refresh_token = token_data["refresh_token"]
            existing.expires_at = expires_at
            existing.realm_id = realm_id
            existing.updated_at = datetime.now(timezone.utc)
        else:
            token = ApiToken(
                provider="quickbooks",
                access_token=token_data["access_token"],
                refresh_token=token_data["refresh_token"],
                expires_at=expires_at,
                realm_id=realm_id,
            )
            session.add(token)

    logger.info("QuickBooks tokens stored successfully")
    return token_data


def _refresh_token(token_record):
    response = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "refresh_token",
            "refresh_token": token_record.refresh_token,
        },
        auth=(settings.QBO_CLIENT_ID, settings.QBO_CLIENT_SECRET),
        headers={"Accept": "application/json"},
    )
    response.raise_for_status()
    token_data = response.json()

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=token_data["expires_in"])

    with get_session() as session:
        record = session.query(ApiToken).filter_by(provider="quickbooks").first()
        record.access_token = token_data["access_token"]
        record.refresh_token = token_data["refresh_token"]
        record.expires_at = expires_at
        record.updated_at = datetime.now(timezone.utc)

    logger.info("QuickBooks token refreshed")
    return token_data["access_token"]


def get_valid_token():
    with get_session() as session:
        token_record = session.query(ApiToken).filter_by(provider="quickbooks").first()
        if not token_record:
            raise RuntimeError("No QuickBooks token found. Run qb_auth_setup.py first.")

        buffer = timedelta(minutes=5)
        if token_record.expires_at and token_record.expires_at - buffer <= datetime.now(timezone.utc):
            logger.info("Token expiring soon, refreshing...")
            return _refresh_token(token_record)

        return token_record.access_token


def get_realm_id():
    with get_session() as session:
        token_record = session.query(ApiToken).filter_by(provider="quickbooks").first()
        if not token_record:
            raise RuntimeError("No QuickBooks token found. Run qb_auth_setup.py first.")
        return token_record.realm_id or settings.QBO_REALM_ID
