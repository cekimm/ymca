import datetime as dt
import requests
import pandas as pd

# ---- config you got from your admin ----
BASE = "https://<your-volunteermatters-host>/api/v3"
AUTH = ("<API_KEY>", "<API_SECRET>")          # Basic Auth
HDRS = {"X-VM-Customer-Code": "<YOUR_CODE>"}  # required header

# ---- date window: Jan 1, 2025 -> first day of month being reported ----
report_month = dt.date(2025, 8, 1)   # example: August report
start_date   = dt.date(2025, 1, 1)
# endDate must be the **first day of the next month**
next_month = (report_month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
end_date = next_month  # e.g., 2025-09-01

params = {
    "startDate": start_date.isoformat(),
    "endDate":   end_date.isoformat(),
    "page": 1,
    "pageSize": 1000
}

rows = []
while True:
    r = requests.get(f"{BASE}/volunteer-history", headers=HDRS, auth=AUTH, params=params, timeout=60)
    r.raise_for_status()
    data = r.json()
    # Adjust field names to your API's shape
    items = data.get("items") or data.get("results") or data
    if not items:
        break
    rows.extend(items)

    # pagination handling: adapt to your API (examples below)
    if data.get("hasNextPage"):
        params["page"] += 1
    elif data.get("nextPage"):
        params["page"] = data["nextPage"]
    else:
        break

df = pd.DataFrame(rows)
# Optional: select/rename the columns you need
# df = df[["volunteerName","project","hours","startDate","endDate", ...]]

# Save to Excel for your dashboard pipeline
out = f"VolunteerHistory_{start_date:%Y-%m}_to_{(end_date - dt.timedelta(days=1)):%Y-%m}.xlsx"
df.to_excel(out, index=False)
print(f"Saved: {out}  |  rows: {len(df)}")
