# oura-ring

[![License: MIT](https://img.shields.io/github/license/SherryLi-vc/oura-ring-skill)](./LICENSE)

**English** · [简体中文](./README.zh-CN.md)

> An Agent Skill that lets your AI agent read **your own** Oura Ring data from the official Oura Cloud API v2 and summarize it for you alone.

**What it is:** a portable `SKILL.md` (Agent Skills format) plus standard-library Python scripts for one-time OAuth2 setup and for fetching daily sleep, activity, readiness, SpO2 and heart-rate series.

**Who it's for:** Oura Ring owners who want their AI agent to summarize their own scores and trends over a date range.

**What it isn't:** not medical advice, and not an official Oura product. This is an unofficial community skill; Oura is a trademark of its owner. No tokens or keys ship in this repo.

- **OAuth2 with PKCE**: authorization-code flow with state validation. Oura retired personal access tokens in December 2025.
- **Refresh handled**: refreshes once on a 401 and writes the new single-use refresh token back atomically to a mode-600 file.
- **Your credentials, your path**: environment variables first, then `OURA_ENV_FILE`, else `~/.config/oura/oura.env`.
- **Five collections, every page**: `daily_sleep`, `daily_activity`, `daily_readiness`, `daily_spo2` and `heartrate` (or `all`), following `next_token`.
- **Local-time defaults**: the last 7 calendar days in your time zone, `--tz` to override, plus `--summary`, `--json` and `--dry-run`.
- **Portable and light**: plain `SKILL.md`; Python 3.9+ standard library only.

## Quick start

**1. Install** to the shared user-level path (other hosts: see [Install](#install)):

    git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.agents/skills/oura-ring

**2. Register an Oura app and create the credentials file**: see [Setup](#setup-one-time-oauth2), steps 1–3.

**3. Authorize, then verify:**

    cd ~/.agents/skills/oura-ring
    python3 scripts/oura_auth.py authorize
    python3 scripts/oura_fetch.py daily_sleep --days 3 --summary

## Install

The repository root is the skill folder; clone or copy it into a skills directory and keep the folder name equal to the skill `name` (`oura-ring`). Keep scripts beside `SKILL.md`.

Shared user-level path read by Codex, Cursor, Gemini CLI, and OpenCode:

```sh
git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.agents/skills/oura-ring
```

Claude Code (also read by Cursor and OpenCode):

```sh
git clone https://github.com/SherryLi-vc/oura-ring-skill.git ~/.claude/skills/oura-ring
```

Gemini CLI alternative:

```sh
gemini skills install https://github.com/SherryLi-vc/oura-ring-skill.git
```

Project-level: put the folder under `.agents/skills/oura-ring/` (or `.claude/skills/oura-ring/`) in your repo. Other hosts that load `SKILL.md` folders can use a copy of the whole folder, including sibling files.

| Host | How to invoke |
|---|---|
| All hosts | Auto-load when the skill description matches the request. |
| Claude Code | `/oura-ring` |
| Codex | `$oura-ring` (or `/oura-ring` via the skills list) |
| Cursor | Use the `/` menu. |
| Gemini CLI | Loads through its `activate_skill` flow. |

**Compatibility:** [Agent Skills specification](https://agentskills.io/specification); [Claude Code](https://code.claude.com/docs/en/skills); [OpenAI Codex](https://developers.openai.com/codex/skills); [Cursor](https://cursor.com/docs/context/skills); [Gemini CLI](https://geminicli.com/docs/cli/skills/); [OpenCode](https://opencode.ai/docs/skills/).

## Setup (one-time OAuth2)

1. At [Oura Cloud API applications](https://cloud.ouraring.com/oauth/applications), register an application with a name, website, and redirect URI. Registered redirect URIs are a whitelist and must match exactly. `http://localhost:8080/callback` is reported to work by some users; if the portal rejects it, use an HTTPS URL you control.
2. Copy the Client ID and Client Secret. Keep the secret private. Apps are limited to 10 users until approved by Oura, which is suitable for personal use.
3. Create the credentials file (replace placeholders; do not include angle brackets) and restrict its permissions:

   ```sh
   mkdir -p "${XDG_CONFIG_HOME:-$HOME/.config}/oura"
   chmod 700 "${XDG_CONFIG_HOME:-$HOME/.config}/oura"
   cat > "${XDG_CONFIG_HOME:-$HOME/.config}/oura/oura.env" <<'EOF'
   OURA_CLIENT_ID=your_client_id
   OURA_CLIENT_SECRET=your_client_secret
   OURA_REDIRECT_URI=http://localhost:8080/callback
   OURA_SCOPES="daily heartrate spo2"
   EOF
   chmod 600 "${XDG_CONFIG_HOME:-$HOME/.config}/oura/oura.env"
   ```

   Alternatively set `OURA_ENV_FILE` to another dotenv-style file. Environment variables override the file per key.
4. Choose the `daily`, `heartrate`, and `spo2` scopes on Oura's consent screen. You can also override scopes with `OURA_SCOPES`.
5. Run `python3 scripts/oura_auth.py authorize`. Open the printed URL, approve access, then paste the full redirect URL. If the redirect page fails, copy its address bar URL. The flow uses state validation and PKCE.
6. Verify setup and fetch sample data:

   ```sh
   python3 scripts/oura_auth.py status
   python3 scripts/oura_fetch.py daily_sleep --days 3 --summary
   ```

Access tokens refresh automatically after a 401 when refresh credentials are available. Oura refresh tokens are single-use; the helper immediately saves the replacement token alongside the new access token.
Oura also offers webhooks for ongoing updates; this skill polls on demand and does not need them.

## Fetching data

```sh
python3 scripts/oura_fetch.py daily_sleep --days 7 --summary
python3 scripts/oura_fetch.py all --start 2026-10-24 --end 2026-10-31 --summary
python3 scripts/oura_fetch.py heartrate --days 3 --tz America/Los_Angeles --json
```

Without `--start` and `--end`, the default is the last seven calendar days in the local timezone. Use `--tz` with an IANA timezone to override it. `--dry-run` prints requests without network access. Scopes are `daily heartrate spo2`. Oura's authentication docs describe the `heartrate` scope as "time series heart rate for Gen 3 users".

## Troubleshooting

| Issue | What to check |
|---|---|
| `invalid_request` or redirect mismatch | The redirect URI must exactly match a registered URI; register an HTTPS URI you control if needed. |
| 400 / 422 | 400 = query parameter validation error (docs); 422 = validation error (OpenAPI). |
| 401 | Check token validity; the fetcher refreshes once if configured. Otherwise authorize again. |
| 403 | Check granted scopes and Oura membership. Requests include a non-empty User-Agent. |
| 429 | The fetcher honors `Retry-After` once; retry later if still limited. |
| Missing scope | Re-authorize and grant the needed `daily`, `heartrate`, or `spo2` scope. |
| `access_denied` | Consent was declined; retry authorization and approve the requested scopes. |

## Privacy & safety

Health data is for the user only. Do not post it to other people, channels, or shared logs. Never share tokens or client secrets, and do not paste raw API responses into shared logs. Use OAuth2; personal access tokens were deprecated in December 2025 and are no longer available. Never scrape cookies or invent credentials.

## Not medical advice

This skill summarizes Oura measurements and does not diagnose conditions or recommend medication. Contact a clinician about concerning values.

## Sources

- [Authentication](https://cloud.ouraring.com/docs/authentication)
- [Oura API v2 documentation](https://cloud.ouraring.com/v2/docs) ([OpenAPI](https://cloud.ouraring.com/v2/static/json/openapi-1.43.json))
- [Oura API documentation](https://cloud.ouraring.com/docs/)
- [Error handling](https://cloud.ouraring.com/docs/error-handling)

## License

MIT © 2026 SherryLi-vc
