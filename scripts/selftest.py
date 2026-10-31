"""Offline unit checks for the Oura skill scripts."""
import base64
import hashlib
import json
import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

import oura_auth
import oura_fetch
import oura_common


class SkillTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "oura.env"
        os.environ["OURA_ENV_FILE"] = str(self.path)

    def tearDown(self):
        self.tmp.cleanup()
        os.environ.pop("OURA_ENV_FILE", None)
        for key in oura_common.KEYS:
            os.environ.pop(key, None)

    def test_arg_parsing(self):
        with patch("sys.argv", ["oura_fetch.py", "daily_sleep", "--days", "3", "--dry-run"]):
            with patch("sys.stdout"):
                # Main reaches config and date range but prints only URLs.
                oura_fetch.main()

    def test_timezone_range(self):
        import argparse
        a = argparse.Namespace(tz="America/Los_Angeles", end="2026-10-31", start=None, days=3)
        start, end, tz = oura_fetch.ranges(a)
        self.assertEqual(start.isoformat(), "2026-10-29")
        url = oura_fetch.endpoint_url("heartrate", start, end, tz)
        self.assertIn("-07%3A00", url)

    def test_pkce(self):
        verifier, challenge = oura_auth.pkce()
        self.assertGreaterEqual(len(verifier), 43); self.assertLessEqual(len(verifier), 128)
        self.assertEqual(challenge, base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("="))
        self.assertNotIn("=", challenge)

    def test_authorize_url(self):
        import argparse
        args = argparse.Namespace(redirect_uri="https://example.com/cb", client_id="id", scopes="daily heartrate spo2")
        url, redirect = oura_auth.build_authorize(args, {}, "state", "challenge")
        q = parse_qs(urlparse(url).query)
        self.assertEqual(q["redirect_uri"], [redirect]); self.assertEqual(q["state"], ["state"])
        self.assertEqual(q["code_challenge_method"], ["S256"])

    def test_env_precedence_and_file(self):
        self.path.write_text("OURA_ACCESS_TOKEN=file\nOURA_CLIENT_ID=file-id\n")
        os.chmod(self.path, 0o600); os.environ["OURA_ACCESS_TOKEN"] = "env"
        c = oura_common.config()
        self.assertEqual(c["OURA_ACCESS_TOKEN"], "env"); self.assertEqual(c["OURA_CLIENT_ID"], "file-id")

    def test_atomic_write_mode_and_preserve(self):
        self.path.write_text("# keep me\nOTHER=value\nOURA_ACCESS_TOKEN=old\n")
        oura_common.set_values({"OURA_ACCESS_TOKEN": "new"})
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o600)
        self.assertIn("# keep me", self.path.read_text()); self.assertIn("OTHER=value", self.path.read_text())
        self.assertIn("OURA_ACCESS_TOKEN='new'", self.path.read_text())

    def test_mask(self):
        self.assertEqual(oura_common.masked("secret-token"), "set")
        self.assertNotIn("secret-token", oura_common.masked("secret-token"))

    def test_dry_run_masks(self):
        output = oura_common.token_request({"client_secret": "SECRET", "refresh_token": "REFRESH", "client_id": "id"}, True)
        from urllib.parse import unquote
        decoded = unquote(output)
        self.assertNotIn("SECRET", decoded); self.assertNotIn("REFRESH", decoded); self.assertIn("[redacted]", decoded)

    def test_paging(self):
        replies = iter([({"data": [{"id": 1}], "next_token": "n"}, {}), ({"data": [{"id": 2}], "next_token": None}, {})])
        urls = []
        def fake(url, headers=None): urls.append(url); return next(replies)
        rows = oura_fetch.get_pages("https://api.ouraring.com/x?a=1", "token", fake)
        self.assertEqual(len(rows), 2); self.assertIn("next_token=n", urls[1])

    def test_401_refresh_retry(self):
        from oura_common import APIError
        values = {"OURA_ACCESS_TOKEN": "old", "OURA_REFRESH_TOKEN": "refresh", "OURA_CLIENT_ID": "id", "OURA_CLIENT_SECRET": "secret"}
        calls = []
        def fake_pages(url, token):
            calls.append(token)
            if token == "old": raise APIError(401, "expired")
            return [{"ok": True}]
        with patch.object(oura_fetch, "get_pages", fake_pages), patch.object(oura_common, "token_request", return_value={"access_token": "new", "refresh_token": "next"}), patch.object(oura_fetch, "set_values"):
            self.assertEqual(oura_fetch.fetch_with_refresh("url", values), [{"ok": True}])
        self.assertEqual(calls, ["old", "new"])

    def test_all_style_refresh_updates_shared_credentials(self):
        from oura_common import APIError
        values = {"OURA_ACCESS_TOKEN": "old", "OURA_REFRESH_TOKEN": "spent", "OURA_CLIENT_ID": "id", "OURA_CLIENT_SECRET": "secret"}
        calls = []; refreshes = []
        def fake_pages(url, token):
            calls.append(token)
            if token == "old": raise APIError(401, "expired")
            return [{"ok": True}]
        def fake_refresh(fields):
            refreshes.append(fields["refresh_token"])
            return {"access_token": "new", "refresh_token": "next"}
        with patch.object(oura_fetch, "get_pages", fake_pages), patch.object(oura_common, "token_request", side_effect=fake_refresh), patch.object(oura_fetch, "set_values"):
            self.assertEqual(oura_fetch.fetch_with_refresh("first", values), [{"ok": True}])
            self.assertEqual(oura_fetch.fetch_with_refresh("second", values), [{"ok": True}])
        self.assertEqual(calls, ["old", "new", "new"])
        self.assertEqual(refreshes, ["spent"])
        self.assertEqual(values["OURA_REFRESH_TOKEN"], "next")

if __name__ == "__main__": unittest.main(verbosity=2)
