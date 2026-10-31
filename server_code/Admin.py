"""Admin page callables: overview, users (make admin, disable), demo data. Admins only.
Feedback admin calls live in Feedback.py."""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables
import anvil.tables.query as q

from . import common as C
from . import DemoData, Feedback


@anvil.server.callable(require_user=True)
def admin_overview():
    C.require_admin()
    return {"users": len([u for u in app_tables.users.search() if not u["is_demo"]]),
            "admins": len(app_tables.users.search(is_admin=True)),
            "feedback_new": Feedback.new_count(),
            "studios": len(app_tables.studios.search(status="live")),
            "studios_review": len(app_tables.studios.search(status="review")),
            "bookings_week": len(app_tables.bookings.search(created=q.greater_than(C.now() - dt.timedelta(days=7)))),
            "classes_week": len(app_tables.classes.search(start=q.between(C.now(), C.now() + dt.timedelta(days=7)))),
            "demo": {"state": DemoData.state(), "counts": DemoData.counts()}}


def _user(u):
    return {"id": u.get_id(), "email": u["email"], "name": C.name_of(u), "is_admin": C.is_admin(u),
            "enabled": u["enabled"] is not False, "joined": C.iso(u["signed_up"]), "last_seen": C.iso(u["last_seen"])}


@anvil.server.callable(require_user=True)
def list_users(query=None):
    C.require_admin()
    query = C.text(query, 80).lower()
    rows = [u for u in app_tables.users.search(tables.order_by("signed_up", ascending=False)) if not u["is_demo"]]
    if query:
        rows = [u for u in rows if query in (u["email"] or "").lower() or query in (u["display_name"] or "").lower()]
    return {"users": [_user(u) for u in rows[:200]], "total": len(rows)}


@anvil.server.callable(require_user=True)
def set_admin(user_id, flag):
    me = C.require_admin()
    u = C.row_by_id(app_tables.users, user_id)
    if u is None:
        return C.fail("That account no longer exists.")
    if u == me and not flag:
        return C.fail("You can't remove your own admin rights.")
    u["is_admin"] = bool(flag)
    return C.ok(user=_user(u))


@anvil.server.callable(require_user=True)
def set_enabled(user_id, flag):
    me = C.require_admin()
    u = C.row_by_id(app_tables.users, user_id)
    if u is None:
        return C.fail("That account no longer exists.")
    if u == me:
        return C.fail("You can't disable your own account.")
    u["enabled"] = bool(flag)
    return C.ok(user=_user(u))


@anvil.server.callable(require_user=True)
def demo_load():
    C.require_admin()
    DemoData.load()
    return C.ok(demo={"state": DemoData.state(), "counts": DemoData.counts()})


@anvil.server.callable(require_user=True)
def demo_remove():
    C.require_admin()
    DemoData.remove()
    return C.ok(demo={"state": DemoData.state(), "counts": DemoData.counts()})


# ----------------------------------------------------------------------------------------------- studios

@anvil.server.callable(require_user=True)
def admin_studios():
    C.require_admin()
    out = []
    for s in app_tables.studios.search(tables.order_by("created", ascending=False)):
        owner = s["owner"]
        out.append({"slug": s["slug"], "name": s["name"], "status": s["status"], "featured": bool(s["featured"]),
                    "neighbourhood": s["neighbourhood"] or "", "owner": C.name_of(owner) if owner else "",
                    "owner_email": owner["email"] if owner else "", "created": C.iso(s["created"]), "demo": bool(s["is_demo"]),
                    "classes": len(app_tables.classes.search(studio=s, start=q.greater_than(C.now()))),
                    "rating": s["rating"] or 0, "accent": s["accent"] or "sage", "tagline": s["tagline"] or ""})
    return {"studios": out}


@anvil.server.callable(require_user=True)
def admin_set_studio(slug, status=None, featured=None):
    """Publish a studio (review -> live), pause it, or feature it at the top of Discover."""
    C.require_admin()
    s = app_tables.studios.get(slug=slug) if isinstance(slug, str) else None
    if s is None:
        return C.fail("That studio doesn't exist.")
    if status is not None:
        if status not in ("live", "review", "paused"):
            return C.fail("Unknown status.")
        was = s["status"]
        s["status"] = status
        if status == "live" and was != "live" and s["owner"] is not None:
            C.notify(s["owner"], s, "studio", "%s is live!" % s["name"],
                     "Your studio is now on Health Booker. Share your page and welcome your first students.", "#studio/" + s["slug"])
    if featured is not None:
        s["featured"] = bool(featured)
    return C.ok()
