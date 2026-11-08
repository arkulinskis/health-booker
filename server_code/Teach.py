"""Teachers: my classes across studios, sub requests (ask, cover, withdraw) and a pay statement.

Subs are automatic: when a teacher at the same studio covers a request, the class moves to them at once,
the owner and the original teacher get a message, and booked students are told who's teaching.
Pay = base per class + per_head for each student above pay_after (so nobody teaches for $0).
"""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

from . import common as C
from . import Model as Mo
from .Manage import pay_for, attended


def _my_staff(me):
    return [s for s in app_tables.staff.search(user=me) if s["active"] is not False and s["studio"] is not None]


@anvil.server.callable(require_user=True)
def teach_home(start_iso=None, end_iso=None):
    me = C.require_user()
    rows = _my_staff(me)
    if not rows:
        return {"teaching": False, "studios": [], "upcoming": [], "open_subs": [], "my_subs": [], "pay": {"lines": [], "total": 0}}
    now = C.now()
    staff, studios, rooms = (C.by_id(app_tables.staff.search()), C.by_id(app_tables.studios.search()), C.by_id(app_tables.rooms.search()))
    upcoming = []
    for st in rows:
        for c in app_tables.classes.search(teacher=st, start=q.between(now - dt.timedelta(hours=2), now + dt.timedelta(days=14))):
            if c["status"] == "scheduled":
                d = Mo.class_dict(c, staff, studios, rooms)
                d["first_timers"] = len([b for b in app_tables.bookings.search(klass=c) if b["first_visit"] and b["status"] in Mo.TAKES_MAT])
                upcoming.append(d)
    upcoming.sort(key=lambda d: d["start"])
    my_ids = set(st.get_id() for st in rows)
    studio_rows = [st["studio"] for st in rows]
    open_subs, my_subs = [], []
    for s in studio_rows:
        for x in app_tables.subs.search(studio=s):
            k = x["klass"]
            if k is None or C.aware(k["start"]) < now - dt.timedelta(days=7):
                continue
            d = _sub(x, staff, studios, rooms)
            if x["from_staff"] is not None and x["from_staff"].get_id() in my_ids:
                my_subs.append(d)
            elif x["status"] == "open" and C.aware(k["start"]) > now:
                open_subs.append(d)
    start = C.parse_iso(start_iso) or now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    end = C.parse_iso(end_iso) or start + dt.timedelta(days=31)
    lines: list = []
    for st in rows:
        for c in app_tables.classes.search(teacher=st, start=q.between(start, min(end, now))):
            if c["status"] != "scheduled":
                continue
            n = attended(c)
            lines.append({"id": c.get_id(), "title": c["title"], "start": C.iso(c["start"]), "studio": st["studio"]["name"],
                          "heads": n, "pay": pay_for(st, n), "base": st["pay_base"] or 0, "per_head": st["pay_per_head"] or 0,
                          "after": st["pay_after"] or 0})
    lines.sort(key=lambda x: x["start"])
    revs = []
    for st in rows:
        revs += [r for r in app_tables.reviews.search(teacher=st) if not r["hidden"]]
    revs.sort(key=lambda r: C.aware(r["created"]), reverse=True)
    return {"teaching": True,
            "studios": [{"slug": st["studio"]["slug"], "name": st["studio"]["name"], "role": st["role"], "accent": st["studio"]["accent"],
                         "pay_base": st["pay_base"] or 0, "pay_per_head": st["pay_per_head"] or 0, "pay_after": st["pay_after"] or 0} for st in rows],
            "upcoming": upcoming, "open_subs": open_subs, "my_subs": my_subs,
            "pay": {"lines": lines, "total": sum(x["pay"] for x in lines), "heads": sum(x["heads"] for x in lines),
                    "from": C.iso(start), "to": C.iso(end)},
            "reviews": [{"stars": r["stars"], "text": r["text"] or "", "class": r["klass"]["title"] if r["klass"] else "",
                         "created": C.iso(r["created"])} for r in revs[:6]],
            "rating": round(sum(r["stars"] for r in revs) / len(revs), 2) if revs else 0, "rating_n": len(revs)}


def _sub(x, staff=None, studios=None, rooms=None):
    k = x["klass"]
    f = x["from_staff"]
    fb = x["filled_by"]
    return {"id": x.get_id(), "status": x["status"], "reason": x["reason"] or "", "created": C.iso(x["created"]),
            "from": f["name"] if f else "", "filled_by": fb["name"] if fb else "",
            "class": Mo.class_dict(k, staff, studios, rooms) if k else None}


def _teacher_of(c, me):
    t = c["teacher"]
    return t if (t is not None and t["user"] == me and t["active"] is not False) else None


@anvil.server.callable(require_user=True)
def request_sub(class_id, reason=""):
    me = C.require_user()
    c = C.row_by_id(app_tables.classes, class_id)
    if c is None:
        return C.fail("That class doesn't exist.")
    t = _teacher_of(c, me)
    if t is None:
        return C.fail("You can only ask for a sub for your own classes.")
    if C.aware(c["start"]) < C.now():
        return C.fail("That class has already started.")
    if any(x["status"] == "open" for x in app_tables.subs.search(klass=c)):
        return C.fail("There's already an open sub request for this class.")
    reason = C.text(reason, 200)
    app_tables.subs.add_row(klass=c, studio=c["studio"], from_staff=t, reason=reason, status="open", filled_by=None,
                            created=C.now(), filled_at=None, is_demo=False)
    for other in app_tables.staff.search(studio=c["studio"], teaches=True):
        if other != t and other["active"] is not False and other["user"] is not None:
            C.notify(other["user"], c["studio"], "sub", "Can you cover %s?" % c["title"],
                     "%s asked for a sub%s. Open Teach to cover it." % (t["name"], (": " + reason) if reason else ""), "#teach")
    return C.ok()


@anvil.server.callable(require_user=True)
def withdraw_sub(sub_id):
    me = C.require_user()
    x = C.row_by_id(app_tables.subs, sub_id)
    if x is None or x["from_staff"] is None or x["from_staff"]["user"] != me:
        return C.fail("That isn't your sub request.")
    if x["status"] != "open":
        return C.fail("This request was already covered.")
    x["status"] = "withdrawn"
    return C.ok()


@anvil.server.callable(require_user=True)
def cover_sub(sub_id):
    me = C.require_user()
    x = C.row_by_id(app_tables.subs, sub_id)
    if x is None or x["status"] != "open":
        return C.fail("Someone already covered this class. Thank you anyway!")
    c = x["klass"]
    mine = [s for s in app_tables.staff.search(studio=x["studio"], user=me) if s["active"] is not False and s["teaches"]]
    if not mine:
        return C.fail("Only teachers at this studio can cover its classes.")
    t = mine[0]
    if x["from_staff"] == t:
        return C.fail("You asked for this sub yourself.")
    if C.aware(c["start"]) < C.now():
        return C.fail("That class has already started.")
    x.update(status="filled", filled_by=t, filled_at=C.now())
    if c["orig_teacher"] is None:
        c["orig_teacher"] = x["from_staff"]
    c["teacher"] = t
    s = c["studio"]
    if x["from_staff"]["user"] is not None:
        C.notify(x["from_staff"]["user"], s, "sub", "%s is covering %s" % (t["name"], c["title"]), "Enjoy the time off.", "#teach")
    owner = s["owner"]
    if owner is not None and owner != me:
        C.notify(owner, s, "sub", "Sub sorted: %s" % c["title"], "%s covers for %s." % (t["name"], x["from_staff"]["name"]), "")
    for b in app_tables.bookings.search(klass=c):
        if b["status"] in ("booked", "waitlist"):
            C.notify(b["user"], s, "sub", "%s will teach %s" % (t["name"], c["title"]),
                     "%s is away, so %s is teaching this one. Your booking stays the same." % (x["from_staff"]["name"], t["name"]),
                     "#class/" + c.get_id())
    return C.ok()
