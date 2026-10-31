---
name: oura-ring
description: >-
  Read the user’s own Oura Ring data (daily sleep, readiness, activity, SpO2,
  and heart-rate series) from Oura Cloud API v2 with bundled stdlib Python
  scripts, including one-time OAuth2 setup and automatic token refresh. Use
  when the user asks about Oura sleep, readiness, activity, heart rate, SpO2,
  recovery, or trends over a date range.
license: MIT
compatibility: Requires Python 3.9+ (standard library only) and network access to api.ouraring.com and cloud.ouraring.com. One-time OAuth2 setup by the user.
---
# Oura Ring

## Privacy

Health data is for the user only. Never post it to other people, channels, or shared logs. Never echo access tokens, refresh tokens, client secrets, or raw API payloads. Do not invent tokens, scrape cookies, or ask for a personal access token. Summarize only the data needed to answer the user's request.

## Credentials

Personal access tokens were deprecated in December 2025 and are no longer available. Use OAuth2. Credentials resolve per key: environment variables first, then `$OURA_ENV_FILE`, else `${XDG_CONFIG_HOME:-~/.config}/oura/oura.env`. Supported values are `OURA_ACCESS_TOKEN`, `OURA_REFRESH_TOKEN`, `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, optional `OURA_REDIRECT_URI`, and optional `OURA_SCOPES` (default `daily heartrate spo2`). The env file must have mode 600; setup creates its parent directory with mode 700. Status output masks values.

If the access token is missing, stop and tell the user to follow Setup in `README.md`, then run `python3 scripts/oura_auth.py authorize`. On a 401, refresh once when refresh credentials are configured; immediately persist both returned tokens because refresh tokens are single-use. Retry the data request once.

## Fetch data

Run script paths relative to the skill folder. Oura's authentication docs describe the `heartrate` scope as "time series heart rate for Gen 3 users".

Primary path:

```sh
python3 scripts/oura_fetch.py daily_sleep --days 7 --summary
python3 scripts/oura_fetch.py all --start 2026-10-24 --end 2026-10-31 --summary
python3 scripts/oura_fetch.py heartrate --days 3 --tz America/Los_Angeles --json
```

Collections: `daily_sleep`, `daily_activity`, `daily_readiness`, `daily_spo2`, `heartrate`, or `all`. Default date range is the last 7 calendar days in the user's local timezone. Override with `--tz` using an IANA timezone. Daily endpoints use `start_date`, `end_date`, and pagination `next_token`; heart rate uses `start_datetime`, `end_datetime`, and `next_token`. All pages are followed.

| Collection | API path |
|---|---|
| Sleep | `/v2/usercollection/daily_sleep` |
| Activity | `/v2/usercollection/daily_activity` |
| Readiness | `/v2/usercollection/daily_readiness` |
| SpO2 | `/v2/usercollection/daily_spo2` |
| Heart rate | `/v2/usercollection/heartrate` |

## Errors

| Status | Meaning and response |
|---|---|
| Missing token | Stop; direct the user to the README setup and authorize command. |
| 400 / 422 | 400 = query parameter validation error (docs); 422 = validation error (OpenAPI). |
| 401 | Refresh once if configured; otherwise re-authorize. |
| 403 | Check granted scopes and Oura membership. |
| 429 | Honor `Retry-After`; retry once, then stop. |

## Output guidance

Summarize scores and trends, cite the date range, and avoid full JSON unless requested. Health data is not medical advice. Do not diagnose or advise medication; suggest a clinician for concerning values.

## Minimal curl fallback

Use the configurable env file path and keep its permissions private:

```sh
ENV_FILE="${OURA_ENV_FILE:-${XDG_CONFIG_HOME:-$HOME/.config}/oura/oura.env}"
set -a; . "$ENV_FILE"; set +a
curl -sS -H "User-Agent: oura-ring-skill/0.2" \
  -H "Authorization: Bearer ${OURA_ACCESS_TOKEN}" \
  "https://api.ouraring.com/v2/usercollection/daily_sleep?start_date=2026-10-25&end_date=2026-10-31"
```
