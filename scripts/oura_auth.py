#!/usr/bin/env python3
"""Manual-paste OAuth2 setup for Oura Cloud."""
import argparse
import base64
import getpass
import hashlib
import json
import os
import secrets
import sys
import tempfile
import urllib.parse
from pathlib import Path

from oura_common import APIError, config, env_path, masked, parse_env_file, request, set_values, token_request

AUTH_URL = "https://cloud.ouraring.com/oauth/authorize"


def pkce():
    verifier = secrets.token_urlsafe(64)[:96]
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    return verifier, challenge


def pending_path():
    return env_path().with_name(".oura-pending.json")


def callback_values(raw):
    parsed = urllib.parse.urlparse(raw if ":" in raw else "https://local.invalid/?" + raw)
    params = urllib.parse.parse_qs(parsed.query)
    if not params and "=" not in raw:
        return {"code": raw.strip()}
    return {k: v[0] for k, v in params.items() if v}


def build_authorize(args, values, state, challenge):
    redirect = args.redirect_uri or values.get("OURA_REDIRECT_URI") or ""
    if not redirect:
        raise SystemExit("Set OURA_REDIRECT_URI or pass --redirect-uri (must exactly match a registered URI).")
    client_id = args.client_id or values.get("OURA_CLIENT_ID") or ""
    if not client_id:
        raise SystemExit("Set OURA_CLIENT_ID or pass --client-id.")
    scope = args.scopes or values.get("OURA_SCOPES") or "daily heartrate spo2"
    params = {"response_type": "code", "client_id": client_id, "redirect_uri": redirect,
              "state": state, "scope": scope, "code_challenge": challenge, "code_challenge_method": "S256"}
    return AUTH_URL + "?" + urllib.parse.urlencode(params), redirect


def save_pending(verifier, state, redirect, client_id):
    p = pending_path()
    p.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(p.parent, 0o700)
    fd, name = tempfile.mkstemp(prefix=".oura-", dir=str(p.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"verifier": verifier, "state": state, "redirect_uri": redirect, "client_id": client_id}, f)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, p)
        os.chmod(p, 0o600)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def credentials(args, values):
    cid = args.client_id or values.get("OURA_CLIENT_ID") or ""
    secret = args.client_secret or values.get("OURA_CLIENT_SECRET") or ""
    if not cid:
        cid = input("Client ID: ").strip()
    if not secret:
        secret = getpass.getpass("Client Secret: ").strip()
    if not cid or not secret:
        raise SystemExit("Client ID and Client Secret are required.")
    return cid, secret


def exchange(code, state, pending, args, values):
    if not code:
        raise SystemExit("No authorization code was found in the redirect. Copy the full redirect URL or provide --code.")
    if state != pending["state"]:
        raise SystemExit("State mismatch; authorization was not completed. Run authorize again.")
    cid, secret = credentials(args, values)
    fields = {"grant_type": "authorization_code", "code": code, "redirect_uri": pending["redirect_uri"],
              "client_id": cid, "client_secret": secret, "code_verifier": pending["verifier"]}
    if args.dry_run:
        print(token_request(fields, True)); return
    result = token_request(fields)
    set_values({"OURA_ACCESS_TOKEN": result["access_token"], "OURA_REFRESH_TOKEN": result["refresh_token"],
                "OURA_CLIENT_ID": cid, "OURA_CLIENT_SECRET": secret, "OURA_REDIRECT_URI": pending["redirect_uri"]})
    pending_path().unlink(missing_ok=True)
    print("OAuth tokens saved securely.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("authorize", "exchange", "refresh"):
        p = sub.add_parser(name)
        p.add_argument("--dry-run", action="store_true")
        p.add_argument("--client-id")
        p.add_argument("--client-secret")
        if name == "authorize":
            p.add_argument("--redirect-uri")
            p.add_argument("--scopes")
        if name == "exchange":
            p.add_argument("--code")
            p.add_argument("--redirect-url")
    sub.add_parser("status")
    args = parser.parse_args()
    values = config()
    if args.command == "status":
        path = env_path()
        print("Environment file:", path)
        print("File mode:", oct(path.stat().st_mode & 0o777) if path.exists() else "missing")
        for key in ("OURA_ACCESS_TOKEN", "OURA_REFRESH_TOKEN", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET", "OURA_REDIRECT_URI", "OURA_SCOPES"):
            print(f"{key}: {masked(values.get(key))}")
        return
    if args.command == "authorize":
        verifier, challenge = pkce(); state = secrets.token_urlsafe(32)
        url, redirect = build_authorize(args, values, state, challenge)
        if args.dry_run:
            print("GET " + url); return
        save_pending(verifier, state, redirect, args.client_id or values.get("OURA_CLIENT_ID", ""))
        print("Open this authorization URL, approve access, then paste the full redirect URL (or code):\n" + url)
        raw = input("Redirect URL or code: ").strip(); cb = callback_values(raw)
        if cb.get("error"):
            raise SystemExit("Authorization denied: " + cb["error"])
        pending = json.loads(pending_path().read_text())
        exchange(cb.get("code", ""), cb.get("state", ""), pending, args, values)
    elif args.command == "exchange":
        p = pending_path()
        if not p.exists(): raise SystemExit("No pending authorization; run authorize first.")
        pending = json.loads(p.read_text())
        cb = callback_values(args.redirect_url) if args.redirect_url else {"code": args.code or "", "state": pending["state"]}
        exchange(cb.get("code", ""), cb.get("state", ""), pending, args, values)
    else:
        needed = ("OURA_REFRESH_TOKEN", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET")
        if not all(values.get(k) for k in needed): raise SystemExit("Refresh requires refresh token, client ID, and client secret.")
        fields = {"grant_type": "refresh_token", "refresh_token": values["OURA_REFRESH_TOKEN"], "client_id": values["OURA_CLIENT_ID"], "client_secret": values["OURA_CLIENT_SECRET"]}
        if args.dry_run: print(token_request(fields, True)); return
        result = token_request(fields)
        set_values({"OURA_ACCESS_TOKEN": result["access_token"], "OURA_REFRESH_TOKEN": result["refresh_token"]})
        if "OURA_REFRESH_TOKEN" in os.environ or "OURA_ACCESS_TOKEN" in os.environ:
            print("Warning: refreshed tokens were saved to the env file; update or unset the token environment variables because they override the file.", file=sys.stderr)
        print("OAuth tokens refreshed and saved securely.")

if __name__ == "__main__":
    main()
