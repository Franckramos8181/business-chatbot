"""Manual trigger for a full QuickBooks data sync."""

import logging
import sys
from datetime import date, timedelta

from quickbooks.sync import full_sync

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def main():
    default_start = (date.today() - timedelta(days=730)).isoformat()
    start_date = sys.argv[1] if len(sys.argv) > 1 else default_start
    end_date = sys.argv[2] if len(sys.argv) > 2 else date.today().isoformat()

    print(f"Running full sync from {start_date} to {end_date}...")
    results = full_sync(start_date=start_date, end_date=end_date)

    print("\nSync results:")
    for entity, count in results.items():
        print(f"  {entity}: {count} records")


if __name__ == "__main__":
    main()
