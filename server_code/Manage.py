"""Studio owners and front desk: today, schedule, rosters + check-in, clients, pricing, team + pay, insights,
reviews, settings, rooms, CSV export, the check-in kiosk.

Every callable starts with _studio_for(slug) / _class_for(id), which checks the caller manages that studio
(owner or desk staff, or a platform admin). Rosters are also open to the studio's teachers.
"""
import csv
import datetime as dt
import io

import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

from . import common as C
from . import Model as Mo
from . import Booking


def _studio_for(slug, me):
    s = Mo.studio_by_slug(slug)
    if s is None or not Mo.can_manage(s, me):
        raise anvil.server.PermissionDenied("Only this studio's owner and front desk can do that.")
    return s


def _class_for(class_id, me, teachers_ok=False):
    c = C.row_by_id(app_tables.classes, class_id)
    if c is None:
        return None
    s = c["studio"]
    if Mo.can_manage(s, me) or (teachers_ok and Mo.is_staff(s, me)):
        return c
    raise anvil.server.PermissionDenied("Only this studio's team can see that.")


def _caches():
    return (C.by_id(app_tables.staff.search()), C.by_id(app_tables.studios.search()), C.by_id(app_tables.rooms.search()))


def _range(start_iso, end_iso, default_days=1):
    start = C.parse_iso(start_iso) or C.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end = C.parse_iso(end_iso) or start + dt.timedelta(days=default_days)
    if end <= start or end - start > dt.timedelta(days=42):
        end = start + dt.timedelta(days=default_days)
    return start, end


@anvil.server.callable(require_user=True)
def manage_list():
    me = C.require_user()
    if C.is_admin(me):
        rows = list(app_tables.studios.search())
        role = {r.get_id(): "admin" for r in rows}
        for st in app_tables.staff.search(user=me):
            if st["studio"] is not None and st["active"] is not False:
                role[st["studio"].get_id()] = st["role"]
    else:
        rows, role = [], {}
        for st in app_tables.staff.search(user=me):
            if st["active"] is not False and st["role"] in ("owner", "desk") and st["studio"] is not None:
                rows.append(st["studio"])
                role[st["studio"].get_id()] = st["role"]
    rows.sort(key=lambda s: (role.get(s.get_id()) == "admin", s["name"]))
    return [{"slug": s["slug"], "name": s["name"], "status": s["status"], "accent": s["accent"] or "sage",
             "role": role.get(s.get_id()), "demo": bool(s["is_demo"])} for s in rows]


@anvil.server.callable(require_user=True)
def manage_day(slug, start_iso=None, end_iso=None):
    """The Today board: classes in the range with fill + rosters' first names, money and to-dos."""
    me = C.require_user()
    s = _studio_for(slug, me)
    start, end = _range(start_iso, end_iso)
    staff, studios, rooms = _caches()
    classes = sorted(app_tables.classes.search(studio=s, start=q.between(start, end)), key=lambda c: C.aware(c["start"]))
    out = []
    for c in classes:
        d = Mo.class_dict(c, staff, studios, rooms)
        bs = [b for b in app_tables.bookings.search(klass=c) if b["status"] in Mo.TAKES_MAT]
        d["checked_in"] = len([b for b in bs if b["status"] == "checked_in"])
        d["first_timers"] = len([b for b in bs if b["first_visit"]])
        out.append(d)
    sold = [p for p in app_tables.passes.search(studio=s, created=q.between(start, end))]
    unpaid = [p for p in app_tables.passes.search(studio=s, paid=False) if p["kind"] != "friend"]
    subs = [x for x in app_tables.subs.search(studio=s, status="open") if x["klass"] and C.aware(x["klass"]["start"]) > C.now()]
    return {"studio": _studio_full(s), "classes": out,
            "sold": {"count": len(sold), "total": sum(p["price"] or 0 for p in sold)},
            "unpaid": [_pass_row(p) for p in sorted(unpaid, key=lambda p: C.aware(p["created"]), reverse=True)[:30]],
            "open_subs": [_sub(x, staff) for x in subs],
            "first_timers": sum(d["first_timers"] for d in out),
            "visits": sum(d["booked"] for d in out), "capacity": sum(d["capacity"] for d in out if d["status"] == "scheduled")}


def _studio_full(s):
    d = Mo.studio_card(s)
    from .Studios import DEFAULT_WAIVER
    d.update(about=s["about"] or "", cancel_hours=Mo.cancel_hours(s), waiver_text=s["waiver_text"] or DEFAULT_WAIVER)
    return d


def _pass_row(p):
    d = Mo.pass_dict(p)
    d["who"] = C.name_of(p["user"])
    d["user_id"] = C.rid(p["user"])
    d["created"] = C.iso(p["created"])
    return d


def _sub(x, staff=None):
    k = x["klass"]
    f = x["from_staff"]
    fb = x["filled_by"]
    return {"id": x.get_id(), "status": x["status"], "reason": x["reason"] or "", "created": C.iso(x["created"]),
            "from": f["name"] if f else "", "filled_by": fb["name"] if fb else "",
            "class": Mo.class_dict(k, staff) if k else None}


# ----------------------------------------------------------------------------------------------- schedule

@anvil.server.callable(require_user=True)
def manage_schedule(slug, start_iso=None, days=7):
    me = C.require_user()
    s = _studio_for(slug, me)
    start, end = _range(start_iso, None, int(C.num(days, 7, 1, 28)))
    staff, studios, rooms = _caches()
    classes = sorted(app_tables.classes.search(studio=s, start=q.between(start, end)), key=lambda c: C.aware(c["start"]))
    team = [Mo.staff_dict(t) for t in app_tables.staff.search(studio=s) if t["active"] is not False and t["teaches"]]
    return {"classes": [Mo.class_dict(c, staff, studios, rooms) for c in classes], "teachers": team,
            "rooms": [_room(r) for r in app_tables.rooms.search(studio=s)], "styles": Mo.STYLES, "tags": Mo.TAGS,
            "levels": Mo.LEVELS}


def _room(r):
    return {"id": r.get_id(), "name": r["name"], "rows": r["rows"], "cols": r["cols"], "blocked": r["blocked"] or [],
            "capacity": (r["rows"] or 0) * (r["cols"] or 0) - len(r["blocked"] or [])}


def _class_values(s, data):
    title = C.text(data.get("title"), 70)
    if len(title) < 3:
        return None, "Give the class a name (at least 3 characters)."
    start = C.parse_iso(data.get("start"))
    if start is None:
        return None, "Choose a date and time."
    teacher = C.row_by_id(app_tables.staff, data.get("teacher_id"))
    if teacher is None or teacher["studio"] != s or teacher["active"] is False:
        return None, "Choose a teacher from your team."
    room = C.row_by_id(app_tables.rooms, data.get("room_id"))
    if room is None or room["studio"] != s:
        return None, "Choose a room."
    cap_room = (room["rows"] or 0) * (room["cols"] or 0) - len(room["blocked"] or [])
    style = data.get("style") if data.get("style") in Mo.STYLES else "Hatha"
    kind = "workshop" if data.get("kind") == "workshop" else "class"
    return dict(title=title, style=style, level=data.get("level") if data.get("level") in Mo.LEVELS else "all",
                intensity=int(C.num(data.get("intensity"), 2, 1, 5)), heated=bool(data.get("heated")),
                tags=[t for t in C.str_list(data.get("tags")) if t in Mo.TAGS],
                about=C.text(data.get("about"), 800, multiline=True), teacher=teacher, room=room, start=start,
                minutes=int(C.num(data.get("minutes"), 60, 15, 300)),
                capacity=int(C.num(data.get("capacity"), cap_room, 1, max(1, cap_room))),
                kind=kind, price=C.num(data.get("price"), 0, 0, 2000) if kind == "workshop" else 0), None


@anvil.server.callable(require_user=True)
def save_class(slug, data):
    """New class (repeat weekly for up to 12 weeks) or an edit to one class or this and the following ones."""
    me = C.require_user()
    s = _studio_for(slug, me)
    data = data if isinstance(data, dict) else {}
    vals, err = _class_values(s, data)
    if err:
        return C.fail(err)
    if data.get("id"):
        c = C.row_by_id(app_tables.classes, data["id"])
        if c is None or c["studio"] != s:
            return C.fail("That class isn't at this studio.")
        targets = [c]
        if data.get("scope") == "future" and c["series"]:
            targets = [x for x in app_tables.classes.search(studio=s, series=c["series"])
                       if C.aware(x["start"]) >= C.aware(c["start"]) and x["status"] == "scheduled"]
        shift = vals["start"] - C.aware(c["start"])
        changed_teacher = vals["teacher"] != c["teacher"]
        for x in targets:
            v = dict(vals)
            v["start"] = C.aware(x["start"]) + shift
            if changed_teacher:
                v["orig_teacher"] = vals["teacher"]
            if v["capacity"] < (x["booked"] or 0):
                v["capacity"] = x["booked"]
            x.update(**v)
            for b in app_tables.bookings.search(klass=x):
                if b["start"] != v["start"]:
                    b["start"] = v["start"]
            Mo.promote(x)
        return C.ok(count=len(targets))
    weeks = int(C.num(data.get("repeat_weeks"), 1, 1, 12))
    series = "s%d" % int(C.now().timestamp() * 1000)
    for i in range(weeks):
        v = dict(vals)
        v["start"] = vals["start"] + dt.timedelta(weeks=i)
        app_tables.classes.add_row(studio=s, series=series, orig_teacher=vals["teacher"], booked=0, waiting=0,
                                   status="scheduled", cancel_note="", is_demo=False, **v)
    return C.ok(count=weeks)


@anvil.server.callable(require_user=True)
def cancel_class(class_id, note=""):
    """Cancel a class: everyone booked or waiting gets their credit back and a message."""
    me = C.require_user()
    c = _class_for(class_id, me)
    if c is None:
        return C.fail("That class doesn't exist.")
    if c["status"] == "cancelled":
        return C.ok(notified=0)
    note = C.text(note, 300) or "Sorry for the change of plans."
    c.update(status="cancelled", cancel_note=note)
    n = 0
    for b in app_tables.bookings.search(klass=c):
        if b["status"] in ("booked", "waitlist", "late"):
            if b["status"] in ("booked", "late"):
                Mo.refund(b["pass_used"])
            b.update(status="cancelled", updated=C.now())
            C.notify(b["user"], c["studio"], "cancelled", "Cancelled: %s" % c["title"],
                     "%s Your credit is back in your wallet." % note, "#practice")
            n += 1
    Mo.recount(c)
    return C.ok(notified=n)


@anvil.server.callable(require_user=True)
def restore_class(class_id):
    me = C.require_user()
    c = _class_for(class_id, me)
    if c is None or c["status"] != "cancelled":
        return C.fail("That class isn't cancelled.")
    if C.aware(c["start"]) < C.now():
        return C.fail("That class is in the past.")
    c.update(status="scheduled", cancel_note="")
    return C.ok()


# ----------------------------------------------------------------------------------------------- roster + check-in

@anvil.server.callable(require_user=True)
def roster(class_id):
    me = C.require_user()
    c = _class_for(class_id, me, teachers_ok=True)
    if c is None:
        return C.fail("That class doesn't exist.")
    s = c["studio"]
    manage = Mo.can_manage(s, me)
    people = []
    for b in app_tables.bookings.search(klass=c):
        if b["status"] == "cancelled":
            continue
        u = b["user"]
        w = C.waiver(s, u)
        p = b["pass_used"]
        n_visits = len(Mo.visits(u, s)) if u else 0
        people.append({"id": b.get_id(), "name": C.name_of(u) if u else (b["walkin_name"] or "Walk-in"),
                       "status": b["status"], "spot": b["spot"] or "", "first_visit": bool(b["first_visit"]),
                       "visits": n_visits, "pass": p["name"] if p else "", "unpaid": bool(p and not p["paid"]),
                       "pass_id": C.rid(p) if manage else None, "grace": bool(b["grace"]),
                       "health": (w["health"] or "") if (w and w["share"]) else "", "waiver": bool(w) or u is None,
                       "wl_at": C.iso(b["wl_at"]), "milestone": n_visits in (10, 25, 50, 100)})
    order = {"checked_in": 0, "booked": 0, "no_show": 1, "late": 2, "waitlist": 3}
    people.sort(key=lambda x: (order.get(x["status"], 4), x["wl_at"] or "", x["name"]))
    return {"class": Mo.class_dict(c), "people": people, "can_manage": manage}


@anvil.server.callable(require_user=True)
def set_attendance(booking_id, status):
    me = C.require_user()
    b = C.row_by_id(app_tables.bookings, booking_id)
    if b is None:
        return C.fail("That booking doesn't exist.")
    _class_for(b["klass"].get_id(), me, teachers_ok=True)
    if status not in ("checked_in", "booked", "no_show"):
        return C.fail("Unknown attendance status.")
    if b["status"] not in ("checked_in", "booked", "no_show"):
        return C.fail("Only people with a mat can be checked in.")
    b.update(status=status, updated=C.now())
    Mo.recount(b["klass"])
    return C.ok(status=status)


@anvil.server.callable(require_user=True)
def forgive(booking_id):
    """Late cancel or no-show: give the credit back. Kindness keeps students."""
    me = C.require_user()
    b = C.row_by_id(app_tables.bookings, booking_id)
    if b is None:
        return C.fail("That booking doesn't exist.")
    _class_for(b["klass"].get_id(), me)
    if b["status"] not in ("late", "no_show"):
        return C.fail("Only late cancels and no-shows can be forgiven.")
    Mo.refund(b["pass_used"])
    b.update(status="cancelled", forgiven=True, updated=C.now())
    Mo.recount(b["klass"])
    C.notify(b["user"], b["studio"], "forgiven", "Your credit is back",
             "%s gave you back the credit for %s. No worries, life happens." % (b["studio"]["name"], b["klass"]["title"]), "#practice/wallet")
    return C.ok()


@anvil.server.callable(require_user=True)
def add_walkin(class_id, name, email=""):
    """The front desk adds someone at the door: an existing account (by email) or just a name."""
    me = C.require_user()
    c = _class_for(class_id, me)
    if c is None:
        return C.fail("That class doesn't exist.")
    name = C.text(name, 60)
    email = C.text(email, 120).lower()
    u = app_tables.users.get(email=email) if email else None
    if u is None and len(name) < 2:
        return C.fail("Type the person's name (or the email of their account).")
    now = C.now()
    p = None
    if u is not None:
        if any(b["status"] in Mo.ACTIVE for b in app_tables.bookings.search(klass=c, user=u)):
            return C.fail("%s is already on the list." % C.name_of(u))
        usable = Mo.usable_passes(u, c)
        p = usable[0] if usable else None
        if p is None:
            p = app_tables.passes.add_row(user=u, studio=c["studio"], product=None, name="Drop-in (at the desk)", kind="dropin",
                                          credits_total=1, credits_left=1, starts=now, expires=now + dt.timedelta(days=1),
                                          paused_until=None, paid=False, pay_method="", price=_dropin_price(c["studio"]),
                                          source="desk", created=now, is_demo=False)
        Mo.spend(p)
    first = u is None or not Mo.has_visited(u, c["studio"])
    app_tables.bookings.add_row(klass=c, user=u, studio=c["studio"], pass_used=p, start=c["start"], spot=None, status="checked_in",
                                wl_at=None, first_visit=first, grace=False, forgiven=False, walkin_name=None if u else name,
                                reviewed=False, created=now, updated=now, is_demo=False)
    Mo.recount(c)
    return C.ok()


def _dropin_price(s):
    for p in app_tables.products.search(studio=s, kind="dropin"):
        if p["active"] is not False:
            return p["price"] or 0
    return 0


@anvil.server.callable(require_user=True)
def mark_paid(pass_id, method="card"):
    me = C.require_user()
    p = C.row_by_id(app_tables.passes, pass_id)
    if p is None:
        return C.fail("That pass doesn't exist.")
    _studio_for(p["studio"]["slug"], me)
    method = method if method in ("card", "cash", "e-transfer", "comp") else "card"
    p.update(paid=True, pay_method=method)
    return C.ok()


# ----------------------------------------------------------------------------------------------- pricing

@anvil.server.callable(require_user=True)
def manage_products(slug):
    me = C.require_user()
    s = _studio_for(slug, me)
    rows = [Mo.product_dict(p) for p in app_tables.products.search(studio=s) if p["kind"] in Mo.PRODUCT_KINDS]
    sold = {}
    for p in app_tables.passes.search(studio=s):
        if p["product"] is not None:
            sold[p["product"].get_id()] = sold.get(p["product"].get_id(), 0) + 1
    for r in rows:
        r["sold"] = sold.get(r["id"], 0)
    rows.sort(key=lambda r: (not r["active"], r["order"]))
    return {"products": rows, "kinds": Mo.PRODUCT_KINDS}


@anvil.server.callable(require_user=True)
def save_product(slug, data):
    me = C.require_user()
    s = _studio_for(slug, me)
    data = data if isinstance(data, dict) else {}
    name = C.text(data.get("name"), 60)
    if len(name) < 3:
        return C.fail("Give it a name (at least 3 characters).")
    kind = data.get("kind") if data.get("kind") in Mo.PRODUCT_KINDS else "pack"
    credits = None if kind == "unlimited" or (kind == "intro" and not data.get("credits")) else int(C.num(data.get("credits"), 1, 1, 200))
    if kind == "dropin":
        credits = 1
    vals: dict = dict(name=name, kind=kind, credits=credits, days=int(C.num(data.get("days"), 30, 1, 730)),
                price=C.num(data.get("price"), 0, 0, 10000), intro_only=bool(data.get("intro_only")) or kind == "intro",
                about=C.text(data.get("about"), 200), active=data.get("active") is not False)
    if data.get("id"):
        p = C.row_by_id(app_tables.products, data["id"])
        if p is None or p["studio"] != s:
            return C.fail("That option isn't at this studio.")
        p.update(**vals)
    else:
        n = len(app_tables.products.search(studio=s))
        app_tables.products.add_row(studio=s, order=n, is_demo=False, **vals)
    return C.ok()


# ----------------------------------------------------------------------------------------------- clients

def _client_rows(s):
    now = C.now()
    people = {}
    for b in app_tables.bookings.search(studio=s):
        u = b["user"]
        if u is None:
            continue
        d = people.setdefault(u.get_id(), {"user": u, "visits": 0, "last": None, "first": None, "upcoming": 0, "late": 0, "no_show": 0})
        st = C.aware(b["start"])
        if b["status"] in ("checked_in", "booked", "no_show") and st < now:
            if b["status"] == "no_show":
                d["no_show"] += 1
            else:
                d["visits"] += 1
                d["last"] = max(d["last"], st) if d["last"] else st
                d["first"] = min(d["first"], st) if d["first"] else st
        elif b["status"] in ("booked", "waitlist") and st >= now:
            d["upcoming"] += 1
        elif b["status"] == "late":
            d["late"] += 1
    for p in app_tables.passes.search(studio=s):
        u = p["user"]
        if u is None:
            continue
        d = people.setdefault(u.get_id(), {"user": u, "visits": 0, "last": None, "first": None, "upcoming": 0, "late": 0, "no_show": 0})
        d.setdefault("passes", []).append(p)
    nudged = {}
    for n in app_tables.notices.search(studio=s, kind="nudge"):
        if n["user"] is not None:
            k = n["user"].get_id()
            nudged[k] = max(nudged.get(k) or C.aware(n["created"]), C.aware(n["created"]))
    out = []
    for k, d in people.items():
        passes = d.get("passes", [])
        active = [p for p in passes if Mo.pass_state(p) in ("active", "paused")]
        kinds = set(p["kind"] for p in active)
        tags = []
        if any(p["kind"] in ("intro", "friend") and C.aware(p["created"]) > now - dt.timedelta(days=21) for p in passes):
            tags.append("new")
        if "unlimited" in kinds:
            tags.append("member")
        elif "intro" in kinds or "friend" in kinds:
            tags.append("intro")
        if active and d["upcoming"] == 0 and (d["last"] is None or d["last"] < now - dt.timedelta(days=14)):
            tags.append("drifting")
        if any(not p["paid"] for p in passes if p["kind"] != "friend"):
            tags.append("unpaid")
        expiring = [p for p in active if p["expires"] and C.aware(p["expires"]) < now + dt.timedelta(days=7)]
        if expiring:
            tags.append("expiring")
        u = d["user"]
        out.append({"id": k, "name": C.name_of(u), "email": u["email"], "visits": d["visits"], "upcoming": d["upcoming"],
                    "last": C.iso(d["last"]), "first": C.iso(d["first"]), "late": d["late"], "no_show": d["no_show"],
                    "passes": [p["name"] for p in active], "credits": sum(p["credits_left"] or 0 for p in active if p["credits_left"] is not None),
                    "tags": tags, "nudged": C.iso(nudged.get(k)), "spent": sum(p["price"] or 0 for p in passes)})
    out.sort(key=lambda c: c["last"] or "", reverse=True)
    return out


@anvil.server.callable(require_user=True)
def clients(slug):
    me = C.require_user()
    s = _studio_for(slug, me)
    rows = _client_rows(s)
    counts = {t: len([c for c in rows if t in c["tags"]]) for t in ("new", "member", "intro", "drifting", "unpaid", "expiring")}
    counts["all"] = len(rows)
    return {"clients": rows, "counts": counts}


@anvil.server.callable(require_user=True)
def client_detail(slug, user_id):
    me = C.require_user()
    s = _studio_for(slug, me)
    u = C.row_by_id(app_tables.users, user_id)
    if u is None:
        return C.fail("That person doesn't exist.")
    bookings = sorted(app_tables.bookings.search(studio=s, user=u), key=lambda b: C.aware(b["start"]), reverse=True)
    if not bookings and not len(app_tables.passes.search(studio=s, user=u)):  # a search is always truthy: count it
        return C.fail("That person isn't a client of this studio.")
    w = C.waiver(s, u)
    return {"name": C.name_of(u), "email": u["email"],
            "passes": [_pass_row(p) for p in sorted(app_tables.passes.search(studio=s, user=u), key=lambda p: C.aware(p["created"]), reverse=True)],
            "bookings": [{"id": b.get_id(), "title": b["klass"]["title"] if b["klass"] else "", "start": C.iso(b["start"]),
                          "status": b["status"], "mood": b["mood"]} for b in bookings[:60]],
            "waiver": {"signed": C.iso(w["signed"]), "emergency": w["emergency"] or "", "health": (w["health"] or "") if w["share"] else "",
                       "shared": bool(w["share"])} if w else None}


@anvil.server.callable(require_user=True)
def nudge(slug, user_id, message):
    """A friendly personal note to a client (shows in their inbox), e.g. to someone drifting away."""
    me = C.require_user()
    s = _studio_for(slug, me)
    u = C.row_by_id(app_tables.users, user_id)
    if u is None or not (len(app_tables.bookings.search(studio=s, user=u)) or len(app_tables.passes.search(studio=s, user=u))):
        return C.fail("You can only message your own clients.")
    message = C.text(message, 600, multiline=True)
    if len(message) < 5:
        return C.fail("Write a short message (at least 5 characters).")
    if C.rate_limited("nudge", 40, 3600):
        return C.fail("That's a lot of messages in an hour. Try again later.")
    C.notify(u, s, "nudge", "A note from %s" % s["name"], message, "#studio/" + s["slug"])
    return C.ok()


# ----------------------------------------------------------------------------------------------- team + pay

def pay_for(st, n):
    return (st["pay_base"] or 0) + (st["pay_per_head"] or 0) * max(0, n - (st["pay_after"] or 0))


def attended(klass):
    return len([b for b in app_tables.bookings.search(klass=klass) if b["status"] in ("checked_in", "booked")])


@anvil.server.callable(require_user=True)
def team(slug, start_iso=None, end_iso=None):
    """Team list with pay rates, plus this period's classes, attendance, pay and rating per person."""
    me = C.require_user()
    s = _studio_for(slug, me)
    now = C.now()
    start = C.parse_iso(start_iso) or now - dt.timedelta(days=30)
    end = C.parse_iso(end_iso) or now
    rows = [t for t in app_tables.staff.search(studio=s) if t["active"] is not False]
    classes = [c for c in app_tables.classes.search(studio=s, start=q.between(start, min(end, now))) if c["status"] == "scheduled"]
    out = []
    for t in rows:
        mine = [c for c in classes if c["teacher"] == t]
        heads = [attended(c) for c in mine]
        revs = [r["stars"] for r in app_tables.reviews.search(teacher=t) if not r["hidden"]]
        d = Mo.staff_dict(t, private=True)
        d.update(classes=len(mine), heads=sum(heads), avg=round(sum(heads) / len(heads), 1) if heads else 0,
                 pay=sum(pay_for(t, n) for n in heads), rating=round(sum(revs) / len(revs), 2) if revs else 0,
                 rating_n=len(revs), subs_covered=len(app_tables.subs.search(filled_by=t)))
        out.append(d)
    subs = sorted(app_tables.subs.search(studio=s), key=lambda x: C.aware(x["created"]), reverse=True)
    return {"team": out, "subs": [_sub(x) for x in subs[:20]], "from": C.iso(start), "to": C.iso(end)}


@anvil.server.callable(require_user=True)
def save_staff(slug, data):
    """Invite someone (by email: they get access when they sign in with it) or change a team member."""
    me = C.require_user()
    s = _studio_for(slug, me)
    data = data if isinstance(data, dict) else {}
    vals: dict = dict(name=C.text(data.get("name"), 60), bio=C.text(data.get("bio"), 600, multiline=True),
                role=data.get("role") if data.get("role") in ("owner", "desk", "teacher") else "teacher",
                teaches=bool(data.get("teaches", True)), styles=[x for x in C.str_list(data.get("styles")) if x in Mo.STYLES],
                pay_base=C.num(data.get("pay_base"), 0, 0, 1000), pay_per_head=C.num(data.get("pay_per_head"), 0, 0, 100),
                pay_after=int(C.num(data.get("pay_after"), 0, 0, 100)))
    if data.get("id"):
        t = C.row_by_id(app_tables.staff, data["id"])
        if t is None or t["studio"] != s:
            return C.fail("That person isn't on this team.")
        if t["role"] == "owner" and vals["role"] != "owner" and len([x for x in app_tables.staff.search(studio=s, role="owner") if x["active"] is not False]) < 2:
            return C.fail("A studio needs at least one owner.")
        if not vals["name"]:
            vals["name"] = t["name"]
        t.update(**vals)
        return C.ok()
    email = C.text(data.get("email"), 120).lower()
    if "@" not in email or "." not in email.split("@")[-1]:
        return C.fail("Type the email they'll sign in with.")
    if len(vals["name"]) < 2:
        return C.fail("Type their name.")
    for t in app_tables.staff.search(studio=s):
        if (t["email"] or "").lower() == email and t["active"] is not False:
            return C.fail("%s is already on the team." % email)
    u = app_tables.users.get(email=email)
    app_tables.staff.add_row(studio=s, user=u, email=email, active=True, created=C.now(), is_demo=False, **vals)
    if u is not None:
        C.notify(u, s, "team", "You joined the team at %s" % s["name"],
                 "You can now see your classes, rosters and pay in Teach.", "#teach")
    return C.ok(invited=u is None)


@anvil.server.callable(require_user=True)
def remove_staff(staff_id):
    me = C.require_user()
    t = C.row_by_id(app_tables.staff, staff_id)
    if t is None:
        return C.fail("That person isn't on the team.")
    s = _studio_for(t["studio"]["slug"], me)
    if t["role"] == "owner" and len([x for x in app_tables.staff.search(studio=s, role="owner") if x["active"] is not False]) < 2:
        return C.fail("A studio needs at least one owner.")
    future = [c for c in app_tables.classes.search(studio=s, teacher=t) if c["status"] == "scheduled" and C.aware(c["start"]) > C.now()]
    if future:
        return C.fail("%s still teaches %d upcoming classes. Give them to someone else first." % (t["name"], len(future)))
    t["active"] = False
    return C.ok()


# ----------------------------------------------------------------------------------------------- insights

@anvil.server.callable(require_user=True)
def insights(slug, days=28):
    me = C.require_user()
    s = _studio_for(slug, me)
    days = int(C.num(days, 28, 7, 90))
    now = C.now()
    start = now - dt.timedelta(days=days)
    staff = C.by_id(app_tables.staff.search(studio=s))
    classes = [c for c in app_tables.classes.search(studio=s, start=q.between(start, now)) if c["status"] == "scheduled"]
    bookings = [b for b in app_tables.bookings.search(studio=s, start=q.between(start, now))]
    by_class = {}
    for b in bookings:
        if b["klass"] is not None:
            by_class.setdefault(b["klass"].get_id(), []).append(b)
    heat = []
    tops = {}
    fill_sum = 0
    for c in classes:
        bs = by_class.get(c.get_id(), [])
        n = len([b for b in bs if b["status"] in ("checked_in", "booked")])
        fill = n / c["capacity"] if c["capacity"] else 0
        fill_sum += fill
        st = C.aware(c["start"])
        heat.append([st.isoformat(), round(fill, 3)])
        key = c["title"]
        t = tops.setdefault(key, {"title": key, "classes": 0, "heads": 0, "fill": 0})
        t["classes"] += 1
        t["heads"] += n
        t["fill"] += fill
    top = sorted(({"title": t["title"], "classes": t["classes"], "avg": round(t["heads"] / t["classes"], 1),
                   "fill": round(100 * t["fill"] / t["classes"])} for t in tops.values()), key=lambda t: -t["fill"])
    status = {}
    for b in bookings:
        status[b["status"]] = status.get(b["status"], 0) + 1
    came = status.get("checked_in", 0) + status.get("booked", 0)
    passes = [p for p in app_tables.passes.search(studio=s, created=q.between(start, now))]
    revenue = {}
    for p in passes:
        revenue[p["kind"]] = revenue.get(p["kind"], 0) + (p["price"] or 0)
    daily = {}
    for p in passes:
        k = C.aware(p["created"]).date().isoformat()
        daily[k] = daily.get(k, 0) + (p["price"] or 0)
    # Intro funnel: intro or friend passes in the window -> came back a 2nd time -> bought a pack or membership.
    intro = [p for p in app_tables.passes.search(studio=s) if p["kind"] in ("intro", "friend") and C.aware(p["created"]) >= now - dt.timedelta(days=max(days, 60))]
    started, second, converted = len(intro), 0, 0
    for p in intro:
        u = p["user"]
        v = [b for b in app_tables.bookings.search(studio=s, user=u) if b["status"] in ("checked_in", "booked") and C.aware(b["start"]) < now]
        if len(v) >= 2:
            second += 1
        if any(x["kind"] in ("pack", "unlimited") and C.aware(x["created"]) >= C.aware(p["created"]) for x in app_tables.passes.search(studio=s, user=u)):
            converted += 1
    teachers = []
    for t in staff.values():
        mine = [c for c in classes if c["teacher"] == t]
        if not mine:
            continue
        heads = [len([b for b in by_class.get(c.get_id(), []) if b["status"] in ("checked_in", "booked")]) for c in mine]
        revs = [r["stars"] for r in app_tables.reviews.search(teacher=t) if not r["hidden"]]
        teachers.append({"name": t["name"], "classes": len(mine), "avg": round(sum(heads) / len(heads), 1),
                         "rating": round(sum(revs) / len(revs), 2) if revs else 0})
    teachers.sort(key=lambda t: -t["avg"])
    rows = _client_rows(s)
    fp = [f for f in app_tables.friend_passes.search(studio=s)]
    moods = [b["mood"] for b in bookings if b["mood"]]
    return {"days": days, "classes": len(classes), "visits": came, "fill": round(100 * fill_sum / len(classes)) if classes else 0,
            "no_show": status.get("no_show", 0), "late": status.get("late", 0),
            "no_show_rate": round(100 * status.get("no_show", 0) / max(1, came + status.get("no_show", 0))),
            "revenue": revenue, "revenue_total": sum(revenue.values()), "daily": daily, "heat": heat, "top": top[:8],
            "funnel": {"started": started, "second": second, "converted": converted}, "teachers": teachers,
            "clients": {"total": len(rows), "new": len([c for c in rows if "new" in c["tags"]]),
                        "drifting": len([c for c in rows if "drifting" in c["tags"]]),
                        "members": len([c for c in rows if "member" in c["tags"]])},
            "friend": {"sent": len(fp), "claimed": len([f for f in fp if f["claimed_by"] is not None])},
            "mood": round(sum(moods) / len(moods), 2) if moods else 0, "mood_n": len(moods),
            "rating": s["rating"] or 0, "rating_n": s["rating_n"] or 0}


# ----------------------------------------------------------------------------------------------- reviews

@anvil.server.callable(require_user=True)
def manage_reviews(slug):
    me = C.require_user()
    s = _studio_for(slug, me)
    rows = sorted(app_tables.reviews.search(studio=s), key=lambda r: C.aware(r["created"]), reverse=True)
    from .Studios import _review
    return {"reviews": [_review(r) for r in rows[:100]], "rating": s["rating"] or 0, "rating_n": s["rating_n"] or 0}


@anvil.server.callable(require_user=True)
def reply_review(review_id, text):
    me = C.require_user()
    r = C.row_by_id(app_tables.reviews, review_id)
    if r is None:
        return C.fail("That review doesn't exist.")
    _studio_for(r["studio"]["slug"], me)
    text = C.text(text, 600, multiline=True)
    r.update(reply=text, reply_at=C.now() if text else None)
    if text and r["user"] is not None:
        C.notify(r["user"], r["studio"], "reply", "%s replied to your review" % r["studio"]["name"], text, "#studio/" + r["studio"]["slug"])
    return C.ok()


@anvil.server.callable(require_user=True)
def hide_review(review_id, hidden):
    """Hide a review that breaks the rules (abuse, personal details). Hidden reviews don't count in the rating."""
    me = C.require_user()
    r = C.row_by_id(app_tables.reviews, review_id)
    if r is None:
        return C.fail("That review doesn't exist.")
    _studio_for(r["studio"]["slug"], me)
    r["hidden"] = bool(hidden)
    Booking.refresh_rating(r["studio"])
    return C.ok()


# ----------------------------------------------------------------------------------------------- settings + rooms

@anvil.server.callable(require_user=True)
def manage_settings(slug):
    me = C.require_user()
    s = _studio_for(slug, me)
    return {"studio": _studio_full(s), "rooms": [_room(r) for r in app_tables.rooms.search(studio=s)],
            "styles": Mo.STYLES, "accents": Mo.ACCENTS}


@anvil.server.callable(require_user=True)
def save_studio(slug, data):
    me = C.require_user()
    s = _studio_for(slug, me)
    data = data if isinstance(data, dict) else {}
    name = C.text(data.get("name"), 60)
    if len(name) < 3:
        return C.fail("The studio needs a name (at least 3 characters).")
    s.update(name=name, tagline=C.text(data.get("tagline"), 90), about=C.text(data.get("about"), 1500, multiline=True),
             neighbourhood=C.text(data.get("neighbourhood"), 60) or s["neighbourhood"], address=C.text(data.get("address"), 120),
             city=C.text(data.get("city"), 60) or s["city"],
             styles=[x for x in C.str_list(data.get("styles")) if x in Mo.STYLES] or s["styles"],
             amenities=C.str_list(data.get("amenities")), languages=C.str_list(data.get("languages"), 4) or s["languages"],
             accent=data.get("accent") if data.get("accent") in Mo.ACCENTS else s["accent"],
             cancel_hours=int(C.num(data.get("cancel_hours"), 12, 0, 72)),
             waiver_text=C.text(data.get("waiver_text"), 2000, multiline=True) or s["waiver_text"])
    return C.ok(studio=_studio_full(s))


@anvil.server.callable(require_user=True)
def save_room(slug, data):
    me = C.require_user()
    s = _studio_for(slug, me)
    data = data if isinstance(data, dict) else {}
    name = C.text(data.get("name"), 40)
    if len(name) < 2:
        return C.fail("Name the room.")
    rows, cols = int(C.num(data.get("rows"), 4, 1, 10)), int(C.num(data.get("cols"), 5, 1, 10))
    blocked = [b for b in C.str_list(data.get("blocked"), 100, 4)
               if len(b) >= 2 and 1 <= ord(b[0]) - 64 <= rows and b[1:].isdigit() and 1 <= int(b[1:]) <= cols]
    if rows * cols - len(blocked) < 1:
        return C.fail("Leave at least one mat free.")
    if data.get("id"):
        r = C.row_by_id(app_tables.rooms, data["id"])
        if r is None or r["studio"] != s:
            return C.fail("That room isn't at this studio.")
        r.update(name=name, rows=rows, cols=cols, blocked=blocked)
    else:
        app_tables.rooms.add_row(studio=s, name=name, rows=rows, cols=cols, blocked=blocked, is_demo=False)
    return C.ok()


@anvil.server.callable(require_user=True)
def export_csv(slug, kind):
    """Your data, any day, free: clients, bookings or passes as a CSV file."""
    me = C.require_user()
    s = _studio_for(slug, me)
    buf = io.StringIO()
    w = csv.writer(buf)
    if kind == "clients":
        w.writerow(["name", "email", "visits", "first_visit", "last_visit", "upcoming", "late_cancels", "no_shows", "active_passes", "tags", "total_spent"])
        for c in _client_rows(s):
            w.writerow([c["name"], c["email"], c["visits"], c["first"] or "", c["last"] or "", c["upcoming"], c["late"], c["no_show"],
                        "; ".join(c["passes"]), "; ".join(c["tags"]), c["spent"]])
    elif kind == "bookings":
        w.writerow(["class", "start", "teacher", "person", "email", "status", "mat", "first_visit", "pass"])
        for b in sorted(app_tables.bookings.search(studio=s), key=lambda b: C.aware(b["start"])):
            k = b["klass"]
            u = b["user"]
            w.writerow([k["title"] if k else "", C.iso(b["start"]), (k["teacher"]["name"] if k and k["teacher"] else ""),
                        C.name_of(u) if u else (b["walkin_name"] or ""), u["email"] if u else "", b["status"], b["spot"] or "",
                        "yes" if b["first_visit"] else "", b["pass_used"]["name"] if b["pass_used"] else ""])
    elif kind == "passes":
        w.writerow(["person", "email", "pass", "kind", "price", "paid", "method", "credits_left", "bought", "expires"])
        for p in sorted(app_tables.passes.search(studio=s), key=lambda p: C.aware(p["created"])):
            u = p["user"]
            w.writerow([C.name_of(u), u["email"] if u else "", p["name"], p["kind"], p["price"] or 0, "yes" if p["paid"] else "no",
                        p["pay_method"] or "", "unlimited" if p["credits_left"] is None else p["credits_left"],
                        C.iso(p["created"]), C.iso(p["expires"])])
    else:
        return C.fail("Export clients, bookings or passes.")
    return C.ok(filename="%s-%s-%s.csv" % (s["slug"], kind, C.now().date().isoformat()), csv=buf.getvalue())


# ----------------------------------------------------------------------------------------------- kiosk

@anvil.server.callable(require_user=True)
def kiosk_day(slug, start_iso=None, end_iso=None):
    """The front-desk tablet: today's classes, each with the people booked (first name + initial)."""
    me = C.require_user()
    s = _studio_for(slug, me)
    start, end = _range(start_iso, end_iso)
    now = C.now()
    out = []
    for c in sorted(app_tables.classes.search(studio=s, start=q.between(start, end)), key=lambda c: C.aware(c["start"])):
        if c["status"] != "scheduled" or C.aware(c["start"]) + dt.timedelta(minutes=c["minutes"] or 60) < now:
            continue
        people = []
        for b in app_tables.bookings.search(klass=c):
            if b["status"] in ("booked", "checked_in"):
                nm = C.name_of(b["user"]) if b["user"] else (b["walkin_name"] or "Walk-in")
                parts = nm.split(" ")
                people.append({"id": b.get_id(), "name": parts[0] + (" " + parts[-1][0] + "." if len(parts) > 1 else ""),
                               "in": b["status"] == "checked_in", "spot": b["spot"] or "", "first": bool(b["first_visit"])})
        people.sort(key=lambda p: p["name"])
        d = Mo.class_dict(c)
        d["people"] = people
        out.append(d)
    return {"studio": Mo.studio_card(s), "classes": out}
