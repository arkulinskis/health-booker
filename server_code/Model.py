"""Shared rules and row -> dict helpers for Health Booker (no callables here).

Who can do what at a studio:
  - platform admins (users.is_admin) can manage every studio
  - staff rows: role "owner" or "desk" manage the studio; teachers (teaches=True) see their rosters
Passes: credits_left None = unlimited. A pass covers a class if it is active, not paused on that day,
starts before and expires after the class, and has a credit left (or is unlimited).
Bookings: booked -> checked_in | no_show | cancelled | late (late cancel keeps the credit used);
waitlist -> booked (promoted) | cancelled. classes.booked / classes.waiting are kept in step by recount().
"""
import datetime as dt

from anvil.tables import app_tables

from . import common as C

ACCENTS = ["sage", "clay", "lake", "plum", "sun", "moss"]
STYLES = ["Vinyasa", "Hatha", "Yin", "Restorative", "Hot", "Ashtanga", "Prenatal", "Pilates", "Breathwork",
          "Meditation", "Mobility", "Kids & family", "Chair", "Sound"]
LEVELS = ["all", "beginner", "intermediate", "advanced"]
TAGS = ["Beginner-friendly", "Props provided", "Heated", "Prenatal-safe", "Trauma-informed", "Chair-friendly",
        "Live music", "Candlelit", "En français", "Bilingual", "Silent", "Bring a baby"]
TAKES_MAT = ("booked", "checked_in", "no_show")
ACTIVE = ("booked", "waitlist", "checked_in")
PRODUCT_KINDS = ["intro", "dropin", "pack", "unlimited"]


# ----------------------------------------------------------------------------------------------- permissions

def staff_row(studio, user):
    if studio is None or user is None:
        return None
    for s in app_tables.staff.search(studio=studio, user=user):
        if s["active"] is not False:
            return s
    return None


def can_manage(studio, user):
    if user is None or studio is None:
        return False
    if C.is_admin(user):
        return True
    s = staff_row(studio, user)
    return bool(s and s["role"] in ("owner", "desk"))


def is_staff(studio, user):
    return C.is_admin(user) or staff_row(studio, user) is not None


def studio_by_slug(slug):
    if not isinstance(slug, str) or not slug:
        return None
    return app_tables.studios.get(slug=slug.strip().lower()[:60])


def visible(studio, user):
    """Live studios are public; others only to their staff and admins (preview)."""
    if studio is None:
        return False
    return studio["status"] == "live" or is_staff(studio, user)


# ----------------------------------------------------------------------------------------------- dicts

def studio_card(s, intro=None):
    return {"slug": s["slug"], "name": s["name"], "tagline": s["tagline"] or "", "neighbourhood": s["neighbourhood"] or "",
            "address": s["address"] or "", "city": s["city"] or "", "styles": s["styles"] or [],
            "amenities": s["amenities"] or [], "languages": s["languages"] or [], "accent": s["accent"] or "sage",
            "status": s["status"], "featured": bool(s["featured"]), "rating": s["rating"] or 0,
            "rating_n": s["rating_n"] or 0, "intro": intro, "demo": bool(s["is_demo"])}


def staff_dict(st, private=False):
    d = {"id": st.get_id(), "name": st["name"] or C.name_of(st["user"]), "bio": st["bio"] or "", "role": st["role"],
         "teaches": bool(st["teaches"]), "styles": st["styles"] or [], "invited": st["user"] is None}
    if private:
        d.update(email=st["email"] or (st["user"]["email"] if st["user"] else ""), pay_base=st["pay_base"] or 0,
                 pay_per_head=st["pay_per_head"] or 0, pay_after=st["pay_after"] or 0, active=st["active"] is not False)
    return d


def class_dict(c, staff=None, studios=None, rooms=None):
    """staff/studios/rooms: optional {id: row} caches so a long list doesn't fetch the same rows again."""
    t = _cached(c["teacher"], staff)
    o = _cached(c["orig_teacher"], staff)
    s = _cached(c["studio"], studios)
    r = _cached(c["room"], rooms)
    cap = c["capacity"] or 0
    booked = c["booked"] or 0
    return {"id": c.get_id(), "title": c["title"], "style": c["style"] or "", "level": c["level"] or "all",
            "intensity": c["intensity"] or 2, "heated": bool(c["heated"]), "tags": c["tags"] or [],
            "about": c["about"] or "", "start": C.iso(c["start"]), "minutes": c["minutes"] or 60, "capacity": cap,
            "booked": booked, "waiting": c["waiting"] or 0, "left": max(0, cap - booked), "kind": c["kind"] or "class",
            "price": c["price"] or 0, "status": c["status"] or "scheduled", "cancel_note": c["cancel_note"] or "",
            "series": c["series"] or "",
            "teacher": {"id": t.get_id(), "name": t["name"] or C.name_of(t["user"])} if t else None,
            "sub": bool(o is not None and t is not None and o != t),
            "orig_teacher": (o["name"] or "") if (o is not None and t is not None and o != t) else "",
            "room": {"id": r.get_id(), "name": r["name"]} if r else None,
            "studio": {"slug": s["slug"], "name": s["name"], "accent": s["accent"] or "sage",
                       "neighbourhood": s["neighbourhood"] or "", "address": s["address"] or "",
                       "cancel_hours": cancel_hours(s)} if s else None}


def _cached(row, cache):
    if row is None:
        return None
    if cache is not None:
        return cache.get(row.get_id(), row)
    return row


def cancel_hours(studio):
    v = studio["cancel_hours"] if studio is not None else None
    return 12 if v is None else v


def pass_state(p, at=None):
    at = at or C.now()
    if p["credits_left"] is not None and p["credits_left"] <= 0:
        return "used"
    if p["expires"] is not None and C.aware(p["expires"]) < at:
        return "expired"
    if p["paused_until"] is not None and C.aware(p["paused_until"]) > at:
        return "paused"
    return "active"


def pass_dict(p):
    s = p["studio"]
    return {"id": p.get_id(), "name": p["name"], "kind": p["kind"], "credits_left": p["credits_left"],
            "credits_total": p["credits_total"], "unlimited": p["credits_left"] is None and p["kind"] != "workshop",
            "starts": C.iso(p["starts"]), "expires": C.iso(p["expires"]), "paused_until": C.iso(p["paused_until"]),
            "state": pass_state(p), "paid": bool(p["paid"]), "price": p["price"] or 0, "source": p["source"] or "buy",
            "can_pause": p["kind"] == "unlimited" and p["paused_until"] is None and pass_state(p) == "active",
            "studio": {"slug": s["slug"], "name": s["name"], "accent": s["accent"] or "sage"} if s else None}


def product_dict(p):
    return {"id": p.get_id(), "name": p["name"], "kind": p["kind"], "credits": p["credits"], "days": p["days"] or 30,
            "price": p["price"] or 0, "intro_only": bool(p["intro_only"]), "about": p["about"] or "",
            "active": p["active"] is not False, "order": p["order"] or 0}


# ----------------------------------------------------------------------------------------------- passes + bookings

def covers(p, klass):
    """True if pass p can pay for klass."""
    if p is None or klass is None or p["studio"] != klass["studio"]:
        return False
    if p["kind"] == "workshop" or klass["kind"] == "workshop":
        return (p["kind"] == "workshop" and klass["kind"] == "workshop" and p["name"] == "Workshop: " + klass["title"]
                and (p["credits_left"] or 0) > 0)
    start = C.aware(klass["start"])
    if p["credits_left"] is not None and p["credits_left"] <= 0:
        return False
    if p["starts"] is not None and C.aware(p["starts"]) > start + dt.timedelta(hours=12):
        return False
    if p["expires"] is not None and C.aware(p["expires"]) < start:
        return False
    if p["paused_until"] is not None and C.aware(p["paused_until"]) > start:
        return False
    return True


def usable_passes(user, klass):
    if user is None:
        return []
    rows = [p for p in app_tables.passes.search(user=user, studio=klass["studio"]) if covers(p, klass)]
    # Spend what runs out first: soonest expiry, packs before unlimited.
    rows.sort(key=lambda p: (p["credits_left"] is None, C.aware(p["expires"]) if p["expires"] else C.now() + dt.timedelta(days=9999)))
    return rows


def visits(user, studio):
    return [b for b in app_tables.bookings.search(user=user, studio=studio) if b["status"] in ("checked_in", "booked", "no_show")]


def has_visited(user, studio):
    for b in app_tables.bookings.search(user=user, studio=studio):
        if b["status"] in ("checked_in", "booked", "no_show", "late"):
            return True
    return False


def recount(klass):
    booked = waiting = 0
    for b in app_tables.bookings.search(klass=klass):
        if b["status"] in TAKES_MAT:
            booked += 1
        elif b["status"] == "waitlist":
            waiting += 1
    klass.update(booked=booked, waiting=waiting)
    return booked, waiting


def spend(p):
    if p is not None and p["credits_left"] is not None:
        p["credits_left"] = max(0, p["credits_left"] - 1)


def refund(p):
    if p is not None and p["credits_left"] is not None:
        p["credits_left"] = min(p["credits_total"] or 99, p["credits_left"] + 1)


def promote(klass):
    """Move people from the waitlist into free mats, oldest first. Promoted inside the cancel window = grace
    (they may still cancel without losing the credit, since they didn't choose to be booked that late)."""
    promoted = []
    if klass["status"] != "scheduled" or C.aware(klass["start"]) < C.now():
        return promoted
    booked, _ = recount(klass)
    if booked >= (klass["capacity"] or 0):
        return promoted
    waiting = sorted([b for b in app_tables.bookings.search(klass=klass, status="waitlist")],
                     key=lambda b: C.aware(b["wl_at"] or b["created"]))
    window = dt.timedelta(hours=cancel_hours(klass["studio"]))
    for b in waiting:
        if booked >= (klass["capacity"] or 0):
            break
        p = b["pass_used"]
        if p is None or not covers(p, klass):
            alt = usable_passes(b["user"], klass)
            p = alt[0] if alt else None
        if p is None:
            continue
        spend(p)
        late = C.aware(klass["start"]) - C.now() < window
        b.update(status="booked", pass_used=p, grace=late, updated=C.now())
        booked += 1
        promoted.append(b)
        C.notify(b["user"], klass["studio"], "waitlist", "You're in: %s" % klass["title"],
                 "A mat opened up and you moved off the waitlist. %s" % (
                     "It's close to class time, so you can still cancel for free if you can't make it." if late else "See you on the mat!"),
                 "#class/" + klass.get_id())
    recount(klass)
    return promoted


def booking_dict(b, klass_d=None):
    k = b["klass"]
    s = k["studio"] if k else None
    start = C.aware(k["start"]) if k else None
    cutoff = start - dt.timedelta(hours=cancel_hours(s)) if start else None
    pos = None
    if b["status"] == "waitlist" and k is not None:
        ahead = [w for w in app_tables.bookings.search(klass=k, status="waitlist")
                 if C.aware(w["wl_at"] or w["created"]) < C.aware(b["wl_at"] or b["created"])]
        pos = len(ahead) + 1
    p = b["pass_used"]
    return {"id": b.get_id(), "status": b["status"], "spot": b["spot"] or "", "first_visit": bool(b["first_visit"]),
            "class": klass_d or (class_dict(k) if k else None), "pass_name": p["name"] if p else "",
            "mood": b["mood"], "note": b["note"] or "", "reviewed": bool(b["reviewed"]), "waitlist_pos": pos,
            "grace": bool(b["grace"]), "cancel_by": C.iso(cutoff),
            "late_if_cancel": bool(cutoff and C.now() > cutoff and not b["grace"] and b["status"] == "booked")}


def shop(user, studio):
    """The studio's passes for sale, with eligible=False on intro offers for people who've been before."""
    visited = bool(user and has_visited(user, studio))
    had_intro = bool(user and any(p["kind"] in ("intro", "friend") for p in app_tables.passes.search(user=user, studio=studio)))
    out = []
    for p in app_tables.products.search(studio=studio):
        if p["active"] is False or p["kind"] not in PRODUCT_KINDS:
            continue
        d = product_dict(p)
        d["eligible"] = not d["intro_only"] or not (visited or had_intro)
        out.append(d)
    out.sort(key=lambda d: d["order"])
    return out
