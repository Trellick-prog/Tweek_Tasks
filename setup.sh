#!/bin/bash
# setup.sh - Run this once on the Pi to install dependencies and set up the cron job.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
CRON_TIME="${CRON_TIME:-0 7 * * *}"  # default: 7am daily, override with CRON_TIME env var

echo "=== Tweek Daily Email Setup ==="

# Install Python dependency
echo "Installing icalendar..."
pip3 install icalendar --quiet

# Check .env exists
if [ ! -f "$SCRIPT_DIR/.env" ]; then
  echo ""
  echo "ERROR: .env file not found."
  echo "Run: cp .env.example .env && nano .env"
  exit 1
fi

# Add cron job (skip if already exists)
CRON_JOB="$CRON_TIME cd $SCRIPT_DIR && python3 daily_email.py >> $SCRIPT_DIR/email.log 2>&1"

if crontab -l 2>/dev/null | grep -q "daily_email.py"; then
  echo "Cron job already exists — skipping."
else
  (crontab -l 2>/dev/null; echo "$CRON_JOB") | crontab -
  echo "Cron job added: $CRON_TIME"
fi

echo ""
echo "Done! Test it now with: python3 $SCRIPT_DIR/daily_email.py"
