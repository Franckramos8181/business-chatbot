import logging
import sys
from datetime import date

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from config.settings import settings

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def nightly_job():
    logger.info("Starting nightly sync and analysis...")

    try:
        from quickbooks.sync import full_sync
        start = date(date.today().year, 1, 1).isoformat()
        end = date.today().isoformat()
        sync_results = full_sync(start_date=start, end_date=end)
        logger.info(f"Sync complete: {sync_results}")
    except Exception as e:
        logger.error(f"Sync failed: {e}")
        return

    try:
        from analysis.metrics import save_snapshot
        snapshot = save_snapshot()
        logger.info(f"Analysis snapshot saved: revenue={snapshot['summary']['total_revenue']}, profit={snapshot['summary']['net_profit']}")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        return

    try:
        from output.email_report import send_report
        send_report(settings.REPORT_RECIPIENT)
        logger.info("Email report sent")
    except Exception as e:
        logger.warning(f"Email report failed (non-critical): {e}")

    try:
        from output.sheets import export_to_sheet
        export_to_sheet()
        logger.info("Google Sheets updated")
    except Exception as e:
        logger.warning(f"Sheets export failed (non-critical): {e}")

    logger.info("Nightly job complete")


def main():
    if "--now" in sys.argv:
        nightly_job()
        return

    scheduler = BlockingScheduler()
    scheduler.add_job(
        nightly_job,
        CronTrigger(hour=settings.NIGHTLY_SYNC_HOUR, minute=settings.NIGHTLY_SYNC_MINUTE),
        id="nightly_sync",
        name="Nightly QuickBooks sync and analysis",
    )

    logger.info(f"Scheduler started. Nightly job runs at {settings.NIGHTLY_SYNC_HOUR:02d}:{settings.NIGHTLY_SYNC_MINUTE:02d}")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped")


if __name__ == "__main__":
    main()
