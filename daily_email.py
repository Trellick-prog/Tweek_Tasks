#!/usr/bin/env python3
"""
daily_email.py - Fetch tweek.so tasks and send a daily HTML email summary.
Covers today + next 7 days.

Config: set environment variables or edit the CONFIG section below.
"""

import json
import smtplib
import ssl
import urllib.request
import urllib.parse
from datetime import date, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ── CONFIG ────────────────────────────────────────────────────────────────────
import os

REFRESH_TOKEN  = os.getenv("TWEEK_REFRESH_TOKEN", "AMf-vBzuRDQQQ02eHNDHQCUrSSfpQnHvdEi3YVY46AUVfTrZQx61K2BHgoGX42EaYQpFuXDq_WmLdRFHDLHKNLk6VDqwtlz2_wQdPpS7DlZhkRSOf5CpOzEC9gAFKeWyxYckIFIdsF6UNaiWjeujsFTaunhfd4JF72Ee8y41R3cutz-In_x28FUh0UV8MSo0nM4kUsLAviyp8yC6IEZDFPLmYcxpWlL16YiqXUZushBoWwFmdibyAfLz7FQFz90YMH00VCQe2ipditsUxaK4-_gWJ6P5o3yd5zevDna8LuQpwawA9TJn3zzVFbKdRFtbqUyYeh1rrBC_sVvds6j0_k2K4gk4xhYgWftwdLocd0EE1AdBhKQ8QMEUCMislg9ge8tXmhOmewzuNdFAh9lCniTGRCCzesgJPVcpWtU8gBj2sslkSNyhsuOZ-QUZyoM4yA7_xx1gmtAU")
FIREBASE_KEY   = os.getenv("TWEEK_FIREBASE_KEY", "AIzaSyDtjavFfRE1wci9XTbzBneJYo7QgL4HP1E")
CALENDAR_ID    = os.getenv("TWEEK_CALENDAR_ID",  "foMWcabECsbyDSl59vtC")

GMAIL_USER     = os.getenv("GMAIL_USER",     "htrenear7@gmail.com")
GMAIL_APP_PASS = os.getenv("GMAIL_APP_PASS", "")   # set this — never commit your app password
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


def build_html(tasks_by_date, today):
    day_names = {
        today: "Today",
        today + timedelta(1): "Tomorrow",
    }

    sections = ""
    for d in sorted(tasks_by_date):
        tasks = tasks_by_date[d]
        incomplete = [t for t in tasks if not t.get("done")]
        done       = [t for t in tasks if t.get("done")]

        label = day_names.get(d, d.strftime("%A"))
        date_str = d.strftime("%-d %B")
        is_today = d == today

        header_bg = "#4F46E5" if is_today else "#6B7280"
        header_style = f"background:{header_bg};color:#fff;padding:10px 16px;border-radius:8px 8px 0 0;margin-top:24px;"

        rows = ""
        for t in incomplete:
            rows += f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0f0f0;">○ {t["text"]}</td></tr>'
        for t in done:
            rows += f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0f0f0;color:#9CA3AF;text-decoration:line-through;">✓ {t["text"]}</td></tr>'

        if not rows:
            rows = '<tr><td style="padding:8px 16px;color:#9CA3AF;font-style:italic;">No tasks</td></tr>'

        count_str = f"{len(incomplete)} remaining" if incomplete else "all done ✓"

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

    total_incomplete = sum(
        len([t for t in v if not t.get("done")]) for v in tasks_by_date.values()
    )

    return f"""
    <html><body style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;background:#F9FAFB;padding:24px;color:#111827;">
      <div style="max-width:600px;margin:0 auto;">
        <h2 style="margin-bottom:4px;">📋 Your week ahead</h2>
        <p style="color:#6B7280;margin-top:0;">{today.strftime("%A, %-d %B %Y")} &middot; {total_incomplete} tasks remaining this week</p>
        {sections}
        <p style="color:#9CA3AF;font-size:12px;margin-top:32px;">Sent by daily_email.py · tweek.so</p>
      </div>
    </body></html>
    """


def send_email(html):
    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"📋 Tasks – {date.today().strftime('%-d %b')}"
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

    print(f"Fetching tasks {today} → {end_date}...")
    token = get_token()
    tasks = fetch_tasks(token, today.isoformat(), end_date.isoformat())

    # Group by date
    tasks_by_date = {}
    for t in tasks:
        d = date.fromisoformat(t["date"]) if t.get("date") else None
        if d:
            tasks_by_date.setdefault(d, []).append(t)

    # Ensure every day in range appears
    for i in range(8):
        d = today + timedelta(i)
        tasks_by_date.setdefault(d, [])

    html = build_html(tasks_by_date, today)
    send_email(html)
    print("Email sent.")


if __name__ == "__main__":
    main()
