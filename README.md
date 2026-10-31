# oura-ring

[![License: MIT](https://img.shields.io/github/license/SherryLi-vc/oura-ring-skill)](./LICENSE)

**English** · [简体中文](./README.zh-CN.md)

<!-- POSITIONING-PLACEHOLDER: tagline + opening paragraph to be written by the repo-description editor. Do not edit by hand. -->
A skill for setting up OAuth2 access to Oura Ring data and fetching personal health summaries.

This is an unofficial community skill, not an official Oura product. Oura is a trademark of its owner.

> Read your Oura Ring data through the Oura Cloud API.

Use this skill to authorize access to your Oura account and fetch sleep, readiness, activity, heart rate, and SpO2 records.

- **OAuth2 setup**: Authorize through Oura with PKCE and securely save credentials locally.
- **Data fetching**: Retrieve daily collections and heart rate with pagination.
- **Compact summaries**: Review per-day scores and trends for a selected range.
- **Privacy first**: Keep health data and credentials on the user's machine.

## Quick start

1. Install into a folder named `oura-ring`.
2. Put your Client ID and Client Secret in `~/.config/oura/oura.env`, or point `OURA_ENV_FILE` to that file.
3. From the skill folder (e.g. `cd ~/.agents/skills/oura-ring`), run `python3 scripts/oura_auth.py authorize` to authorize, then `python3 scripts/oura_fetch.py daily_sleep --days 3 --summary` to verify.

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

## Repository About / Topics (placeholder)
<!-- ABOUT-TOPICS-PLACEHOLDER: to be filled by the repo-description editor -->
