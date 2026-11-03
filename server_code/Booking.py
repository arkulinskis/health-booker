"""Students: book, waitlist, cancel, buy passes, sign waivers, the practice journal, reviews, inbox, friend passes.

Payments: Health Booker doesn't take card payments yet. A pass bought online is "pay at the studio"
(paid=False) and the front desk marks it paid; free offers are paid at once.
"""
import datetime as dt
import secrets

import anvil.server
from anvil.tables import app_tables
import anvil.tables as tables

from . import common as C
from . import Model as Mo

MOODS = {1: "Heavy", 2: "Tired", 3: "Okay", 4: "Light", 5: "Glowing"}


def _own_booking(booking_id, me):
    b = C.row_by_id(app_tables.bookings, booking_id)
    if b is None or b["user"] != me:
        return None
    return b


@tables.in_transaction
def _book(me, c, p, spot):
    """Returns (booking, None) or (None, error). Inside a transaction so two people can't take the last mat."""
    for b in app_tables.bookings.search(klass=c, user=me):
        if b["status"] in Mo.ACTIVE:
            return b, None
    booked, _ = Mo.recount(c)
    first = not Mo.has_visited(me, c["studio"])
    if spot:
        taken = set(b["spot"] for b in app_tables.bookings.search(klass=c) if b["status"] in Mo.TAKES_MAT and b["spot"])
        room = c["room"]
        valid = room is not None and spot not in (room["blocked"] or []) and _spot_in_room(spot, room)
        if not valid:
            return None, "That mat isn't in this room."
        if spot in taken:
            return None, "Someone just took that mat. Pick another one."
    now = C.now()
    if booked >= (c["capacity"] or 0):
        b = app_tables.bookings.add_row(klass=c, user=me, studio=c["studio"], pass_used=p, start=c["start"], spot=None,
                                        status="waitlist", wl_at=now, first_visit=first, grace=False, forgiven=False,
                                        reviewed=False, created=now, updated=now, is_demo=False)
    else:
        Mo.spend(p)
        b = app_tables.bookings.add_row(klass=c, user=me, studio=c["studio"], pass_used=p, start=c["start"], spot=spot or None,
                                        status="booked", wl_at=None, first_visit=first, grace=False, forgiven=False,
                                        reviewed=False, created=now, updated=now, is_demo=False)
    Mo.recount(c)
    return b, None


def _spot_in_room(spot, room):
    if not isinstance(spot, str) or len(spot) < 2:
        return False
    r = ord(spot[0].upper()) - 64
    try:
        col = int(spot[1:])
    except ValueError:
        return False
    return 1 <= r <= (room["rows"] or 0) and 1 <= col <= (room["cols"] or 0)


@anvil.server.callable(require_user=True)
def book_class(class_id, pass_id=None, spot=None):
    me = C.require_user()
    c = C.row_by_id(app_tables.classes, class_id)
    if c is None or c["status"] != "scheduled" or not Mo.visible(c["studio"], me):
        return C.fail("That class isn't on the schedule any more.")
    if C.aware(c["start"]) + dt.timedelta(minutes=10) < C.now():
        return C.fail("This class has already started.")
    s = c["studio"]
    if not C.waiver(s, me):
        from .Studios import DEFAULT_WAIVER
        return dict(C.fail("Please sign %s's waiver first (once, takes 20 seconds)." % s["name"]), need="waiver",
                    waiver_text=s["waiver_text"] or DEFAULT_WAIVER)
    if c["kind"] == "workshop":
        p = _workshop_ticket(me, c)
    elif pass_id:
        p = C.row_by_id(app_tables.passes, pass_id)
        if p is None or p["user"] != me or not Mo.covers(p, c):
            return C.fail("That pass can't be used for this class.")
    else:
        usable = Mo.usable_passes(me, c)
        if not usable:
            return dict(C.fail("You need a pass for %s first." % s["name"]), need="pass", products=Mo.shop(me, s))
        p = usable[0]
    spot = C.text(spot, 4).upper() or None
    b, err = _book(me, c, p, spot)
    if err:
        return C.fail(err)
    return C.ok(booking=Mo.booking_dict(b))


def _workshop_ticket(me, c):
    """Workshops are paid per event: a one-off ticket, paid at the studio (free if the price is 0)."""
    for p in app_tables.passes.search(user=me, studio=c["studio"], kind="workshop"):
        if p["name"] == "Workshop: " + c["title"] and p["credits_left"]:
            return p
    price = c["price"] or 0
    return app_tables.passes.add_row(user=me, studio=c["studio"], product=None, name="Workshop: " + c["title"], kind="workshop",
                                     credits_total=1, credits_left=1, starts=C.now(), expires=C.aware(c["start"]) + dt.timedelta(days=1),
                                     paused_until=None, paid=price == 0, pay_method="free" if price == 0 else "",
                                     price=price, source="buy", created=C.now(), is_demo=False)


@anvil.server.callable(require_user=True)
def cancel_booking(booking_id):
    me = C.require_user()
    b = _own_booking(booking_id, me)
    if b is None:
        return C.fail("That booking isn't yours.")
    c = b["klass"]
    if b["status"] == "waitlist":
        b.update(status="cancelled", updated=C.now())
        Mo.recount(c)
        return C.ok(result="left_waitlist")
    if b["status"] != "booked":
        return C.fail("This booking can't be cancelled any more.")
    start = C.aware(c["start"])
    if start < C.now():
        return C.fail("Class has started. Talk to the front desk.")
    cutoff = start - dt.timedelta(hours=Mo.cancel_hours(c["studio"]))
    if C.now() <= cutoff or b["grace"]:
        Mo.refund(b["pass_used"])
        b.update(status="cancelled", updated=C.now())
        result = "refunded"
    else:
        b.update(status="late", updated=C.now())
        result = "late"
    Mo.promote(c)
    return C.ok(result=result)


@anvil.server.callable(require_user=True)
def buy_product(product_id):
    me = C.require_user()
    p = C.row_by_id(app_tables.products, product_id)
    if p is None or p["active"] is False or p["kind"] not in Mo.PRODUCT_KINDS:
        return C.fail("That option isn't for sale any more.")
    s = p["studio"]
    if not Mo.visible(s, me):
        return C.fail("This studio isn't taking bookings yet.")
    if p["intro_only"]:
        had_intro = any(x["kind"] == "intro" for x in app_tables.passes.search(user=me, studio=s))
        if had_intro or Mo.has_visited(me, s):
            return C.fail("Intro offers are for your first visit to %s." % s["name"])
    if C.rate_limited("buy", 12, 3600):
        return C.fail("That's a lot of purchases in an hour. Please try again later.")
    now = C.now()
    price = p["price"] or 0
    row = app_tables.passes.add_row(user=me, studio=s, product=p, name=p["name"], kind=p["kind"], credits_total=p["credits"],
                                    credits_left=p["credits"], starts=now, expires=now + dt.timedelta(days=p["days"] or 30),
                                    paused_until=None, paid=price == 0, pay_method="free" if price == 0 else "",
                                    price=price, source="buy", created=now, is_demo=False)
    return C.ok(pass_=Mo.pass_dict(row))


@anvil.server.callable(require_user=True)
def sign_waiver(slug, signature, emergency="", health="", share=False):
    me = C.require_user()
    s = Mo.studio_by_slug(slug)
    if s is None:
        return C.fail("That studio doesn't exist.")
    signature = C.text(signature, 80)
    if len(signature) < 3:
        return C.fail("Type your full name to sign.")
    row = C.waiver(s, me)
    vals = dict(signed=C.now(), signature=signature, emergency=C.text(emergency, 120),
                health=C.text(health, 600, multiline=True), share=bool(share))
    if row:
        row.update(**vals)
    else:
        app_tables.waivers.add_row(studio=s, user=me, is_demo=False, **vals)
    return C.ok()


@anvil.server.callable(require_user=True)
def my_practice():
    """Everything the Practice page needs: upcoming, history (for the journal and stats), wallet, follows."""
    me = C.require_user()
    staff, studios, rooms = (C.by_id(app_tables.staff.search()), C.by_id(app_tables.studios.search()),
                             C.by_id(app_tables.rooms.search()))
    now = C.now()
    upcoming, history, late = [], [], []
    for b in app_tables.bookings.search(user=me):
        k = b["klass"]
        if k is None:
            continue
        end = C.aware(k["start"]) + dt.timedelta(minutes=k["minutes"] or 60)
        d = Mo.booking_dict(b, Mo.class_dict(k, staff, studios, rooms))
        if b["status"] in ("booked", "waitlist") and end > now and k["status"] == "scheduled":
            upcoming.append(d)
        elif b["status"] in ("checked_in", "booked") and end <= now:
            history.append(d)
        elif b["status"] in ("late", "no_show"):
            late.append(d)
    upcoming.sort(key=lambda d: d["class"]["start"])
    history.sort(key=lambda d: d["class"]["start"], reverse=True)
    passes = [Mo.pass_dict(p) for p in app_tables.passes.search(user=me)]
    passes.sort(key=lambda p: (p["state"] != "active", p["expires"] or ""))
    follows = []
    for f in app_tables.follows.search(user=me):
        if f["studio"] is not None:
            follows.append({"kind": "studio", "slug": f["studio"]["slug"], "name": f["studio"]["name"], "accent": f["studio"]["accent"]})
        elif f["teacher"] is not None:
            st = f["teacher"]["studio"]
            follows.append({"kind": "teacher", "id": f["teacher"].get_id(), "name": f["teacher"]["name"],
                            "slug": st["slug"] if st else "", "studio": st["name"] if st else ""})
    sent = [{"code": f["code"], "studio": f["studio"]["name"], "claimed": f["claimed_by"] is not None, "created": C.iso(f["created"])}
            for f in app_tables.friend_passes.search(sender=me)]
    return {"upcoming": upcoming, "history": history[:200], "late": late[:20], "passes": passes, "follows": follows,
            "friend_passes": sent, "moods": MOODS}


@anvil.server.callable(require_user=True)
def pause_pass(pass_id, weeks):
    me = C.require_user()
    p = C.row_by_id(app_tables.passes, pass_id)
    if p is None or p["user"] != me:
        return C.fail("That pass isn't yours.")
    if p["kind"] != "unlimited":
        return C.fail("Only memberships can be paused.")
    if p["paused_until"] is not None:
        return C.fail("This membership has been paused already. Ask the studio for another pause.")
    if Mo.pass_state(p) != "active":
        return C.fail("Only an active membership can be paused.")
    weeks = int(C.num(weeks, 1, 1, 4))
    until = C.now() + dt.timedelta(weeks=weeks)
    future = [b for b in app_tables.bookings.search(user=me, pass_used=p)
              if b["status"] in ("booked", "waitlist") and C.aware(b["start"]) < until and C.aware(b["start"]) > C.now()]
    if future:
        return C.fail("Cancel your %s during the pause first." % UI_plural(len(future), "booking"))
    p.update(paused_until=until, expires=C.aware(p["expires"]) + dt.timedelta(weeks=weeks))
    C.notify(p["studio"]["owner"], p["studio"], "pause", "%s paused their membership" % C.name_of(me),
             "For %s. Their end date moved by the same time." % UI_plural(weeks, "week"), "")
    return C.ok(pass_=Mo.pass_dict(p))


def UI_plural(n, one):
    return "%d %s" % (n, one if n == 1 else one + "s")


@anvil.server.callable(require_user=True)
def reflect(booking_id, mood, note=""):
    me = C.require_user()
    b = _own_booking(booking_id, me)
    if b is None:
        return C.fail("That class isn't in your journal.")
    if b["status"] not in ("checked_in", "booked") or C.aware(b["start"]) > C.now():
        return C.fail("You can add a reflection after class.")
    mood = int(C.num(mood, 3, 1, 5))
    b.update(mood=mood, note=C.text(note, 600, multiline=True))
    return C.ok(mood=mood)


@anvil.server.callable(require_user=True)
def review_class(booking_id, stars, text=""):
    me = C.require_user()
    b = _own_booking(booking_id, me)
    if b is None or b["status"] not in ("checked_in", "booked") or C.aware(b["start"]) > C.now():
        return C.fail("Only people who came to the class can review it.")
    if b["reviewed"]:
        return C.fail("You already reviewed this class. Thank you!")
    stars = int(C.num(stars, 0, 0, 5))
    if stars < 1:
        return C.fail("Choose 1 to 5 stars.")
    k = b["klass"]
    s = b["studio"]
    app_tables.reviews.add_row(studio=s, klass=k, teacher=k["teacher"], user=me, booking=b, stars=stars,
                               text=C.text(text, 800, multiline=True), created=C.now(), reply="", reply_at=None,
                               hidden=False, is_demo=False)
    b["reviewed"] = True
    refresh_rating(s)
    return C.ok()


def refresh_rating(s):
    rows = [r for r in app_tables.reviews.search(studio=s) if not r["hidden"]]
    n = len(rows)
    s.update(rating=round(sum(r["stars"] for r in rows) / n, 2) if n else 0, rating_n=n)


# ----------------------------------------------------------------------------------------------- inbox

def _notice(n):
    s = n["studio"]
    return {"id": n.get_id(), "kind": n["kind"], "title": n["title"], "body": n["body"] or "", "link": n["link"] or "",
            "created": C.iso(n["created"]), "read": bool(n["read"]),
            "studio": {"slug": s["slug"], "name": s["name"], "accent": s["accent"]} if s else None}


@anvil.server.callable(require_user=True)
def inbox():
    me = C.require_user()
    rows = sorted(app_tables.notices.search(user=me), key=lambda n: C.aware(n["created"]), reverse=True)
    return {"items": [_notice(n) for n in rows[:100]], "unread": len([n for n in rows if not n["read"]])}


@anvil.server.callable(require_user=True)
def inbox_count():
    me = C.require_user()
    return len(app_tables.notices.search(user=me, read=False))


@anvil.server.callable(require_user=True)
def inbox_read(notice_id=None):
    me = C.require_user()
    if notice_id:
        n = C.row_by_id(app_tables.notices, notice_id)
        if n is None or n["user"] != me:
            return C.fail("That message isn't yours.")
        n["read"] = True
    else:
        for n in app_tables.notices.search(user=me, read=False):
            n["read"] = True
    return C.ok()


# ----------------------------------------------------------------------------------------------- friend passes

@anvil.server.callable(require_user=True)
def friend_pass_send(slug):
    me = C.require_user()
    s = Mo.studio_by_slug(slug)
    if s is None or s["status"] != "live":
        return C.fail("That studio isn't open.")
    if not any(p["kind"] in ("pack", "unlimited") and Mo.pass_state(p) == "active" for p in app_tables.passes.search(user=me, studio=s)):
        return C.fail("Friend passes come with a class pack or membership at %s." % s["name"])
    recent = [f for f in app_tables.friend_passes.search(sender=me, studio=s)
              if C.aware(f["created"]) > C.now() - dt.timedelta(days=30)]
    if len(recent) >= 2:
        return C.fail("You can share 2 friend passes a month per studio. More next month!")
    code = secrets.token_urlsafe(6).replace("-", "x").replace("_", "y")
    app_tables.friend_passes.add_row(studio=s, sender=me, code=code, created=C.now(), claimed_by=None, claimed_at=None, is_demo=False)
    return C.ok(code=code)


@anvil.server.callable
def friend_pass_get(code):
    f = app_tables.friend_passes.get(code=C.text(code, 20)) if code else None
    if f is None:
        return C.fail("That friend pass doesn't exist. Check the link?")
    me = C.me()
    s = f["studio"]
    return {"studio": Mo.studio_card(s), "from": C.first_name(f["sender"]), "claimed": f["claimed_by"] is not None,
            "mine": me is not None and f["claimed_by"] == me, "sender_is_me": me is not None and f["sender"] == me}


@anvil.server.callable(require_user=True)
def friend_pass_claim(code):
    me = C.require_user()
    f = app_tables.friend_passes.get(code=C.text(code, 20)) if code else None
    if f is None:
        return C.fail("That friend pass doesn't exist.")
    if f["sender"] == me:
        return C.fail("This one's for a friend! Send them the link.")
    if f["claimed_by"] is not None:
        return C.fail("This friend pass has been used already.") if f["claimed_by"] != me else C.ok(slug=f["studio"]["slug"])
    s = f["studio"]
    if Mo.has_visited(me, s):
        return C.fail("Friend passes are for a first visit to %s." % s["name"])
    now = C.now()
    app_tables.passes.add_row(user=me, studio=s, product=None, name="Friend pass from %s" % C.first_name(f["sender"]), kind="friend",
                              credits_total=1, credits_left=1, starts=now, expires=now + dt.timedelta(days=21), paused_until=None,
                              paid=True, pay_method="free", price=0, source="friend", created=now, is_demo=False)
    f.update(claimed_by=me, claimed_at=now)
    C.notify(f["sender"], s, "friend", "%s claimed your friend pass" % C.first_name(me),
             "They can come to a free class at %s. Book one together?" % s["name"], "#studio/" + s["slug"])
    return C.ok(slug=s["slug"])
