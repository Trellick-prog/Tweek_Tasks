#!/usr/bin/env python3
"""
dedup_tasks.py - Find and delete duplicate tasks on specific dates.
"""

import json
import urllib.request
import urllib.parse
from datetime import date, timedelta
from collections import defaultdict

import os

DRY_RUN = False  # set True to preview deletions without executing

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


def fetch_tasks(token, date_from, date_to):
    url = (
        f"https://tweek.so/api/v1/tasks"
        f"?calendarId={CALENDAR_ID}"
        f"&dateFrom={date_from}&dateTo={date_to}"
    )
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    with urllib.request.urlopen(req) as r:
        return json.loads(r.read()).get("data", [])


def delete_task(token, task_id):
    req = urllib.request.Request(
        f"https://tweek.so/api/v1/tasks/{task_id}",
        headers={"Authorization": f"Bearer {token}"},
        method="DELETE",
    )
    try:
        with urllib.request.urlopen(req) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code


def main():
    today    = date.today()
    year_end = date(today.year, 12, 31)

    print("Fetching token...")
    token = get_token()

    print(f"Fetching tasks {today} → {year_end}...")
    tasks = fetch_tasks(token, today.isoformat(), year_end.isoformat())

    # Group by (date, normalized text)
    groups = defaultdict(list)
    for t in tasks:
        key = (t.get("date", ""), t.get("text", "").lower().strip())
        groups[key].append(t)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        print("No duplicates found.")
        return

    print(f"\nFound {len(duplicates)} duplicate group(s):")
    for (d, text), group in sorted(duplicates.items()):
        print(f"  {d}  '{text}'  ×{len(group)}  — keeping id={group[0]['id']}, deleting {len(group)-1}")

    if DRY_RUN:
        print("\nDRY_RUN=True — not deleting anything.")
        return

    print("\nDeleting extras...")
    for (d, text), group in sorted(duplicates.items()):
        for task in group[1:]:  # keep first, delete rest
            status = delete_task(token, task["id"])
            print(f"  DELETE {d} '{text}' id={task['id']}  →  {status}")


if __name__ == "__main__":
    main()
