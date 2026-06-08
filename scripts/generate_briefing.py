#!/usr/bin/env python3
"""Generates briefing/index.html from Airtable + weather data."""

import json
import os
import urllib.request
import urllib.parse
from datetime import datetime, timezone, timedelta

AIRTABLE_TOKEN = os.environ["AIRTABLE_TOKEN"]
BASE_ID = "appIHyTJk70t2mG3p"
CMM_ACCOUNT_ID = "recJiDT42I3sWPI7p"
DGC_ACCOUNT_ID = "recBhstEFiwJ0fA9M"

EET = timezone(timedelta(hours=3))
now = datetime.now(EET)
today_str = now.strftime("%Y-%m-%d")

DAYS_GR = ["Δευτέρα","Τρίτη","Τετάρτη","Πέμπτη","Παρασκευή","Σάββατο","Κυριακή"]
MONTHS_GR = ["Ιανουαρίου","Φεβρουαρίου","Μαρτίου","Απριλίου","Μαΐου","Ιουνίου",
             "Ιουλίου","Αυγούστου","Σεπτεμβρίου","Οκτωβρίου","Νοεμβρίου","Δεκεμβρίου"]

day_name = DAYS_GR[now.weekday()]
date_label = f"{now.day} {MONTHS_GR[now.month-1]} {now.year}"


def at_get(table_id, params):
    qs = urllib.parse.urlencode(params, doseq=True)
    req = urllib.request.Request(
        f"https://api.airtable.com/v0/{BASE_ID}/{table_id}?{qs}",
        headers={"Authorization": f"Bearer {AIRTABLE_TOKEN}"}
    )
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r).get("records", [])


def fetch_weather():
    try:
        req = urllib.request.Request(
            "https://wttr.in/Akrata,Greece?format=j1",
            headers={"User-Agent": "CMM-Briefing/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.load(r)
        current = data["current_condition"][0]
        temp = current["temp_C"]
        feels = current["FeelsLikeC"]
        desc = current["weatherDesc"][0]["value"]
        wind_kmph = current["windspeedKmph"]
        humidity = current["humidity"]
        # Beach verdict
        temp_n = int(temp)
        wind_n = int(wind_kmph)
        if temp_n >= 27 and wind_n < 20:
            verdict = ("🟢 Beach Day", "#27ae60")
        elif temp_n >= 22 and wind_n < 30:
            verdict = ("🟡 Maybe", "#f39c12")
        else:
            verdict = ("🔴 Skip", "#c0392b")
        return {
            "temp": temp, "feels": feels, "desc": desc,
            "wind": wind_kmph, "humidity": humidity,
            "verdict": verdict[0], "verdict_color": verdict[1]
        }
    except Exception:
        return None


def fetch_projects():
    records = at_get("tblWFC88Q9a3Egx89", {
        "filterByFormula": "OR({Status}='Active Live',{Status}='Planning')",
        "fields[]": ["Project_Name", "Status", "End_Date", "Account"],
        "sort[0][field]": "End_Date",
        "sort[0][direction]": "asc",
        "maxRecords": 25
    })
    return records


def fetch_tasks():
    records = at_get("tblMqUxBOH6nznSzj", {
        "filterByFormula": f"AND(NOT(OR({{Status}}='Complete',{{Status}}='Canceled')),{{End_Date}}<='{{today}}')"
            .replace("{today}", today_str),
        "fields[]": ["Name", "Status", "End_Date", "Record_Type"],
        "sort[0][field]": "End_Date",
        "sort[0][direction]": "asc",
        "maxRecords": 30
    })
    return records


def status_badge(status):
    colors = {
        "Active Live": ("#27ae60", "#fff"),
        "Planning": ("#2980b9", "#fff"),
        "WIP": ("#e67e22", "#fff"),
        "Under Review": ("#8e44ad", "#fff"),
        "Pending Brief": ("#7f8c8d", "#fff"),
        "Awaiting Revision": ("#c0392b", "#fff"),
    }
    bg, fg = colors.get(status, ("#bdc3c7", "#2c3e50"))
    return f'<span style="background:{bg};color:{fg};padding:2px 8px;border-radius:3px;font-size:11px;font-weight:600;">{status}</span>'


def fmt_date(iso):
    if not iso:
        return "—"
    try:
        d = datetime.fromisoformat(iso.replace("Z","+00:00"))
        delta = (d.date() - now.date()).days
        label = d.strftime("%d/%m")
        if delta < 0:
            return f'<span style="color:#c0392b;font-weight:700;">{label} ▲{abs(delta)}d</span>'
        elif delta == 0:
            return f'<span style="color:#e67e22;font-weight:700;">Σήμερα</span>'
        else:
            return label
    except Exception:
        return iso[:10]


def build_html(weather, projects, tasks):
    overdue_count = sum(1 for r in tasks if r.get("fields", {}).get("End_Date", "") < today_str)

    # Stats bar
    stats = f"""
    <div style="background:#C0392B;color:#fff;padding:10px 24px;display:flex;gap:24px;align-items:center;flex-wrap:wrap;font-size:13px;">
      <span>📋 <strong>{len(projects)}</strong> Active Projects</span>
      <span>⚠️ <strong>{overdue_count}</strong> Overdue Tasks</span>
      <span style="margin-left:auto;opacity:0.8;">{day_name}, {date_label}</span>
    </div>"""

    # Weather section
    if weather:
        verdict_style = f"background:{weather['verdict_color']};color:#fff;padding:3px 12px;border-radius:20px;font-weight:700;font-size:13px;"
        weather_html = f"""
    <div class="section">
      <div class="section-title">01 — Καιρός Ακράτας</div>
      <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
        <div style="font-size:32px;font-weight:700;">{weather['temp']}°C</div>
        <div style="color:#666;">
          <div>{weather['desc']}</div>
          <div style="font-size:12px;">Feels {weather['feels']}°C · Wind {weather['wind']} km/h · Humidity {weather['humidity']}%</div>
        </div>
        <div style="margin-left:auto;"><span style="{verdict_style}">{weather['verdict']}</span></div>
      </div>
    </div>"""
    else:
        weather_html = '<div class="section"><div class="section-title">01 — Καιρός Ακράτας</div><p style="color:#999;">Δεν ήταν δυνατή η λήψη δεδομένων.</p></div>'

    # Projects section
    if projects:
        rows = ""
        for r in projects:
            f = r.get("fields", {})
            rows += f"""<tr>
              <td style="padding:8px 12px;">{f.get('Project_Name','—')}</td>
              <td style="padding:8px 12px;">{status_badge(f.get('Status','?'))}</td>
              <td style="padding:8px 12px;text-align:right;">{fmt_date(f.get('End_Date',''))}</td>
            </tr>"""
        projects_html = f"""
    <div class="section">
      <div class="section-title">02 — Active Projects</div>
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="border-bottom:2px solid #eee;font-size:11px;color:#999;text-transform:uppercase;">
          <th style="padding:6px 12px;text-align:left;">Project</th>
          <th style="padding:6px 12px;text-align:left;">Status</th>
          <th style="padding:6px 12px;text-align:right;">End Date</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""
    else:
        projects_html = '<div class="section"><div class="section-title">02 — Active Projects</div><p style="color:#999;">Κανένα active project.</p></div>'

    # Tasks section
    if tasks:
        rows = ""
        for r in tasks:
            f = r.get("fields", {})
            rows += f"""<tr style="border-bottom:1px solid #f5f5f5;">
              <td style="padding:7px 12px;font-size:13px;">{f.get('Name','—')[:70]}</td>
              <td style="padding:7px 12px;">{status_badge(f.get('Status','?'))}</td>
              <td style="padding:7px 12px;font-size:12px;text-align:right;">{fmt_date(f.get('End_Date',''))}</td>
            </tr>"""
        tasks_html = f"""
    <div class="section">
      <div class="section-title">03 — Tasks Due & Overdue</div>
      <table style="width:100%;border-collapse:collapse;">
        <thead><tr style="border-bottom:2px solid #eee;font-size:11px;color:#999;text-transform:uppercase;">
          <th style="padding:6px 12px;text-align:left;">Task</th>
          <th style="padding:6px 12px;text-align:left;">Status</th>
          <th style="padding:6px 12px;text-align:right;">Due</th>
        </tr></thead>
        <tbody>{rows}</tbody>
      </table>
    </div>"""
    else:
        tasks_html = '<div class="section"><div class="section-title">03 — Tasks Due & Overdue</div><p style="color:#4caf50;font-weight:600;">✓ Κανένα overdue task.</p></div>'

    footer_links = """
    <div style="background:#f8f8f8;border-top:1px solid #eee;padding:14px 24px;font-size:12px;color:#999;display:flex;gap:20px;flex-wrap:wrap;">
      <a href="https://airtable.com/appIHyTJk70t2mG3p/tblWFC88Q9a3Egx89" style="color:#C0392B;text-decoration:none;">→ Projects Board</a>
      <a href="https://airtable.com/appIHyTJk70t2mG3p/tblMqUxBOH6nznSzj" style="color:#C0392B;text-decoration:none;">→ Tasks Board</a>
      <span style="margin-left:auto;">Generated {now_str}</span>
    </div>""".replace("{now_str}", now.strftime("%d/%m/%Y %H:%M EET"))

    return f"""<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1.0">
  <title>CMM Briefing — {date_label}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, sans-serif; background: #f0f0f0; }}
    .card {{ max-width: 720px; margin: 20px auto; background: #fff; border-radius: 6px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,.08); }}
    .header {{ background: #1a1a1a; color: #fff; padding: 18px 24px; }}
    .header h1 {{ font-size: 18px; font-weight: 700; letter-spacing: -.3px; }}
    .header p {{ font-size: 12px; color: #888; margin-top: 3px; }}
    .section {{ padding: 20px 24px; border-bottom: 1px solid #f0f0f0; }}
    .section:last-of-type {{ border-bottom: none; }}
    .section-title {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; color: #C0392B; margin-bottom: 12px; }}
    table tr:hover {{ background: #fafafa; }}
    @media (max-width: 600px) {{ .card {{ margin: 0; border-radius: 0; }} }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">
      <h1>☀️ CMM Morning Briefing</h1>
      <p>{day_name}, {date_label}</p>
    </div>
    {stats}
    {weather_html}
    {projects_html}
    {tasks_html}
    {footer_links}
  </div>
</body>
</html>"""


if __name__ == "__main__":
    print("Fetching weather...")
    weather = fetch_weather()
    print("Fetching projects...")
    projects = fetch_projects()
    print(f"  → {len(projects)} active projects")
    print("Fetching tasks...")
    tasks = fetch_tasks()
    print(f"  → {len(tasks)} due/overdue tasks")

    html = build_html(weather, projects, tasks)

    os.makedirs("briefing", exist_ok=True)
    with open("briefing/index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("✓ briefing/index.html written")
