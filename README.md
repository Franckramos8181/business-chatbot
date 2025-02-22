# Business Chatbot

Automated financial analysis system that connects to QuickBooks Online, analyzes business performance, and answers plain-English questions through OpenAI.

## Features

- **QuickBooks Online integration** — pulls revenue, expenses, products/services, customers, liabilities, and credit card debt via OAuth 2.0
- **Financial analysis** — calculates product-level margins, net profit, and identifies hidden pricing opportunities
- **Pricing scenarios** — "If I raise tax returns by $5, what's the annual net profit increase?"
- **Forecasting** — projects revenue, expenses, debt paydown, and net profit
- **OpenAI Q&A** — ask business questions in plain English, get answers backed by real data
- **Scheduled syncs** — nightly automated data pulls and analysis
- **Multiple outputs** — chat interface, Google Sheets export, email reports

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API credentials

# Set up the database
psql -U postgres -f db/migrations/001_initial.sql

# Authorize QuickBooks
python scripts/qb_auth_setup.py

# Run initial data sync
python scripts/run_sync.py

# Start the web interface
python -m output.web
```

## Architecture

QuickBooks Online is the financial source of truth. Operational data from EZRentOut, PictaMail, MyTaxPrepOffice, and USPS supplements the financial data with volume, usage, and activity metrics.

```
QuickBooks API → sync → PostgreSQL → analysis engine → OpenAI Q&A
                                                      → Google Sheets
                                                      → email reports
                                                      → web dashboard
```

See `docs/ARCHITECTURE.md` for details.

## Operational Integrations

In addition to QuickBooks (financial source of truth), the system pulls operational data from:

- **EZRentOut** — equipment rental utilization and rates
- **PictaMail** — mailing campaign costs and volumes
- **MyTaxPrepOffice** — tax return counts and types
- **USPS** — shipping and postage costs

These provide context for volume-based analysis and pricing decisions without overriding QuickBooks financial data.

## Example Questions

```
"What's my net profit this year?"
"If I raise tax returns by $5, what's the annual net profit increase?"
"Which products can I raise prices on with the lowest customer impact?"
"What pricing changes get me to $100K annual profit?"
"How long to pay off my credit card debt at $500/month?"
"Show me my top customers by revenue"
"What does my revenue forecast look like for the next 6 months?"
```

## Tech Stack

- Python 3.11+
- PostgreSQL (Supabase compatible)
- QuickBooks Online API (OAuth 2.0)
- OpenAI API (GPT-4 with function calling)
- FastAPI for the web interface
- APScheduler for nightly syncs

## Documentation

- [Architecture Overview](docs/ARCHITECTURE.md)
- [QuickBooks Setup](docs/QUICKBOOKS_SETUP.md)
- [Deployment Guide](docs/DEPLOYMENT.md)
