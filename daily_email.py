#!/usr/bin/env python3
"""
daily_email.py - Fetch tweek.so tasks + Google Calendar events and send a daily HTML email.
Covers today + next 7 days.

Config: copy .env.example to .env and fill in values, or set environment variables.
"""

import json
import smtplib
import ssl
import urllib.request
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import os

# Load .env file if present
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    for _line in open(_env_path):
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _v = _line.split("=", 1)
            os.environ.setdefault(_k.strip(), _v.strip())

# ── CONFIG ────────────────────────────────────────────────────────────────────
REFRESH_TOKEN  = os.getenv("TWEEK_REFRESH_TOKEN", "")
FIREBASE_KEY   = os.getenv("TWEEK_FIREBASE_KEY",  "AIzaSyDtjavFfRE1wci9XTbzBneJYo7QgL4HP1E")
CALENDAR_ID    = os.getenv("TWEEK_CALENDAR_ID",   "foMWcabECsbyDSl59vtC")

GCAL_URLS      = [v for k, v in sorted(os.environ.items()) if k.startswith("GCAL_ICAL_URL")]

GMAIL_USER     = os.getenv("GMAIL_USER",     "htrenear7@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")
EMAIL_TO       = os.getenv("EMAIL_TO",       "htrenear7@gmail.com")
# ─────────────────────────────────────────────────────────────────────────────


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


def fetch_gcal_events(ical_urls, date_from, date_to):
    """Fetch events from iCal URLs, return dict of date -> list of event strings."""
    try:
        from icalendar import Calendar
    except ImportError:
        print("Warning: icalendar not installed. Run: pip3 install icalendar")
        return {}

    events_by_date = {}

    for url in ical_urls:
        try:
            with urllib.request.urlopen(url, timeout=10) as r:
                cal = Calendar.from_ical(r.read())
        except Exception as e:
            print(f"Warning: could not fetch calendar {url[:60]}...: {e}")
            continue

        for component in cal.walk():
            if component.name != "VEVENT":
                continue

            dtstart = component.get("DTSTART")
            if not dtstart:
                continue

            val = dtstart.dt
            # All-day event (date object) vs timed event (datetime object)
            if isinstance(val, datetime):
                event_date = val.astimezone(timezone.utc).date()
                time_str = val.astimezone().strftime("%-I:%M%p").lower()
            else:
                event_date = val
                time_str = None

            if not (date_from <= event_date <= date_to):
                continue

            summary = str(component.get("SUMMARY", "Untitled"))
            label = f"{time_str} {summary}" if time_str else summary

            events_by_date.setdefault(event_date, []).append(label)

    # Sort events within each day
    for d in events_by_date:
        events_by_date[d].sort()

    return events_by_date


def build_html(tasks_by_date, events_by_date, today):
    day_names = {
        today: "Today",
        today + timedelta(1): "Tomorrow",
    }

    sections = ""
    for d in sorted(tasks_by_date):
        tasks  = tasks_by_date[d]
        events = events_by_date.get(d, [])

        incomplete = [t for t in tasks if not t.get("done")]
        done       = [t for t in tasks if t.get("done")]

        label    = day_names.get(d, d.strftime("%A"))
        date_str = d.strftime("%-d %B")
        is_today = d == today

        header_bg    = "#4F46E5" if is_today else "#6B7280"
        header_style = f"background:{header_bg};color:#fff;padding:10px 16px;border-radius:8px 8px 0 0;margin-top:24px;"

        rows = ""

        # Calendar events
        for e in events:
            rows += f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0f0f0;">🗓 {e}</td></tr>'

        # Divider if both events and tasks
        if events and (incomplete or done):
            rows += '<tr><td style="padding:0;border-bottom:2px solid #e5e7eb;"></td></tr>'

        # Incomplete tasks
        for t in incomplete:
            rows += f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0f0f0;">○ {t["text"]}</td></tr>'

        # Completed tasks
        for t in done:
            rows += f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0f0f0;color:#9CA3AF;text-decoration:line-through;">✓ {t["text"]}</td></tr>'

        if not rows:
            rows = '<tr><td style="padding:8px 16px;color:#9CA3AF;font-style:italic;">Nothing scheduled</td></tr>'

        task_count = f"{len(incomplete)} task{'s' if len(incomplete) != 1 else ''}" if incomplete else "all done ✓"
        event_count = f"{len(events)} event{'s' if len(events) != 1 else ''}" if events else ""
        count_str = " · ".join(filter(None, [event_count, task_count]))

        sections += f"""
        <div style="margin-bottom:4px;">
          <div style="{header_style}">
            <strong>{label}</strong>
            <span style="font-size:13px;opacity:0.85;margin-left:8px;">{date_str} &middot; {count_str}</span>
          </div>
          <table style="width:100%;border-collapse:collapse;background:#fff;border:1px solid #e5e7eb;border-top:none;border-radius:0 0 8px 8px;">
            {rows}
          </table>
        </div>
        """

    total_incomplete = sum(len([t for t in v if not t.get("done")]) for v in tasks_by_date.values())
    total_events     = sum(len(v) for v in events_by_date.values())

    return f"""
    <html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F9FAFB;padding:24px;color:#111827;">
      <div style="max-width:600px;margin:0 auto;">
        <h2 style="margin-bottom:4px;">📋 Your week ahead</h2>
        <p style="color:#6B7280;margin-top:0;">{today.strftime("%A, %-d %B %Y")} &middot; {total_incomplete} tasks &middot; {total_events} events this week</p>
        {sections}
        <p style="color:#9CA3AF;font-size:12px;margin-top:32px;">Sent by daily_email.py · tweek.so + Google Calendar</p>
      </div>
    </body></html>
    """


def send_email(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📋 {date.today().strftime('%-d %b')} – tasks & calendar"
    msg["From"]    = GMAIL_USER
    msg["To"]      = EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    ctx = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, context=ctx) as s:
        s.login(GMAIL_USER, GMAIL_APP_PASS)
        s.sendmail(GMAIL_USER, EMAIL_TO, msg.as_string())


def main():
    today    = date.today()
    end_date = today + timedelta(days=7)

    print(f"Fetching tweek tasks {today} → {end_date}...")
    token = get_token()
    tasks = fetch_tasks(token, today.isoformat(), end_date.isoformat())

    tasks_by_date = {}
    for t in tasks:
        d = date.fromisoformat(t["date"]) if t.get("date") else None
        if d:
            tasks_by_date.setdefault(d, []).append(t)
    for i in range(8):
        tasks_by_date.setdefault(today + timedelta(i), [])

    print(f"Fetching {len(GCAL_URLS)} Google Calendar(s)...")
    events_by_date = fetch_gcal_events(GCAL_URLS, today, end_date)

    html = build_html(tasks_by_date, events_by_date, today)
    send_email(html)
    print("Email sent.")


if __name__ == "__main__":
    main()
