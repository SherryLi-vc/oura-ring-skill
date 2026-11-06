"""Shared OAuth, configuration, and HTTP helpers for the Oura skill."""
import json
import os
import re
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

BASE_URL = "https://api.ouraring.com"
TOKEN_URL = BASE_URL + "/oauth/token"
USER_AGENT = "oura-ring-skill/0.2"
TIMEOUT = 30
KEYS = ("OURA_ACCESS_TOKEN", "OURA_REFRESH_TOKEN", "OURA_CLIENT_ID", "OURA_CLIENT_SECRET",
        "OURA_REDIRECT_URI", "OURA_SCOPES")


def env_path():
    return Path(os.environ.get("OURA_ENV_FILE") or Path((os.environ.get("XDG_CONFIG_HOME") or "~/.config")).expanduser() / "oura" / "oura.env").expanduser()


def parse_env_file(path=None):
    values = {}
    path = Path(path or env_path())
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if m:
            value = m.group(2)
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1]
            values[m.group(1)] = value
    return values


def config():
    file_values = parse_env_file()
    return {key: os.environ[key] if os.environ.get(key) is not None else file_values.get(key, "") for key in KEYS}


def set_values(updates, path=None):
    path = Path(path or env_path())
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    try:
        os.chmod(path.parent, 0o700)
    except OSError:
        pass
    old = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen = set()
    out = []
    for line in old:
        m = re.match(r"^(\s*(?:export\s+)?)([A-Za-z_][A-Za-z0-9_]*)(\s*=).*$", line)
        if m and m.group(2) in updates:
            key = m.group(2)
            out.append(m.group(1) + key + m.group(3) + sh_quote(str(updates[key])))
            seen.add(key)
        else:
            out.append(line)
    for key, value in updates.items():
        if key not in seen:
            out.append(f"{key}={sh_quote(str(value))}")
    fd, name = tempfile.mkstemp(prefix=".oura-", dir=str(path.parent))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(out) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def sh_quote(value):
    return "'" + value.replace("'", "'\"'\"'") + "'"


def masked(value):
    return "set" if value else "not set"


def request(url, data=None, headers=None, method=None, timeout=TIMEOUT, opener=None):
    merged = {"User-Agent": USER_AGENT}
    if headers:
        merged.update(headers)
    req = urllib.request.Request(url, data=data, headers=merged, method=method)
    try:
        open_fn = opener or urllib.request.urlopen
        with open_fn(req, timeout=timeout) as response:
            body = response.read()
            return json.loads(body.decode("utf-8")), response.headers
    except urllib.error.HTTPError as exc:
        # Do not print response bodies: providers and proxies can echo credentials.
        exc.read()
        raise APIError(exc.code, "request rejected", exc.headers) from None
    except urllib.error.URLError as exc:
        raise RuntimeError("Network request failed: " + str(getattr(exc, "reason", "connection error"))) from None


class APIError(RuntimeError):
    def __init__(self, status, message, headers=None):
        self.status = status
        self.headers = headers or {}
        super().__init__(f"HTTP {status}: request rejected")


def token_request(fields, dry_run=False):
    data = urllib.parse.urlencode(fields).encode("utf-8")
    if dry_run:
        masked_fields = {k: ("[redacted]" if k in ("client_secret", "code", "code_verifier", "refresh_token") else v) for k, v in fields.items()}
        return f"POST {TOKEN_URL}\nContent-Type: application/x-www-form-urlencoded\n" + urllib.parse.urlencode(masked_fields)
    return request(TOKEN_URL, data=data, headers={"Content-Type": "application/x-www-form-urlencoded"}, method="POST")[0]
