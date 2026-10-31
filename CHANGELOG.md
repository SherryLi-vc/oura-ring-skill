# Changelog

All notable changes to this project are documented here.

## [Unreleased]

- Reposition both READMEs and replace Quick start with concise install and authorization steps.
- Remove the duplicate webhooks sentence from the Chinese README.
- Clarify in SKILL.md that the env file is written with mode 600 and should remain private.
- Treat an empty `XDG_CONFIG_HOME` as unset when resolving the default credentials path.
- Replace environment-specific paths and wording with generic skill paths.
- Add OAuth2 authorization, exchange, refresh, and status helper scripts.
- Add paginated data fetcher with summaries, timezone support, and dry-run mode.
- Add offline standard-library self-test.
- Add English and Simplified Chinese setup and install guides.
- Persist refreshed credentials in the active fetch configuration so `all` collections reuse the rotated single-use refresh token.
- Warn when environment token variables override refreshed credentials saved to the env file, and reject pasted redirects without an authorization code.
- Add per-collection summary headers and empty-result messaging; clarify heart-rate scope support, webhook behavior, and unofficial project status in both READMEs.

## [0.1.0] - 2026-10-29

- Initial publish.
