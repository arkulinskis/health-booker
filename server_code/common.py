"""Shared server helpers: time, permissions, input cleaning, rate limits, app settings.

Every other server module imports this as `from . import common as C`.
Rules every callable follows:
  - check who is calling (C.me() / C.require_user() / C.require_admin()) before touching data
  - return JSON-friendly values only (dicts, lists, str, numbers, bools, None); dates via C.iso()
  - expected problems return C.fail("Message the user can read"); the page shows it
"""
import datetime as dt
import re

import anvil.server
import anvil.users
from anvil.tables import app_tables


def now():
    return dt.datetime.now(dt.timezone.utc)


def iso(v):
    """date/datetime -> ISO string (datetimes in UTC), anything else unchanged."""
    if isinstance(v, dt.datetime):
        if v.tzinfo is None:
            v = v.replace(tzinfo=dt.timezone.utc)
        return v.astimezone(dt.timezone.utc).isoformat()
    if isinstance(v, dt.date):
        return v.isoformat()
    return v


def fail(message):
    return {"ok": False, "error": message}


def ok(**data):
    data["ok"] = True
    return data


def text(value, limit=200, multiline=False):
    """Clean user text: str, trimmed, length-capped; single-line unless multiline."""
    s = "" if value is None else str(value)
    s = s.replace("\r\n", "\n").strip()
    if not multiline:
        s = re.sub(r"\s+", " ", s)
    else:
        s = re.sub(r"\n{3,}", "\n\n", s)
    return s[:limit]


def me():
    return anvil.users.get_user()


def require_user():
    u = anvil.users.get_user()
    if u is None:
        raise anvil.server.PermissionDenied("Please sign in first.")
    return u


def is_admin(user):
    return bool(user is not None and user["is_admin"])


def require_admin():
    u = require_user()
    if not is_admin(u):
        raise anvil.server.PermissionDenied("Only admins can do that.")
    return u


def name_of(user):
    if user is None:
        return "Someone"
    return user["display_name"] or (user["email"] or "Someone").split("@")[0].capitalize()


def row_by_id(table, row_id):
    """get_by_id that returns None for a missing or malformed id (ids come from the browser)."""
    if not isinstance(row_id, str) or not row_id:
        return None
    try:
        return table.get_by_id(row_id)
    except Exception:
        return None


def rate_limited(key, limit, seconds):
    """True if this browser session already did `key` `limit` times in the last `seconds`."""
    stamp = now()
    store = "rate_" + key
    recent = [t for t in (anvil.server.session.get(store) or [])
              if (stamp - dt.datetime.fromisoformat(t)).total_seconds() < seconds]
    if len(recent) >= limit:
        return True
    getattr(anvil.server, "session")[store] = recent + [stamp.isoformat()]
    return False


def get_setting(key, default=None):
    row = app_tables.app_settings.get(key=key)
    return default if row is None else row["value"]


def set_setting(key, value):
    row = app_tables.app_settings.get(key=key)
    if row is None:
        app_tables.app_settings.add_row(key=key, value=value)
    else:
        row["value"] = value


# ----------------------------------------------------------------------------------------------- Health Booker helpers

def parse_iso(value):
    """ISO string from the browser -> aware UTC datetime, or None."""
    if not isinstance(value, str) or not value:
        return None
    try:
        d = dt.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        return None
    if d.tzinfo is None:
        d = d.replace(tzinfo=dt.timezone.utc)
    return d.astimezone(dt.timezone.utc)


def aware(d):
    if d is not None and d.tzinfo is None:
        return d.replace(tzinfo=dt.timezone.utc)
    return d


_EPOCH = dt.datetime(1970, 1, 1, tzinfo=dt.timezone.utc)


def waiver(studio, user):
    """The person's waiver at a studio (the newest if there are several), or None."""
    if studio is None or user is None:
        return None
    rows = list(app_tables.waivers.search(studio=studio, user=user))
    return max(rows, key=lambda r: aware(r["signed"]) or _EPOCH) if rows else None


def slugify(name):
    s = re.sub(r"[^a-z0-9]+", "-", (name or "").lower()).strip("-")
    return s[:40] or "studio"


def num(value, default=0, lo=None, hi=None):
    try:
        v = float(value)
    except (TypeError, ValueError):
        return default
    if v != v:  # NaN
        return default
    if lo is not None:
        v = max(lo, v)
    if hi is not None:
        v = min(hi, v)
    return int(v) if float(v).is_integer() else round(v, 2)


def str_list(value, limit=12, each=40):
    if not isinstance(value, (list, tuple)):
        return []
    out = []
    for v in value:
        t = text(v, each)
        if t and t not in out:
            out.append(t)
    return out[:limit]


def by_id(rows):
    return {r.get_id(): r for r in rows}


def rid(row):
    return row.get_id() if row is not None else None


def first_name(user):
    return name_of(user).split(" ")[0]


def notify(user, studio, kind, title, body="", link=""):
    if user is None:
        return
    app_tables.notices.add_row(user=user, studio=studio, kind=kind, title=text(title, 140),
                               body=text(body, 600, multiline=True), link=link or "", created=now(),
                               read=False, is_demo=bool(user["is_demo"]))
