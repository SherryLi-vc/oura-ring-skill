#!/usr/bin/env python3
"""Fetch Oura Cloud data with automatic one-time token refresh."""
import argparse
import datetime as dt
import json
import os
import sys
import time
from zoneinfo import ZoneInfo
import urllib.parse

from oura_common import APIError, BASE_URL, config, request, set_values
from oura_auth import credentials

ENDPOINTS = {"daily_sleep": "daily_sleep", "daily_activity": "daily_activity", "daily_readiness": "daily_readiness", "daily_spo2": "daily_spo2", "heartrate": "heartrate"}


def ranges(args, now=None):
    tz = ZoneInfo(args.tz) if args.tz else dt.datetime.now().astimezone().tzinfo
    today = (now or dt.datetime.now(tz)).astimezone(tz).date()
    end = dt.date.fromisoformat(args.end) if args.end else today
    start = dt.date.fromisoformat(args.start) if args.start else end - dt.timedelta(days=args.days - 1)
    if start > end: raise ValueError("--start must not be after --end")
    return start, end, tz


def endpoint_url(name, start, end, tz):
    if name == "heartrate":
        start_dt = dt.datetime.combine(start, dt.time.min, tzinfo=tz).isoformat()
        end_dt = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=tz).isoformat()
        params = {"start_datetime": start_dt, "end_datetime": end_dt}
    else:
        params = {"start_date": start.isoformat(), "end_date": end.isoformat()}
    return BASE_URL + "/v2/usercollection/" + ENDPOINTS[name] + "?" + urllib.parse.urlencode(params)


def get_pages(url, token, fetch=request):
    rows = []; next_url = url
    while next_url:
        payload, headers = fetch(next_url, headers={"Authorization": "Bearer " + token})
        rows.extend(payload.get("data", []))
        token_value = payload.get("next_token")
        if token_value:
            sep = "&" if "?" in url else "?"
            next_url = url + sep + urllib.parse.urlencode({"next_token": token_value})
        else: next_url = None
    return rows


def fetch_with_refresh(url, values, dry_run=False):
    token = values.get("OURA_ACCESS_TOKEN", "")
    if not token:
        raise SystemExit("OURA_ACCESS_TOKEN is not set. Run setup in README.md: python3 scripts/oura_auth.py authorize")
    if dry_run: return []
    try: return get_pages(url, token)
    except APIError as exc:
        if exc.status == 429:
            try: delay = min(60, max(0, int(exc.headers.get("Retry-After", "0"))))
            except (TypeError, ValueError): delay = 0
            time.sleep(delay)
            return get_pages(url, token)
        if exc.status != 401 or not all(values.get(k) for k in ("OURA_REFRESH_TOKEN", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET")): raise
        from oura_common import token_request
        refreshed = token_request({"grant_type": "refresh_token", "refresh_token": values["OURA_REFRESH_TOKEN"], "client_id": values["OURA_CLIENT_ID"], "client_secret": values["OURA_CLIENT_SECRET"]})
        set_values({"OURA_ACCESS_TOKEN": refreshed["access_token"], "OURA_REFRESH_TOKEN": refreshed["refresh_token"]})
        values["OURA_ACCESS_TOKEN"] = refreshed["access_token"]
        values["OURA_REFRESH_TOKEN"] = refreshed["refresh_token"]
        if "OURA_REFRESH_TOKEN" in os.environ or "OURA_ACCESS_TOKEN" in os.environ:
            print("Warning: refreshed tokens were saved to the env file; update or unset the token environment variables because they override the file.", file=sys.stderr)
        return get_pages(url, refreshed["access_token"])


def summarize(name, rows):
    if name == "daily_sleep": field, label = "score", "sleep"
    elif name == "daily_readiness": field, label = "score", "readiness"
    elif name == "daily_activity": field, label = "score", "activity"
    elif name == "daily_spo2": field, label = "spo2_percentage", "SpO2"
    else: field, label = "bpm", "HR"
    daily = {}
    for row in rows:
        day = row.get("day") or row.get("timestamp", "")[:10] or "unknown"
        vals = row.get(field)
        if vals is None and name == "daily_activity": vals = row.get("steps")
        if isinstance(vals, dict): vals = vals.get("average") or vals.get("percentage")
        if isinstance(vals, (int, float)): daily.setdefault(day, []).append(vals)
    for day, vals in sorted(daily.items()):
        if name == "heartrate": value = f"min {min(vals):g}, avg {sum(vals)/len(vals):.1f}, max {max(vals):g} bpm"
        elif name == "daily_activity":
            steps = next((r.get("steps") for r in rows if r.get("day") == day), None)
            value = f"score {sum(vals)/len(vals):g}" + (f", {steps} steps" if steps is not None else "")
        elif name == "daily_spo2": value = f"average {sum(vals)/len(vals):.1f}%"
        else: value = f"{label} score {sum(vals)/len(vals):g}"
        print(f"{day}: {value}")


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("collection", choices=list(ENDPOINTS) + ["all"])
    p.add_argument("--start"); p.add_argument("--end"); p.add_argument("--days", type=int, default=7)
    p.add_argument("--tz", help="IANA timezone name")
    out = p.add_mutually_exclusive_group(); out.add_argument("--json", action="store_true"); out.add_argument("--summary", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()
    if args.days < 1: p.error("--days must be positive")
    try: start, end, tz = ranges(args)
    except (ValueError, KeyError) as exc: p.error(str(exc))
    values = config()
    names = list(ENDPOINTS) if args.collection == "all" else [args.collection]
    results = {}
    for name in names:
        url = endpoint_url(name, start, end, tz)
        if args.dry_run: print(url); continue
        try: results[name] = fetch_with_refresh(url, values)
        except APIError as exc:
            if exc.status == 403: raise SystemExit(str(exc) + " (check granted scopes and Oura membership)")
            if exc.status == 429: raise SystemExit(str(exc) + " (rate limited; retry later)")
            raise SystemExit(str(exc))
        except RuntimeError as exc: raise SystemExit(str(exc))
    if args.dry_run: return
    if args.summary:
        for name, rows in results.items():
            if args.collection == "all": print(f"== {name} ==")
            if not rows: print("no data")
            else: summarize(name, rows)
    else:
        output = results if args.collection == "all" else results[args.collection]
        print(json.dumps(output, indent=2, ensure_ascii=False))

if __name__ == "__main__": main()
