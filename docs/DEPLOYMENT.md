# Deployment Guide

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 14+ (or Supabase free tier)
- QuickBooks Online developer account
- OpenAI API key

### Setup

```bash
# Clone the repository
git clone https://github.com/Franckramos8181/business-chatbot.git
cd business-chatbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your credentials

# Create database
createdb business_chatbot
psql -d business_chatbot -f db/migrations/001_initial.sql

# (Optional) Seed with sample data for testing
python scripts/seed_db.py

# Authorize QuickBooks
python scripts/qb_auth_setup.py

# Run initial sync
python scripts/run_sync.py

# Start the web interface
python -m output.web
# Open http://localhost:8000
```

## Nightly Scheduler

### Option A: APScheduler (built-in)

```bash
python -m scheduler.nightly
```

Runs as a long-lived process. Use a process manager to keep it running.

### Option B: Windows Task Scheduler

1. Open Task Scheduler
2. Create Basic Task: "Business Chatbot Nightly Sync"
3. Trigger: Daily at 2:00 AM
4. Action: Start a Program
   - Program: `C:\path\to\venv\Scripts\python.exe`
   - Arguments: `-m scheduler.nightly --now`
   - Start in: `C:\path\to\business-chatbot`

### Option C: Linux cron

```bash
# Edit crontab
crontab -e

# Add nightly sync at 2:00 AM
0 2 * * * cd /path/to/business-chatbot && /path/to/venv/bin/python -m scheduler.nightly --now >> /var/log/business-chatbot.log 2>&1
```

## VPS Deployment

### Using systemd (Linux VPS)

Create `/etc/systemd/system/business-chatbot.service`:

```ini
[Unit]
Description=Business Chatbot Web Interface
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/business-chatbot
ExecStart=/opt/business-chatbot/venv/bin/python -m output.web
Restart=always
EnvironmentFile=/opt/business-chatbot/.env

[Install]
WantedBy=multi-user.target
```

Create `/etc/systemd/system/business-chatbot-scheduler.service`:

```ini
[Unit]
Description=Business Chatbot Nightly Scheduler
After=network.target postgresql.service

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/business-chatbot
ExecStart=/opt/business-chatbot/venv/bin/python -m scheduler.nightly
Restart=always
EnvironmentFile=/opt/business-chatbot/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable business-chatbot business-chatbot-scheduler
sudo systemctl start business-chatbot business-chatbot-scheduler
```

### Recommended VPS providers

- **DigitalOcean**: $6/mo droplet (1 vCPU, 1GB RAM)
- **Hetzner**: $4/mo VPS
- **Railway**: Free tier available, auto-deploys from GitHub

## Supabase Setup

1. Create a free project at https://supabase.com
2. Go to Settings > Database > Connection string
3. Copy the PostgreSQL connection string to your `.env`:
   ```
   DATABASE_URL=postgresql://postgres:[password]@db.[project-ref].supabase.co:5432/postgres
   ```
4. Run the migration via Supabase SQL Editor or psql

## Environment Variables

See `.env.example` for all available configuration options. Required variables:

| Variable | Required | Description |
|---|---|---|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `QBO_CLIENT_ID` | Yes | QuickBooks app client ID |
| `QBO_CLIENT_SECRET` | Yes | QuickBooks app client secret |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `QBO_REALM_ID` | After auth | Set automatically during OAuth |
| `SMTP_USER` | For email | Gmail or SMTP credentials |
| `GOOGLE_SHEETS_CREDS_FILE` | For Sheets | Service account JSON path |

## Monitoring

- Check scheduler logs for sync failures
- QuickBooks token refresh failures will log warnings
- If the refresh token expires (100+ days without sync), re-run `qb_auth_setup.py`

## Costs

| Service | Cost |
|---|---|
| Supabase (DB) | Free tier (500MB) |
| OpenAI API | ~$0.01-0.10 per chat query (GPT-4) |
| VPS (optional) | $4-6/month |
| QuickBooks API | Free (included with QBO subscription) |
| Google Sheets API | Free |
