# Architecture

## Overview

This system automates financial analysis for a multi-service business by pulling data from QuickBooks Online (source of truth) and operational systems, running analysis, and exposing results through an OpenAI-powered Q&A interface.

## Data Flow

```
┌─────────────────┐     ┌─────────────────┐     ┌──────────────┐
│  QuickBooks API  │────>│  sync pipeline  │────>│  PostgreSQL   │
└─────────────────┘     └─────────────────┘     └──────┬───────┘
                                                       │
┌─────────────────┐     ┌─────────────────┐            │
│  EZRentOut       │────>│                 │            │
│  PictaMail       │────>│  integrations   │───────────>│
│  MyTaxPrepOffice │────>│                 │            │
│  USPS            │────>│                 │            │
└─────────────────┘     └─────────────────┘            │
                                                       │
                        ┌─────────────────┐            │
                        │ analysis engine  │<───────────┘
                        │  - metrics       │
                        │  - pricing       │
                        │  - forecasting   │
                        └────────┬────────┘
                                 │
                        ┌────────▼────────┐
                        │ analysis_snapshots│
                        └────────┬────────┘
                                 │
              ┌──────────┬───────┼────────┬──────────┐
              ▼          ▼       ▼        ▼          ▼
         OpenAI Q&A   Sheets   Email   Web UI   Scheduler
```

## Modules

| Module | Responsibility |
|---|---|
| `config/` | Central settings loaded from `.env` |
| `db/` | ORM models, connection management, migrations |
| `quickbooks/` | OAuth 2.0 auth, API client, data sync |
| `integrations/` | EZRentOut, PictaMail, MyTaxPrepOffice, USPS clients |
| `analysis/` | Financial metrics, pricing scenarios, forecasting |
| `ai/` | OpenAI function-calling assistant, prompt templates |
| `output/` | Google Sheets, email reports, FastAPI web interface |
| `scheduler/` | APScheduler nightly sync and analysis job |

## Key Design Decisions

1. **QuickBooks as source of truth** — all financial figures come from QBO. Other integrations provide operational context (volumes, activity) but never override QBO numbers.

2. **Precomputed snapshots** — the nightly job writes an `analysis_snapshots` row with pre-aggregated metrics. The AI assistant reads this for instant answers to common questions, calling live analysis functions only for specific queries.

3. **OpenAI function calling** — the assistant doesn't receive raw financial data in its context. Instead, it calls typed functions (`get_product_metrics`, `run_pricing_scenario`, etc.) that query the database and return structured results.

4. **Raw data preservation** — every synced entity stores the full API response in a `raw_data` JSONB column, allowing debugging and reprocessing without re-fetching from external APIs.

## Database

PostgreSQL with 9 tables. See `db/migrations/001_initial.sql` for the full schema.

Core tables: `customers`, `products_services`, `revenue`, `expenses`, `liabilities`
Analysis: `analysis_snapshots`
Operational: `operational_data`
System: `api_tokens`, `chat_history`
