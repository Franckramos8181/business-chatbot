# QuickBooks Online Setup

## Prerequisites

1. A QuickBooks Online account (sandbox or production)
2. An Intuit Developer account at https://developer.intuit.com

## Create a QuickBooks App

1. Go to https://developer.intuit.com/app/developer/myapps
2. Click "Create an app"
3. Select "QuickBooks Online and Payments"
4. Name your app (e.g., "Business Chatbot")
5. Under "Development Settings" > "Keys & OAuth":
   - Note your **Client ID** and **Client Secret**
   - Add redirect URI: `http://localhost:8080/callback`
6. Under "Scopes", ensure "Accounting" is selected

## Configure Environment

Add your credentials to `.env`:

```
QBO_CLIENT_ID=your_client_id_here
QBO_CLIENT_SECRET=your_client_secret_here
QBO_REDIRECT_URI=http://localhost:8080/callback
QBO_ENVIRONMENT=sandbox
```

For production, change `QBO_ENVIRONMENT` to `production`.

## Authorize the App

Run the one-time setup script:

```bash
python scripts/qb_auth_setup.py
```

This will:
1. Open your browser to the Intuit authorization page
2. After you authorize, catch the callback on localhost:8080
3. Exchange the authorization code for access and refresh tokens
4. Store the tokens in the database

## Token Lifecycle

- **Access tokens** expire after 1 hour and are automatically refreshed
- **Refresh tokens** expire after 100 days but are renewed on each use
- The nightly sync job keeps tokens alive automatically
- If the refresh token expires (app unused for 100+ days), re-run `qb_auth_setup.py`

## Running a Sync

Manual sync (pulls last 2 years of data):
```bash
python scripts/run_sync.py
```

Sync a specific date range:
```bash
python scripts/run_sync.py 2024-01-01 2024-12-31
```

## Sandbox Testing

Intuit provides sandbox companies with sample data at https://developer.intuit.com/app/developer/sandbox. Use these for development and testing before connecting to your production QuickBooks account.
