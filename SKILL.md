---
name: oura-ring
description: >-
  Use when reading the user's Oura Ring health data (daily sleep, activity,
  readiness, heart rate, SpO2) via the Oura Cloud API—especially for
  health-assistant summaries or trend checks.
---
# Oura Ring API

Read the user's Oura Cloud data for health coaching. Health data is for the user only: never post it to Slack/email/X, never put tokens or raw payloads in shared logs, and never send credentials or full responses to other agents unless that agent is the user's health assistant and needs the summary.

Docs: [Authentication](https://cloud.ouraring.com/docs/authentication) · API base `https://api.ouraring.com` · Interactive [v2 docs](https://cloud.ouraring.com/v2/docs)

## Credentials (never print secrets)

**Auth model (as of Dec 2025):** Personal Access Tokens are **deprecated and no longer available for new use**. New integrations must use **OAuth2 authorization code** (PKCE recommended). `OURA_ACCESS_TOKEN` here means an **OAuth2 access token**, not a portal PAT.

OAuth endpoints:
- Authorize: `https://cloud.ouraring.com/oauth/authorize` (alt: `https://developer.ouraring.com/authorize`)
- Token: `https://api.ouraring.com/oauth/token`
- Data calls: `Authorization: Bearer <access_token>`

Resolve credentials in this order; never echo token values in chat, memory, skill files, or agent messages.

1. **Required for data calls:** `OURA_ACCESS_TOKEN` from `process.env.OURA_ACCESS_TOKEN` (bot secret / secret-request).
2. **Shared box file (preferred when env is empty):** if the access token is still missing, load `/home/box/.secrets/oura.env` (mode `600`) with `set -a && source /home/box/.secrets/oura.env && set +a` (or equivalent in Python). That file should hold `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, `OURA_ACCESS_TOKEN`, and `OURA_REFRESH_TOKEN`. Do not copy its contents into chat or logs.
3. **Refresh (required for longevity):** `OURA_REFRESH_TOKEN`, `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET` from the same env or file. Without these, a 401 means full re-OAuth.

**Missing token:** stop. Tell the coordinating agent (do not message the user unless they are in this chat): `OURA_ACCESS_TOKEN is not set. Ask the chief of staff to re-run Oura OAuth2 and restore /home/box/.secrets/oura.env.` Do not invent sample tokens or scrape cookies. Do not tell the user to create a Personal Access Token.

**After refresh:** write the new `access_token` and single-use `refresh_token` back into `/home/box/.secrets/oura.env` (and bot secrets if those are also configured). Never leave the new refresh token only in shell history. Skipping persistence invalidates the next refresh.

Scopes needed for this skill: `daily`, `heartrate`, `spo2` (API scope name may appear as `spo2` / `spo2Daily`). Prefer the minimum scopes.

**Not this skill:** aggregator APIs (e.g. Open Wearables) may use a different header such as `X-Open-Wearables-API-Key`. This skill talks only to `api.ouraring.com` with Bearer.

## Auth header

Every data call:

```http
Authorization: Bearer <OURA_ACCESS_TOKEN>
```

## Refresh access token

When a data call returns **401**, and refresh secrets exist, refresh once then retry the data call once.

`POST https://api.ouraring.com/oauth/token`  
`Content-Type: application/x-www-form-urlencoded`

Body: `grant_type=refresh_token&refresh_token=$OURA_REFRESH_TOKEN&client_id=$OURA_CLIENT_ID&client_secret=$OURA_CLIENT_SECRET`  
(or HTTP Basic with client_id:client_secret instead of those two form fields).

Response includes new `access_token`, `expires_in`, and a **single-use** `refresh_token`. Persist them as above. If refresh secrets are missing or refresh fails, report that re-authorization is required—do not loop.

## Endpoints this skill covers

Date params are `YYYY-MM-DD`. Heart rate uses datetimes (ISO-8601).

| Need | Method | Path | Query |
|------|--------|------|-------|
| Daily sleep scores | GET | `/v2/usercollection/daily_sleep` | `start_date`, `end_date`, optional `next_token` |
| Daily activity | GET | `/v2/usercollection/daily_activity` | same |
| Daily readiness | GET | `/v2/usercollection/daily_readiness` | same |
| Daily SpO2 (Gen3+) | GET | `/v2/usercollection/daily_spo2` | same |
| Heart rate series | GET | `/v2/usercollection/heartrate` | `start_datetime`, `end_datetime`, optional `next_token` |

Follow `next_token` until null when paging. Default a health check to the last 7 days unless the ask names another range. Prefer Asia/Shanghai calendar dates when the user lives there.

Useful related paths (optional, same auth): `/v2/usercollection/sleep` (detailed sleep periods), `/v2/usercollection/personal_info`.

## curl examples

Load credentials first; never paste token values into the command from chat.

```bash
if [ -z "${OURA_ACCESS_TOKEN:-}" ] && [ -f /home/box/.secrets/oura.env ]; then
  set -a && . /home/box/.secrets/oura.env && set +a
fi
: "${OURA_ACCESS_TOKEN:?OURA_ACCESS_TOKEN is not set}"
START=$(date -d '7 days ago' +%F 2>/dev/null || date -v-7d +%F)
END=$(date +%F)

curl -sS -H "Authorization: Bearer ${OURA_ACCESS_TOKEN}" \
  "https://api.ouraring.com/v2/usercollection/daily_sleep?start_date=${START}&end_date=${END}"
```

Same pattern for `daily_activity`, `daily_readiness`, `daily_spo2`, and `heartrate` (`start_datetime` / `end_datetime`).

Refresh (only when all four refresh-related vars are set); **persist the new refresh_token**:

```bash
curl -sS -X POST "https://api.ouraring.com/oauth/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "grant_type=refresh_token&refresh_token=${OURA_REFRESH_TOKEN}&client_id=${OURA_CLIENT_ID}&client_secret=${OURA_CLIENT_SECRET}"
```

## Python example

```python
import os, sys, urllib.parse, urllib.request, json

def load_oura_env(path="/home/box/.secrets/oura.env"):
    if os.environ.get("OURA_ACCESS_TOKEN"):
        return
    if not os.path.isfile(path):
        return
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)

def token():
    load_oura_env()
    t = os.environ.get("OURA_ACCESS_TOKEN")
    if not t:
        sys.exit("OURA_ACCESS_TOKEN is not set. Re-run Oura OAuth2; restore /home/box/.secrets/oura.env or the bot secret.")
    return t

def get(path, params):
    q = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
    req = urllib.request.Request(
        f"https://api.ouraring.com{path}?{q}",
        headers={"Authorization": f"Bearer {token()}"},
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def refresh_if_configured():
    load_oura_env()
    need = ["OURA_REFRESH_TOKEN", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET"]
    if not all(os.environ.get(k) for k in need):
        return None
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": os.environ["OURA_REFRESH_TOKEN"],
        "client_id": os.environ["OURA_CLIENT_ID"],
        "client_secret": os.environ["OURA_CLIENT_SECRET"],
    }).encode()
    req = urllib.request.Request(
        "https://api.ouraring.com/oauth/token",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        return json.load(r)  # persist access_token + refresh_token back to oura.env
```

## Error handling

| HTTP | Meaning | Action |
|------|---------|--------|
| missing env | No token | Clear setup message; stop; ask for OAuth2 re-auth (not PAT) |
| 401 | Expired/revoked/malformed token | Refresh once if configured; else ask for re-auth |
| 403 | Subscription / access forbidden | Report; do not retry blindly |
| 422 | Bad params | Fix dates/datetimes |
| 429 | Rate limit | Back off and retry later |

## Output for health use

Summarize scores and trends for the user (sleep score, readiness, activity, resting HR / HR series highlights, SpO2 average). Cite the date range. Do not dump full JSON unless asked. This skill does not diagnose or prescribe medication.
