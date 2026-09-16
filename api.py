"""Thin Travelpayouts Data API client.

Always https (the docs still show http), always an explicit currency, always
gzip, and every response is persisted verbatim before anyone parses it.
"""

import gzip
import json
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone

import config

BASE = "https://api.travelpayouts.com"
UA = "faredrop/0.1 (personal fare tracker)"


class ApiError(RuntimeError):
    pass


def now_iso():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _fetch(url, timeout=30):
    req = urllib.request.Request(url, headers={
        "Accept-Encoding": "gzip, deflate",
        "User-Agent": UA,
    })
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        if resp.headers.get("Content-Encoding") == "gzip":
            raw = gzip.decompress(raw)
        return resp.status, raw.decode("utf-8", errors="replace")


def get(path, params=None, conn=None, need_token=True, retries=3):
    """Call an endpoint. Returns (parsed_json, fetched_at).

    Persists the raw body to `raw_response` when a connection is supplied.
    """
    params = dict(params or {})
    if need_token:
        if not config.TOKEN:
            raise ApiError(
                "TRAVELPAYOUTS_TOKEN is not set.\n"
                "  Sign up at https://www.travelpayouts.com/developers/api\n"
                "  then: export TRAVELPAYOUTS_TOKEN=your_token_here"
            )
        params["token"] = config.TOKEN
        params.setdefault("currency", config.CURRENCY)

    url = f"{BASE}{path}?" + urllib.parse.urlencode(params)

    last = None
    for attempt in range(retries):
        try:
            status, body = _fetch(url)
            break
        except Exception as exc:              # noqa: BLE001 - retry anything transient
            last = exc
            if attempt == retries - 1:
                raise ApiError(f"{path} failed after {retries} tries: {exc}") from exc
            time.sleep(2 ** attempt)
    else:                                     # pragma: no cover
        raise ApiError(str(last))

    fetched_at = now_iso()
    if conn is not None:
        from db import save_raw
        save_raw(conn, path, params, status, fetched_at, body)

    try:
        payload = json.loads(body)
    except json.JSONDecodeError as exc:
        raise ApiError(f"{path} returned non-JSON: {body[:200]}") from exc

    if isinstance(payload, dict) and payload.get("success") is False:
        raise ApiError(f"{path} error: {payload.get('error')}")
    return payload, fetched_at


# --- reference data (no token required) --------------------------------

def reference(name):
    """airports | airlines | cities | countries"""
    status, body = _fetch(f"{BASE}/data/{name}.json")
    return json.loads(body)
