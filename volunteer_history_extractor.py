import datetime as dt
import requests
import pandas as pd
from requests.auth import HTTPBasicAuth

# ---- CONFIG ----
BASE = "https://api.volunteermatters.io/api/v2"   # from Swagger "Servers"
AUTH = HTTPBasicAuth("62lJN9CLNQbuVag36vFSmDg", "oRBbayCJRE2fdJyqKfs9Axw")
HDRS = {
    "X-VM-Customer-Code": "cincinnatiymca",
    "Accept": "application/json",
}

# ---- Date window: Jan 1, 2025 -> first day of the month AFTER report month ----
report_month = dt.date(2025, 8, 1)   # Example: August 2025
start_date   = dt.date(2025, 1, 1)
end_date     = (report_month.replace(day=28) + dt.timedelta(days=4)).replace(day=1)

params = {
    "startDate": start_date.isoformat(),
    "endDate":   end_date.isoformat(),
    "page": 1,
    "pageSize": 1000
}

rows = []
while True:
    url = f"{BASE}/volunteerHistory"
    r = requests.get(url, headers=HDRS, auth=AUTH, params=params, timeout=60)
    print(f"Requesting: {r.url}")
    print("Status:", r.status_code)
    if not r.ok:
        raise SystemExit(f"❌ {r.status_code} {r.reason}: {r.text}")

    data = r.json()
    items = data.get("items") or data.get("results") or data
    if not items:
        break
    rows.extend(items)

    if data.get("hasNextPage"):
        params["page"] += 1
    elif data.get("nextPage"):
        params["page"] = data["nextPage"]
    else:
        break

# ---- Save to Excel ----
df = pd.DataFrame(rows)
out = f"VolunteerHistory_{start_date:%Y-%m}_to_{(end_date - dt.timedelta(days=1)):%Y-%m}.xlsx"
df.to_excel(out, index=False)
print(f"✅ Saved: {out} | rows: {len(df)}")