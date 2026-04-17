#!/usr/bin/env python3
"""
create_tasks_test.py - Test creating tasks via tweek.so API.
Set DRY_RUN = True to preview dates without sending.
Set TEST_ONLY = True to only send the first task as a sanity check.
"""

import json
import urllib.request
import urllib.parse
from datetime import date, timedelta

import os

DRY_RUN   = False  # set True to preview only
TEST_ONLY = True   # set True to send just the first task

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


def next_monday(from_date):
    """Return the next Monday on or after from_date."""
    days_ahead = (0 - from_date.weekday()) % 7  # 0 = Monday
    if days_ahead == 0:
        days_ahead = 7  # if today is Monday, take next week's
    return from_date + timedelta(days=days_ahead)


def mondays_every_6_weeks(start, year_end):
    """Yield Mondays spaced 6 weeks apart from start through year_end."""
    d = start
    while d <= year_end:
        yield d
        d += timedelta(weeks=6)


def create_task(token, task_date, text):
    payload = json.dumps({
        "calendarId": CALENDAR_ID,
        "date": task_date.isoformat(),
        "text": text,
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
    first    = next_monday(today)
    dates    = list(mondays_every_6_weeks(first, year_end))

    print(f"Today: {today}  |  First Monday: {first}")
    print(f"Dates to create 'haircut' ({len(dates)} total):")
    for d in dates:
        print(f"  {d}  {d.strftime('%A, %-d %B %Y')}")

    if DRY_RUN:
        print("\nDRY_RUN=True — not sending anything.")
        return

    print("\nFetching token...")
    token = get_token()

    targets = dates[:1] if TEST_ONLY else dates

    for d in targets:
        print(f"\nPOSTing task for {d}...", flush=True)
        status, body = create_task(token, d, "haircut")
        print(f"  Status: {status}")
        print(f"  Body:   {body}")

    if TEST_ONLY and len(dates) > 1:
        print(f"\nTEST_ONLY=True — sent 1 of {len(dates)}. Check tweek.so, then set TEST_ONLY=False to send the rest.")


if __name__ == "__main__":
    main()
