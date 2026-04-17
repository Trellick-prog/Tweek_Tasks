#!/usr/bin/env python3
"""
create_tasks_test.py - Create recurring tasks via tweek.so API.
Set DRY_RUN = True to preview dates without sending.

Add entries to RECURRING_TASKS to schedule more tasks.
weekday: 0=Mon, 1=Tue, 2=Wed, 3=Thu, 4=Fri, 5=Sat, 6=Sun
"""

import json
import urllib.request
import urllib.parse
from datetime import date, timedelta

import os

DRY_RUN = False  # set True to preview only

# ── RECURRING TASKS ───────────────────────────────────────────────────────────
# Schedules (uncomment to re-run next year):
#   haircut          — every 6 weeks, Monday
#   change bedsheets — every 2 weeks, Saturday
RECURRING_TASKS = [
    # {"text": "haircut",         "weekday": 0, "interval_weeks": 6},
    # {"text": "change bedsheets","weekday": 5, "interval_weeks": 2},
]

# ── ONE-OFF TASKS ──────────────────────────────────────────────────────────────
# Comment out after running to avoid duplicates.
ONE_OFF_TASKS = [
    # {"text": "book dentist",     "date": "2026-06-01"},
    # {"text": "book dentist",     "date": "2027-01-05"},
    # {"text": "book car service", "date": "2026-12-15"},
]
# ─────────────────────────────────────────────────────────────────────────────

_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

REFRESH_TOKEN = os.getenv("TWEEK_REFRESH_TOKEN", "")
FIREBASE_KEY  = os.getenv("TWEEK_FIREBASE_KEY",  "AIzaSyDtjavFfRE1wci9XTbzBneJYo7QgL4HP1E")
CALENDAR_ID   = os.getenv("TWEEK_CALENDAR_ID",   "foMWcabECsbyDSl59vtC")


def get_token():
    data = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
    }).encode()
    req = urllib.request.Request(
        f"https://securetoken.googleapis.com/v1/token?key={FIREBASE_KEY}",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read())["id_token"]


def next_weekday(from_date, weekday):
    """Return the next occurrence of weekday (0=Mon…6=Sun) after from_date."""
    days_ahead = (weekday - from_date.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    return from_date + timedelta(days=days_ahead)


def recurring_dates(start, interval_weeks, year_end):
    d = start
    while d <= year_end:
        yield d
        d += timedelta(weeks=interval_weeks)


def create_task(token, task_date, text):
    payload = json.dumps({
        "calendarId": CALENDAR_ID,
        "date": task_date.isoformat(),
        "text": text,
        "done": False,
        "gcal": False,
    }).encode()
    req = urllib.request.Request(
        "https://tweek.so/api/v1/tasks",
        data=payload,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read().decode()
            return r.status, body
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    today    = date.today()
    year_end = date(today.year, 12, 31)

    all_tasks = []
    for task in RECURRING_TASKS:
        first = next_weekday(today, task["weekday"])
        dates = list(recurring_dates(first, task["interval_weeks"], year_end))
        all_tasks.append((task["text"], dates))
        print(f"\n'{task['text']}' — {len(dates)} dates (every {task['interval_weeks']}w on weekday {task['weekday']}):")
        for d in dates:
            print(f"  {d}  {d.strftime('%A, %-d %B %Y')}")

    for task in ONE_OFF_TASKS:
        d = date.fromisoformat(task["date"])
        all_tasks.append((task["text"], [d]))
        print(f"\n'{task['text']}' — one-off: {d.strftime('%A, %-d %B %Y')}")

    if DRY_RUN:
        print("\nDRY_RUN=True — not sending anything.")
        return

    print("\nFetching token...")
    token = get_token()

    for text, dates in all_tasks:
        print(f"\n── {text} ──")
        for d in dates:
            status, body = create_task(token, d, text)
            print(f"  {d}  →  {status}  {body}")


if __name__ == "__main__":
    main()
