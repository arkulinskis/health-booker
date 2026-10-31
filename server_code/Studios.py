"""The marketplace: discover classes across studios, studio pages, class pages, follows, opening a studio.

Browsing works without an account (no forced sign-up to look). Only live studios are listed; a studio in
review is visible to its own staff and to admins, with a preview banner.
"""
import datetime as dt

import anvil.server
from anvil.tables import app_tables
import anvil.tables.query as q

from . import common as C
from . import DemoData
from . import Model as Mo


def _caches():
    return (C.by_id(app_tables.staff.search()), C.by_id(app_tables.studios.search()), C.by_id(app_tables.rooms.search()))


def _intro(studio):
    best = None
    for p in app_tables.products.search(studio=studio, kind="intro"):
        if p["active"] is False:
            continue
        if best is None or (p["price"] or 0) < (best["price"] or 0):
            best = p
    return {"name": best["name"], "price": best["price"] or 0} if best else None


def _follows(me):
    if me is None:
        return {"studios": [], "teachers": []}
    rows = app_tables.follows.search(user=me)
    return {"studios": [r["studio"]["slug"] for r in rows if r["studio"] is not None],
            "teachers": [r["teacher"].get_id() for r in rows if r["teacher"] is not None]}


def _my_states(me, classes):
    """{class_id: booking status} for the signed-in person (booked / waitlist / checked_in)."""
    if me is None:
        return {}
    ids = set(c.get_id() for c in classes)
    out = {}
    for b in app_tables.bookings.search(user=me, start=q.greater_than_or_equal_to(C.now() - dt.timedelta(days=1))):
        k = b["klass"]
        if k is not None and k.get_id() in ids and b["status"] in Mo.ACTIVE:
            out[k.get_id()] = b["status"]
    return out


@anvil.server.callable
def discover(start_iso=None, days=7):
    """Classes at live studios from start (default: now) for `days` days, plus the studios and filters."""
    DemoData.ensure_loaded()
    DemoData.top_up()
    me = C.me()
    days = int(C.num(days, 7, 1, 14))
    start = C.parse_iso(start_iso) or C.now()
    start = max(start, C.now() - dt.timedelta(minutes=30))
    end = start + dt.timedelta(days=days)
    staff, studios, rooms = _caches()
    live = {k: s for k, s in studios.items() if s["status"] == "live"}
    rows = [c for c in app_tables.classes.search(start=q.between(start, end), status="scheduled")
            if c["studio"] is not None and c["studio"].get_id() in live]
    rows.sort(key=lambda c: C.aware(c["start"]))
    cards = [Mo.studio_card(s, _intro(s)) for s in live.values()]
    cards.sort(key=lambda s: (not s["featured"], -(s["rating"] or 0)))
    return {"classes": [Mo.class_dict(c, staff, studios, rooms) for c in rows], "studios": cards,
            "mine": _my_states(me, rows), "follows": _follows(me), "styles": Mo.STYLES, "tags": Mo.TAGS,
            "neighbourhoods": sorted(set(s["neighbourhood"] for s in cards if s["neighbourhood"])),
            "from": C.iso(start), "to": C.iso(end)}


@anvil.server.callable
def get_studio(slug):
    DemoData.ensure_loaded()
    me = C.me()
    s = Mo.studio_by_slug(slug)
    if not Mo.visible(s, me):
        return C.fail("That studio isn't on Health Booker (or isn't open yet).")
    staff, studios, rooms = _caches()
    now = C.now()
    rows = [c for c in app_tables.classes.search(studio=s, start=q.between(now - dt.timedelta(minutes=30), now + dt.timedelta(days=14)))
            if c["status"] == "scheduled"]
    rows.sort(key=lambda c: C.aware(c["start"]))
    teachers = [Mo.staff_dict(t) for t in app_tables.staff.search(studio=s, teaches=True) if t["active"] is not False]
    reviews = [r for r in app_tables.reviews.search(studio=s) if not r["hidden"]]
    reviews.sort(key=lambda r: C.aware(r["created"]), reverse=True)
    products = Mo.shop(me, s)
    visited = bool(me and Mo.has_visited(me, s))
    passes = [Mo.pass_dict(p) for p in app_tables.passes.search(user=me, studio=s)] if me else []
    return {"studio": dict(Mo.studio_card(s, _intro(s)), about=s["about"] or "", cancel_hours=Mo.cancel_hours(s),
                           waiver_text=s["waiver_text"] or DEFAULT_WAIVER),
            "classes": [Mo.class_dict(c, staff, studios, rooms) for c in rows], "teachers": teachers,
            "reviews": [_review(r) for r in reviews[:12]], "products": products,
            "mine": _my_states(me, rows), "follows": _follows(me), "passes": passes,
            "waiver": bool(me and app_tables.waivers.get(studio=s, user=me)),
            "can_manage": Mo.can_manage(s, me), "visited": visited}


def _review(r):
    t = r["teacher"]
    k = r["klass"]
    return {"id": r.get_id(), "stars": r["stars"], "text": r["text"] or "", "created": C.iso(r["created"]),
            "who": C.first_name(r["user"]) if r["user"] else "A student", "teacher": t["name"] if t else "",
            "class": k["title"] if k else "", "reply": r["reply"] or "", "reply_at": C.iso(r["reply_at"]),
            "hidden": bool(r["hidden"])}


@anvil.server.callable
def get_class(class_id):
    me = C.me()
    c = C.row_by_id(app_tables.classes, class_id)
    if c is None or not Mo.visible(c["studio"], me):
        return C.fail("That class isn't on the schedule any more.")
    s = c["studio"]
    d = Mo.class_dict(c)
    room = c["room"]
    taken = []
    mine = None
    for b in app_tables.bookings.search(klass=c):
        if b["status"] in Mo.TAKES_MAT and b["spot"]:
            taken.append(b["spot"])
        if me is not None and b["user"] == me and b["status"] in Mo.ACTIVE + ("late",):
            mine = b
    t = c["teacher"]
    teacher = Mo.staff_dict(t) if t else None
    reviews = []
    if t is not None:
        reviews = [r for r in app_tables.reviews.search(teacher=t) if not r["hidden"]]
        reviews.sort(key=lambda r: C.aware(r["created"]), reverse=True)
    passes = [Mo.pass_dict(p) for p in Mo.usable_passes(me, c)] if me else []
    visited = bool(me and Mo.has_visited(me, s))
    products = Mo.shop(me, s)
    following = _follows(me)
    return {"class": d, "teacher": teacher, "reviews": [_review(r) for r in reviews[:4]],
            "room": {"id": room.get_id(), "name": room["name"], "rows": room["rows"], "cols": room["cols"],
                     "blocked": room["blocked"] or []} if room else None,
            "taken": taken, "booking": Mo.booking_dict(mine, d) if mine else None, "passes": passes,
            "products": products, "waiver": bool(me and app_tables.waivers.get(studio=s, user=me)),
            "waiver_text": s["waiver_text"] or DEFAULT_WAIVER, "visited": visited, "follows": following,
            "is_staff": Mo.is_staff(s, me), "past": C.aware(c["start"]) + dt.timedelta(minutes=c["minutes"] or 60) < C.now()}


@anvil.server.callable(require_user=True)
def toggle_follow(kind, ref):
    me = C.require_user()
    if kind == "studio":
        s = Mo.studio_by_slug(ref)
        if s is None:
            return C.fail("That studio doesn't exist.")
        row = app_tables.follows.get(user=me, studio=s)
        if row:
            row.delete()
            return C.ok(following=False)
        app_tables.follows.add_row(user=me, studio=s, created=C.now(), is_demo=False)
        return C.ok(following=True)
    if kind == "teacher":
        t = C.row_by_id(app_tables.staff, ref)
        if t is None:
            return C.fail("That teacher isn't listed any more.")
        row = app_tables.follows.get(user=me, teacher=t)
        if row:
            row.delete()
            return C.ok(following=False)
        app_tables.follows.add_row(user=me, teacher=t, created=C.now(), is_demo=False)
        return C.ok(following=True)
    return C.fail("Follow a studio or a teacher.")


DEFAULT_WAIVER = ("I take part in classes at my own risk and will listen to my body. I will tell the teacher about any "
                  "injury, pregnancy or health condition before class. The studio may photograph group classes only "
                  "with my consent.")

DEFAULT_PRODUCTS = [
    ("Intro week: unlimited for 7 days", "intro", None, 7, 29, True, "New here? Try every class for a week.", 0),
    ("Drop-in", "dropin", 1, 30, 24, False, "One class, use it within 30 days.", 1),
    ("10-class pack", "pack", 10, 180, 210, False, "Ten classes, valid six months, shareable never.", 2),
    ("Monthly unlimited", "unlimited", None, 30, 149, False, "Practise as much as you like. Pause it anytime.", 3),
]


@anvil.server.callable(require_user=True)
def create_studio(data):
    """Anyone can open a studio. It starts "in review" (admins publish it); admins' own studios go live at once."""
    me = C.require_user()
    data = data if isinstance(data, dict) else {}
    name = C.text(data.get("name"), 60)
    if len(name) < 3:
        return C.fail("Give your studio a name (at least 3 characters).")
    if C.rate_limited("create_studio", 3, 86400):
        return C.fail("You've opened a few studios today already. Try again tomorrow.")
    hood = C.text(data.get("neighbourhood"), 60)
    if not hood:
        return C.fail("Which neighbourhood is the studio in?")
    base = C.slugify(name)
    slug, n = base, 2
    while app_tables.studios.get(slug=slug):
        slug, n = "%s-%d" % (base, n), n + 1
    accent = data.get("accent") if data.get("accent") in Mo.ACCENTS else "sage"
    styles = [s for s in C.str_list(data.get("styles")) if s in Mo.STYLES] or ["Hatha"]
    s = app_tables.studios.add_row(
        slug=slug, name=name, tagline=C.text(data.get("tagline"), 90), about=C.text(data.get("about"), 1500, multiline=True),
        neighbourhood=hood, address=C.text(data.get("address"), 120), city=C.text(data.get("city"), 60) or "Montréal",
        styles=styles, amenities=C.str_list(data.get("amenities")), languages=C.str_list(data.get("languages"), 4) or ["English"],
        accent=accent, status="live" if C.is_admin(me) else "review", featured=False, cancel_hours=12,
        waiver_text=DEFAULT_WAIVER, owner=me, rating=0, rating_n=0, created=C.now(), is_demo=False)
    rows, cols = int(C.num(data.get("rows"), 4, 1, 10)), int(C.num(data.get("cols"), 5, 1, 10))
    app_tables.rooms.add_row(studio=s, name=C.text(data.get("room"), 40) or "Main room", rows=rows, cols=cols, blocked=[], is_demo=False)
    app_tables.staff.add_row(studio=s, user=me, email=me["email"], name=C.name_of(me), bio="", role="owner", teaches=True,
                             styles=styles, pay_base=0, pay_per_head=0, pay_after=0, active=True, created=C.now(), is_demo=False)
    for (pname, kind, credits, days, price, intro, about, order) in DEFAULT_PRODUCTS:
        app_tables.products.add_row(studio=s, name=pname, kind=kind, credits=credits, days=days, price=price, intro_only=intro,
                                    about=about, active=True, order=order, is_demo=False)
    return C.ok(slug=slug, status=s["status"])
