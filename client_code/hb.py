"""Health Booker's shared client helpers (the old window.HB): studio accents, money and time wording, small display
pieces (tags, stars, intensity leaves), files, and the flows several pages share: booking (waiver -> pass -> book ->
the breathing confirmation), cancelling, reflections + reviews, the class list (roster) and marking a pass paid.

Local times come from the browser (theme/assets/hb-draw.js, window.HBD.fmt), so they show in the visitor's own zone.
Booking rules live on the server (Booking.py / Model.py); this module only asks and shows what the server says.
"""
import json

import anvil.js
import anvil.server
from anvil import alert, confirm
from anvil.js import window

from . import router, state

ACCENTS = ["sage", "clay", "lake", "plum", "sun", "moss"]
LEVEL = {"all": "All levels", "beginner": "Beginner", "intermediate": "Intermediate", "advanced": "Advanced"}
MOODS = ["Heavy", "Tired", "Okay", "Light", "Glowing"]
INTENSITY = ["", "Very gentle", "Gentle", "Moderate", "Strong", "Very strong"]
KIND = {"intro": "Intro offer", "dropin": "Drop-in", "pack": "Class pack", "unlimited": "Membership",
        "friend": "Friend pass", "workshop": "Workshop"}
STYLES = ["Vinyasa", "Hatha", "Yin", "Restorative", "Hot", "Ashtanga", "Prenatal", "Pilates", "Breathwork",
          "Meditation", "Mobility", "Kids & family", "Chair", "Sound"]


def loose(x):
    """Pass dynamic values the type checker can't follow (JS objects, dom_nodes keys) through untyped."""
    return x


# ---------------------------------------------------------------- accents
def acc(key):
    return "acc-" + (key if key in ACCENTS else "sage")


def set_acc(component, key):
    """Give a component (or a plain DOM node) the studio's accent: .acc-<key> sets --acc / --acc-soft inside."""
    node = component if hasattr(component, "classList") else anvil.js.get_dom_node(component)
    for k in ACCENTS:
        node.classList.remove("acc-" + k)
    node.classList.add(acc(key))


# ---------------------------------------------------------------- words for numbers and times
def plural(n, one, many=None):
    return state.plural(n, one, many)


def money(n):
    n = float(n or 0)
    if not n:
        return "Free"
    if n % 1:
        return "$%.2f" % n
    return "$" + "{:,}".format(int(n))


def money0(n):
    return money(n) if n else "$0"


def mins(m):
    m = int(m or 0)
    if m >= 60:
        return "%dh%s" % (m // 60, (" %d" % (m % 60)) if m % 60 else "")
    return "%d min" % m


def _f():
    return window.HBD.fmt


def time(iso):
    return str(_f().time(iso))


def time_parts(iso):
    p = _f().timeParts(iso)
    return str(p[0]), str(p[1])


def rel_day(iso):
    return str(_f().relDay(iso))


def date(iso):
    return str(_f().date(iso))


def when(iso):
    return str(_f().when(iso)) if iso else ""


def day_key(iso):
    return str(_f().dayKey(iso))


def day_long(iso):
    return str(_f().dayLong(iso))


def day_month(iso):
    return str(_f().dayMonth(iso))


def full_date(iso):
    return str(_f().fullDate(iso)) if iso else ""


def ago(iso):
    return str(_f().ago(iso)) if iso else ""


def start_of_day(offset=0):
    return str(_f().startOfDay(offset))


def add_days(iso, n):
    return str(_f().addDays(iso, n))


def ms(iso):
    return float(_f().ms(iso))


def now_ms():
    return float(_f().now())


def first_name(name):
    return (name or "").split(" ")[0]


def ordinal(n):
    return "%d%s" % (n, {1: "st", 2: "nd", 3: "rd"}.get(n if n < 20 else n % 10, "th"))


# ---------------------------------------------------------------- small display pieces (DOM, no HTML strings)
def text(node, value):
    node.textContent = "" if value is None else str(value)


def _el(tag, cls=None, value=None):
    e = window.document.createElement(tag)
    if cls:
        e.className = cls
    if value is not None:
        e.textContent = str(value)
    return e


def fill(node, parts):
    """Replace node's children with small labels: parts = [(text, css class, icon name or None)]."""
    node.textContent = ""
    for p in parts:
        value, cls, icon = (list(p) + [None, None])[:3]
        span = _el("span", cls or "hb-tag")
        if icon:
            span.appendChild(_el("i", "ic ic-" + icon))
        span.appendChild(window.document.createTextNode(str(value)))
        node.appendChild(span)


def class_tags(c, all_tags=False):
    """The little labels under a class: style, level, heat, workshop price, who's subbing, then its tags."""
    tags = [(c.get("style") or "", "hb-tag", None)]
    if c.get("level") and c["level"] != "all":
        tags.append((LEVEL.get(c["level"], c["level"]), "hb-tag", None))
    if c.get("heated"):
        tags.append(("Heated", "hb-tag heat", "flame"))
    if c.get("kind") == "workshop":
        tags.append(("Workshop · " + money(c.get("price")), "hb-tag heat", None))
    if c.get("sub"):
        t = c.get("teacher") or {}
        tags.append(("Sub: %s for %s" % (first_name(t.get("name")), first_name(c.get("orig_teacher"))), "hb-tag sub", None))
    extra = [t for t in (c.get("tags") or []) if t != "Heated"]
    for t in extra[: (9 if all_tags else 2)]:
        tags.append((t, "hb-tag", None))
    return tags


def stars(node, n):
    """Five stars, filled up to n (rounded), read out as 'n out of 5 stars'."""
    node.textContent = ""
    node.className = "hb-stars"
    node.setAttribute("role", "img")
    node.setAttribute("aria-label", "%s out of 5 stars" % (int(n) if float(n) == int(n) else round(float(n), 1)))
    for i in range(1, 6):
        node.appendChild(_el("i", "ic ic-starfill on" if i <= round(float(n or 0)) else "ic ic-star"))


def leaves(node, n):
    node.textContent = ""
    node.className = "hb-leaves"
    node.setAttribute("role", "img")
    node.setAttribute("aria-label", "Intensity %d of 5" % int(n or 0))
    node.setAttribute("title", "Intensity %d of 5" % int(n or 0))
    for i in range(1, 6):
        node.appendChild(_el("i", "on" if i <= int(n or 0) else ""))


def spots(c):
    """('Only 2 mats left', 'low') for a class card."""
    if c.get("status") == "cancelled":
        return "Cancelled", ""
    left = c.get("left") or 0
    if left <= 0:
        return "Full" + (" · %d waiting" % c["waiting"] if c.get("waiting") else ""), "low"
    return ("Only " if left <= 3 else "") + plural(left, "mat") + " left", "low" if left <= 3 else ""


def rating_text(r, n):
    return ("%.1f (%d)" % (float(r or 0), n)) if n else "New on Health Booker"


# ---------------------------------------------------------------- files
def ics(c):
    window.HBD.ics(json.dumps(c))


def download(name, body, kind="text/plain"):
    window.HBD.download(name, body, kind)


def link(hash_text):
    return str(window.HBD.link(hash_text))


def copy(value, message="Link copied."):
    if window.HBD.copy(value):
        state.toast(message, "ok")


def csv_text(rows):
    return "\n".join(",".join('"' + str(v if v is not None else "").replace('"', '""') + '"' for v in r) for r in rows)


def chart(node, kind, data):
    window.HBD.chart(node, kind, json.dumps(data))


# ---------------------------------------------------------------- the bell
_unread: dict = {"at": 0.0}


def refresh_unread(force=False):
    """The bell's count: asked quietly when the page changes (at most every 20 seconds), or now after a booking."""
    me = state.me()
    if not me or (not force and now_ms() - _unread["at"] < 20000):
        return
    _unread["at"] = now_ms()
    n = state.call_quiet("inbox_count")
    if n is not None and state.me() and me.get("unread") != n:
        me["unread"] = n
        router.refresh_shell()


# ---------------------------------------------------------------- booking flow
def _dialog(form, large=False):
    return alert(form, buttons=[], large=large, role="app-dialog", dismissible=True)


def book(c, pass_id=None, spot=None):
    """Book a class (or join its waitlist). The server says what's missing: a waiver (sign it here, once per studio)
    or a pass (choose one: paid at the studio). Returns the booking dict, or None."""
    if not state.me():
        router.need_account("#class/" + c["id"], "Create your free account to book. One account works at every studio.")
        return None
    r = anvil.server.call("book_class", c["id"], pass_id, spot)
    if r.get("ok"):
        booked(r["booking"])
        refresh_unread(True)
        return r["booking"]
    if r.get("need") == "waiver":
        return book(c, pass_id, spot) if waiver(c["studio"], r.get("waiver_text") or "") else None
    if r.get("need") == "pass":
        p = shop(c["studio"], r.get("products") or [], c)
        return book(c, p["id"], spot) if p else None
    state.toast(r.get("error") or "That didn't work.", "error")
    return None


def waiver(studio, waiver_text):
    from .Dialogs.Waiver import Waiver
    return bool(_dialog(Waiver(studio=studio, waiver_text=waiver_text)))


def shop(studio, products, klass=None):
    """Choose and get a pass for a studio (paid at the desk). Returns the new pass dict, or None."""
    from .Dialogs.Shop import Shop
    return _dialog(Shop(studio=studio, products=products, klass=klass))


def booked(b):
    from .Dialogs.Booked import Booked
    _dialog(Booked(booking=b))


def cancel(b):
    """Cancel a booking or leave a waitlist, with the studio's cancel window spelled out first. True when done."""
    c = b["class"]
    hrs = (c.get("studio") or {}).get("cancel_hours", 12)
    if b["status"] == "waitlist":
        title, body, ok, keep = "Leave the waitlist?", "You won't be moved into %s if a mat opens up." % c["title"], "Leave waitlist", "Cancel"
    elif b.get("late_if_cancel"):
        title = "Late cancel?"
        body = ("It's less than %s hours before class, so this class still counts against your pass. The studio may "
                "forgive it." % hrs)
        ok, keep = "Cancel anyway", "Keep it"
    else:
        title = "Cancel this class?"
        body = "Your credit goes straight back to your wallet" + (
            " (you were moved off the waitlist late, so it's free)." if b.get("grace") else ".")
        ok, keep = "Cancel class", "Keep it"
    if not confirm(body, title=title, buttons=[(keep, False), (ok, True)], role="app-dialog"):
        return False
    r = state.call("cancel_booking", b["id"])
    if not r:
        return False
    res = r.get("result")
    state.toast("Cancelled (late). Your mat goes to the next person waiting." if res == "late"
                else "You left the waitlist." if res == "left_waitlist" else "Cancelled. Your credit is back.", "ok")
    return True


def reflect(b):
    """How do you feel after class (only you see it) + an optional public review. True when something was saved."""
    from .Dialogs.Reflect import Reflect
    return bool(_dialog(Reflect(booking=b)))


def roster(class_id):
    """The class list with check-in (teachers, front desk, owners). True if anything changed."""
    from .Dialogs.Roster import Roster
    f = Roster(class_id=class_id)
    _dialog(f, large=True)
    return f.changed


def mark_paid(pass_id):
    from .Dialogs.MarkPaid import MarkPaid
    return bool(_dialog(MarkPaid(pass_id=pass_id)))


def ask(form, large=False):
    """Any of the app's dialog Forms (they close themselves with x-close-alert)."""
    return _dialog(form, large)


def face(node, mood):
    window.HBD.face(node, int(mood or 3))


def by_day(rows, start_of=None):
    """Group row items by local day: [{label: 'Today', sub: '5 November', rows: [...]}]. start_of(row) -> ISO start."""
    get = start_of or (lambda r: r["c"]["start"])
    groups: list = []
    last = None
    for r in rows:
        k = day_key(get(r))
        if k != last:
            groups.append({"label": rel_day(get(r)), "sub": day_long(get(r)), "rows": []})
            last = k
        groups[-1]["rows"].append(r)
    return groups
