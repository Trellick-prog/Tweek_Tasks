#!/bin/bash
# tweek_tasks.sh - Fetch tasks from tweek.so for a given date
# Usage: ./tweek_tasks.sh [YYYY-MM-DD]   (defaults to today)

REFRESH_TOKEN="AMf-vBzuRDQQQ02eHNDHQCUrSSfpQnHvdEi3YVY46AUVfTrZQx61K2BHgoGX42EaYQpFuXDq_WmLdRFHDLHKNLk6VDqwtlz2_wQdPpS7DlZhkRSOf5CpOzEC9gAFKeWyxYckIFIdsF6UNaiWjeujsFTaunhfd4JF72Ee8y41R3cutz-In_x28FUh0UV8MSo0nM4kUsLAviyp8yC6IEZDFPLmYcxpWlL16YiqXUZushBoWwFmdibyAfLz7FQFz90YMH00VCQe2ipditsUxaK4-_gWJ6P5o3yd5zevDna8LuQpwawA9TJn3zzVFbKdRFtbqUyYeh1rrBC_sVvds6j0_k2K4gk4xhYgWftwdLocd0EE1AdBhKQ8QMEUCMislg9ge8tXmhOmewzuNdFAh9lCniTGRCCzesgJPVcpWtU8gBj2sslkSNyhsuOZ-QUZyoM4yA7_xx1gmtAU"
FIREBASE_API_KEY="AIzaSyDtjavFfRE1wci9XTbzBneJYo7QgL4HP1E"
CALENDAR_ID="foMWcabECsbyDSl59vtC"
DATE="${1:-$(date +%Y-%m-%d)}"

# Refresh the access token
TOKEN=$(curl -s -X POST \
  "https://securetoken.googleapis.com/v1/token?key=$FIREBASE_API_KEY" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&refresh_token=$REFRESH_TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin).get('id_token',''))")

if [ -z "$TOKEN" ]; then
  echo "Error: Failed to refresh token. You may need to update the REFRESH_TOKEN in this script."
  exit 1
fi

# Fetch tasks for the given date
curl -s "https://tweek.so/api/v1/tasks?calendarId=$CALENDAR_ID&dateFrom=$DATE&dateTo=$DATE" \
  -H "Authorization: Bearer $TOKEN" | python3 -c "
import sys, json
data = json.load(sys.stdin)
tasks = data.get('data', [])
incomplete = [t for t in tasks if not t.get('done')]
done = [t for t in tasks if t.get('done')]
print(f'Tasks for $DATE — {len(incomplete)} incomplete, {len(done)} done\n')
if incomplete:
    print('TODO:')
    for t in incomplete:
        print(f'  ○ {t.get(\"text\",\"\")}')
if done:
    print()
    print('DONE:')
    for t in done:
        print(f'  ✓ {t.get(\"text\",\"\")}')
"
