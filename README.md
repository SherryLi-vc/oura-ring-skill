# oura-ring (Grok Bot / Cursor skill)

Private-ready skill template for reading Oura Ring Cloud API data (daily sleep, activity, readiness, heart rate, SpO2).

## Install

Copy `SKILL.md` into your agent's skills/workflows folder as `oura-ring/SKILL.md`, or import via your bot's skill installer.

## Credentials

**This repository contains no tokens or secrets.**

Configure OAuth2 locally:
- Bot secret / env: `OURA_ACCESS_TOKEN` (and refresh trio)
- Or a local file such as `/home/box/.secrets/oura.env` (mode `600`) with:
  `OURA_CLIENT_ID`, `OURA_CLIENT_SECRET`, `OURA_ACCESS_TOKEN`, `OURA_REFRESH_TOKEN`

Personal Access Tokens are deprecated; use OAuth2 authorization code (PKCE recommended).

## License

MIT
