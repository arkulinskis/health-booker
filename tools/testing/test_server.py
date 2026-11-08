"""Server tests against the strict mock of Anvil (tools/testing/mock).

    python tools/testing/test_server.py          -> prints ALL OK, or the first failure

call(name, ...) runs a server function the way the browser does: by name, with require_user enforced,
and the reply must be JSON (a datetime or a row in a reply fails here, like it would break the page).
Add tests for every new server function: the happy path, bad input, and someone who isn't allowed.
"""
import datetime as dt
import importlib
import json
import os
import pathlib
import shutil
import sys
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
PROJECT = HERE.parents[1]
_tmp = pathlib.Path(tempfile.mkdtemp())
shutil.copytree(PROJECT / "server_code", _tmp / "app")
(_tmp / "app" / "__init__.py").write_text("")
os.environ["ANVIL_APP_YAML"] = str(PROJECT / "anvil.yaml")  # the mock's tables follow the app's own schema
sys.path[:0] = [str(HERE / "mock"), str(_tmp)]
import anvil.server  # noqa: E402
import anvil.users  # noqa: E402
from anvil.tables import app_tables as T  # noqa: E402

M = {p.stem: importlib.import_module("app." + p.stem) for p in sorted((PROJECT / "server_code").glob("*.py"))}
now = dt.datetime.now(dt.timezone.utc)


def call(name, *args):
    r = anvil.server.call(name, *args)
    json.dumps(r)  # strict: must be JSON-able
    _string_keys(r, name)
    return r


def _string_keys(v, where):
    """Anvil refuses to send dicts with non-string keys (json.dumps quietly turns 1 into "1")."""
    if isinstance(v, dict):
        for k, x in v.items():
            assert isinstance(k, str), "%s: a dict key isn't a string (%r): Anvil can't send it" % (where, k)
            _string_keys(x, where)
    elif isinstance(v, (list, tuple)):
        for x in v:
            _string_keys(x, where)


def as_user(row):
    anvil.users.CURRENT[0] = row
    anvil.server.session.use(row.get_id() if row is not None else None)


def denied(name, *args):
    try:
        call(name, *args)
    except anvil.server.PermissionDenied:
        return True
    return False


def ok(r, msg=""):
    assert isinstance(r, dict) and r.get("ok"), (msg, r)
    return r


def bad(r, msg=""):
    assert isinstance(r, dict) and r.get("ok") is False and r.get("error"), (msg, r)
    return r


def person(email, name=None, **kw):
    return T.users.add_row(email=email, enabled=True, signed_up=now, display_name=name, **kw)


# ---------------------------------------------------------------------------------- accounts
admin = person("arkulinskis@gmail.com", "The Admin")
ana = person("ana@example.com", "Ana")
bob = person("bob@example.com")

as_user(None)
assert call("get_me") is None
assert denied("update_profile", "X")
as_user(admin)
assert call("get_me")["is_admin"] is True, "ADMIN_EMAILS become admins on first sign-in"
as_user(ana)
me = call("get_me")
assert me["name"] == "Ana" and me["is_admin"] is False
assert ana["last_seen"] is not None
as_user(bob)
assert call("get_me")["name"] == "Bob", "a name comes from the email when none is set"
bad(call("update_profile", " x "))
assert ok(call("update_profile", "  Bob   Stone "))["me"]["name"] == "Bob Stone"

# ---------------------------------------------------------------------------------- feedback
as_user(None)
bad(call("submit_feedback", "bug", "hi"))
ok(call("submit_feedback", "bug", "The button is broken", "guest@example.com", {"page": "#home", "evil": "x" * 9999}))
fb = T.feedback.search()[0]
assert fb["name"] == "Guest" and fb["email"] == "guest@example.com" and "evil" not in fb["context"] and fb["status"] == "new"
for i in range(4):
    ok(call("submit_feedback", "idea", "Idea number %d" % i))
bad(call("submit_feedback", "idea", "One too many this hour"), "rate limit")
as_user(ana)
ok(call("submit_feedback", "nonsense-kind", "Signed-in feedback"))
assert T.feedback.get(message="Signed-in feedback")["kind"] == "other"
assert denied("list_feedback")
as_user(admin)
lst = call("list_feedback")
assert lst["counts"]["new"] == 6 and len(lst["items"]) == 6
fid = lst["items"][0]["id"]
ok(call("set_feedback_status", fid, "done", "Fixed it"))
assert call("list_feedback", "done")["items"][0]["note"] == "Fixed it"
bad(call("set_feedback_status", fid, "weird"))
bad(call("set_feedback_status", "nope", "done"))
ok(call("delete_feedback", fid))
assert len(call("list_feedback")["items"]) == 5

# ---------------------------------------------------------------------------------- admin
as_user(ana)
for fn, args in [("admin_overview", ()), ("list_users", ()), ("set_admin", (bob.get_id(), True)), ("demo_load", ()), ("demo_remove", ())]:
    assert denied(fn, *args), fn
as_user(admin)
ov = call("admin_overview")
assert ov["users"] == 3 and ov["admins"] == 1 and ov["feedback_new"] == 5
assert len(call("list_users")["users"]) == 3 and len(call("list_users", "bob")["users"]) == 1
ok(call("set_admin", bob.get_id(), True))
assert bob["is_admin"] is True
bad(call("set_admin", admin.get_id(), False), "can't remove your own admin")
ok(call("set_enabled", bob.get_id(), False))
assert bob["enabled"] is False
bad(call("set_enabled", admin.get_id(), False))
ok(call("set_enabled", bob.get_id(), True))
ok(call("set_admin", bob.get_id(), False))
assert bob["is_admin"] is False

# ---------------------------------------------------------------------------------- Health Booker
import datetime as _dt  # noqa: E402

# --- the marketplace (anyone)
as_user(None)
d = call("discover")
assert M["DemoData"].state() == "loaded", "demo loads on first visit"
assert d["classes"] and len(d["studios"]) == 5, "5 live demo studios (Kula Laval is in review)"
assert all(c["studio"]["slug"] != "kula-laval" for c in d["classes"])
assert d["classes"] == sorted(d["classes"], key=lambda c: c["start"])
bad(call("get_studio", "kula-laval"), "studios in review are hidden from the public")
bad(call("get_studio", "nope"))
sg = call("get_studio", "sage-and-stone")
assert sg["classes"] and sg["products"] and sg["teachers"] and sg["reviews"] and not sg["can_manage"]
assert any(p["intro_only"] and p["eligible"] for p in sg["products"])
assert M["DemoData"].top_up() == 0, "top-up does nothing when the schedule is far enough ahead"
cands = [c for c in sg["classes"] if c["left"] > 3 and c["kind"] == "class" and c["start"] > (now + _dt.timedelta(days=1)).isoformat()]
c0 = cands[0]
g = call("get_class", c0["id"])
assert g["room"] and g["booking"] is None and not g["is_staff"]
bad(call("get_class", "nope"))
for fn, args in [("book_class", (c0["id"],)), ("toggle_follow", ("studio", "sage-and-stone")), ("my_practice", ()), ("buy_product", ("x",)),
                 ("manage_list", ()), ("teach_home", ()), ("create_studio", ({},)), ("inbox", ())]:
    assert denied(fn, *args), fn
assert any(c["waiting"] and c["booked"] >= c["capacity"] for c in T.classes.search() if c["start"] > now), "the demo has a full class with a waitlist"

# --- a new student books: waiver -> pass -> mat
as_user(bob)
r = bad(call("book_class", c0["id"]))
assert r["need"] == "waiver" and r["waiver_text"]
bad(call("sign_waiver", "sage-and-stone", "x"))
bad(call("sign_waiver", "nowhere", "Bob Stone"))
ok(call("sign_waiver", "sage-and-stone", "Bob Stone", "Jo 555-0100", "Sore left knee", True))
r = bad(call("book_class", c0["id"]))
assert r["need"] == "pass"
intro = [p for p in r["products"] if p["intro_only"]][0]
assert intro["eligible"]
bp = ok(call("buy_product", intro["id"]))["pass_"]
assert bp["paid"] is False and bp["unlimited"] and bp["state"] == "active"
bad(call("buy_product", intro["id"]), "one intro offer per person per studio")
bad(call("buy_product", "nope"))
room = g["room"]
spots = ["%s%d" % (chr(65 + r_), k + 1) for r_ in range(room["rows"]) for k in range(room["cols"])]
free = [s for s in spots if s not in g["taken"] and s not in room["blocked"]]
bad(call("book_class", c0["id"], None, "Z9"), "a mat that isn't in the room")
b = ok(call("book_class", c0["id"], None, free[0]))["booking"]
assert b["status"] == "booked" and b["spot"] == free[0] and b["first_visit"] and b["cancel_by"]
assert ok(call("book_class", c0["id"]))["booking"]["id"] == b["id"], "booking twice gives the same booking"
assert call("get_class", c0["id"])["booking"]["id"] == b["id"]

# --- someone else can't take the same mat
as_user(ana)
ok(call("sign_waiver", "sage-and-stone", "Ana Lima"))
packs = [p for p in call("get_studio", "sage-and-stone")["products"] if p["kind"] == "pack"]
ana_pack = ok(call("buy_product", packs[-1]["id"]))["pass_"]
assert ana_pack["credits_left"] == 10
bad(call("book_class", c0["id"], None, free[0]), "that mat is taken")
bad(call("book_class", c0["id"], "nope"), "a pass that isn't yours")

# --- the owner adds classes; waitlist + promotion
maya = T.users.get(email="maya.demo@example.com")
theo = T.users.get(email="theo.demo@example.com")
samir = T.users.get(email="samir.demo@example.com")
as_user(bob)
for fn, args in [("manage_day", ("sage-and-stone",)), ("manage_schedule", ("sage-and-stone",)), ("save_class", ("sage-and-stone", {})),
                 ("clients", ("sage-and-stone",)), ("insights", ("sage-and-stone",)), ("export_csv", ("sage-and-stone", "clients")),
                 ("manage_settings", ("sage-and-stone",)), ("kiosk_day", ("sage-and-stone",))]:
    assert denied(fn, *args), fn
as_user(maya)
me_m = call("get_me")
assert me_m["manages"] and me_m["teaches"] and me_m["roles"][0]["slug"] == "sage-and-stone"
assert [s["slug"] for s in call("manage_list")] == ["sage-and-stone"]
denied("manage_day", "lumen-hot-yoga")
sch = call("manage_schedule", "sage-and-stone", now.isoformat(), 7)
assert sch["classes"] and sch["teachers"] and len(sch["rooms"]) == 2
theo_staff = [t for t in sch["teachers"] if t["name"] == "Theo Martin"][0]
room0 = sch["rooms"][0]
when = (now + _dt.timedelta(days=2)).replace(microsecond=0)
base = {"title": "Test Flow", "style": "Vinyasa", "level": "all", "teacher_id": theo_staff["id"], "room_id": room0["id"],
        "start": when.isoformat(), "minutes": 60, "capacity": 1, "repeat_weeks": 2, "tags": ["Beginner-friendly", "Nope"]}
bad(call("save_class", "sage-and-stone", dict(base, title="x")))
bad(call("save_class", "sage-and-stone", dict(base, start="soon")))
other_teacher = T.staff.search(studio=T.studios.get(slug="lumen-hot-yoga"))[0]
bad(call("save_class", "sage-and-stone", dict(base, teacher_id=other_teacher.get_id())), "teachers from another studio")
assert ok(call("save_class", "sage-and-stone", base))["count"] == 2
tests = sorted([c for c in T.classes.search(title="Test Flow")], key=lambda c: c["start"])
assert len(tests) == 2 and tests[0]["tags"] == ["Beginner-friendly"] and tests[0]["capacity"] == 1
t1 = tests[0].get_id()
as_user(bob)
b1 = ok(call("book_class", t1))["booking"]
assert b1["status"] == "booked"
as_user(ana)
w = ok(call("book_class", t1))["booking"]
assert w["status"] == "waitlist" and w["waitlist_pos"] == 1
assert T.passes.get_by_id(ana_pack["id"])["credits_left"] == 10, "joining a waitlist doesn't spend a credit"
as_user(bob)
bad(call("cancel_booking", w["id"]), "can't cancel someone else's booking")
assert ok(call("cancel_booking", b1["id"]))["result"] == "refunded"
as_user(ana)
mine = call("get_class", t1)["booking"]
assert mine["status"] == "booked", "the waitlist moves up automatically"
assert T.passes.get_by_id(ana_pack["id"])["credits_left"] == 9
assert any(n["kind"] == "waitlist" for n in call("inbox")["items"])
assert call("inbox_count") >= 1
ok(call("inbox_read"))
assert call("inbox_count") == 0

# --- late cancel, and the owner forgives it
as_user(maya)
soon = (now + _dt.timedelta(hours=3)).replace(microsecond=0)
ok(call("save_class", "sage-and-stone", dict(base, title="Soon Flow", start=soon.isoformat(), capacity=5, repeat_weeks=1)))
sid = T.classes.get(title="Soon Flow").get_id()
as_user(ana)
lb = ok(call("book_class", sid))["booking"]
assert lb["late_if_cancel"] is True
assert ok(call("cancel_booking", lb["id"]))["result"] == "late"
assert T.passes.get_by_id(ana_pack["id"])["credits_left"] == 8, "a late cancel keeps the credit used"
as_user(theo)
assert denied("forgive", lb["id"]), "teachers can't forgive; owners and desk can"
as_user(maya)
ok(call("forgive", lb["id"]))
assert T.passes.get_by_id(ana_pack["id"])["credits_left"] == 9
bad(call("forgive", lb["id"]), "only once")

# --- roster, check-in, walk-ins, payments
as_user(theo)
ro = call("roster", t1)
assert ro["people"][0]["name"] == "Ana" and not ro["can_manage"]
ok(call("set_attendance", ro["people"][0]["id"], "checked_in"))
bad(call("set_attendance", ro["people"][0]["id"], "dancing"))
as_user(bob)
assert denied("roster", t1)
as_user(maya)
ok(call("add_walkin", sid, "Walk-in Wendy"))
ok(call("add_walkin", sid, "", "bob@example.com"))
bad(call("add_walkin", sid, "", "bob@example.com"), "already on the list")
bad(call("add_walkin", sid, "x"))
ro2 = call("roster", sid)
assert ro2["can_manage"] and {p["name"] for p in ro2["people"]} >= {"Walk-in Wendy", "Bob Stone"}
assert any(p["health"] == "Sore left knee" for p in ro2["people"]), "shared health notes show on the class list"
as_user(bob)
assert denied("mark_paid", bp["id"])
as_user(maya)
ok(call("mark_paid", bp["id"], "cash"))
assert T.passes.get_by_id(bp["id"])["paid"] is True
day = call("manage_day", "sage-and-stone", (now - _dt.timedelta(hours=1)).isoformat(), (now + _dt.timedelta(days=1)).isoformat())
assert any(c["title"] == "Soon Flow" for c in day["classes"]) and "unpaid" in day
assert call("kiosk_day", "sage-and-stone", now.isoformat(), (now + _dt.timedelta(days=1)).isoformat())["classes"]

# --- cancelling a class gives credits back
as_user(ana)
w2 = ok(call("book_class", tests[1].get_id()))["booking"]
assert w2["status"] == "booked" and T.passes.get_by_id(ana_pack["id"])["credits_left"] == 8
as_user(maya)
assert ok(call("cancel_class", tests[1].get_id(), "Teacher is sick"))["notified"] == 1
assert T.passes.get_by_id(ana_pack["id"])["credits_left"] == 9
ok(call("restore_class", tests[1].get_id()))
bad(call("restore_class", tests[1].get_id()))
edited = ok(call("save_class", "sage-and-stone", dict(base, id=t1, title="Test Flow Plus", scope="future", capacity=4)))
assert edited["count"] == 2 and T.classes.get_by_id(t1)["title"] == "Test Flow Plus"

# --- clients, messages, pricing, team
cl = call("clients", "sage-and-stone")
bob_row = [c for c in cl["clients"] if c["email"] == "bob@example.com"][0]
assert "new" in bob_row["tags"] and cl["counts"]["drifting"] > 0
det = call("client_detail", "sage-and-stone", bob.get_id())
assert det["waiver"]["health"] == "Sore left knee" and det["passes"]
bad(call("client_detail", "sage-and-stone", admin.get_id()), "not a client")
ok(call("nudge", "sage-and-stone", bob.get_id(), "We miss you, Bob!"))
bad(call("nudge", "sage-and-stone", admin.get_id(), "Hello there"), "only your own clients")
bad(call("nudge", "sage-and-stone", bob.get_id(), "hi"))
pr = call("manage_products", "sage-and-stone")
assert pr["products"] and any(p["sold"] for p in pr["products"])
ok(call("save_product", "sage-and-stone", {"name": "Student month", "kind": "unlimited", "days": 30, "price": 99}))
sm = [p for p in call("manage_products", "sage-and-stone")["products"] if p["name"] == "Student month"][0]
assert sm["credits"] is None and sm["active"]
ok(call("save_product", "sage-and-stone", dict(sm, price=89, active=False)))
assert not [p for p in call("get_studio", "sage-and-stone")["products"] if p["name"] == "Student month"], "hidden passes aren't for sale"
bad(call("save_product", "sage-and-stone", {"name": "x"}))
tm = call("team", "sage-and-stone")
assert len(tm["team"]) == 4 and tm["subs"]
theo_row = [t for t in tm["team"] if t["name"] == "Theo Martin"][0]
assert theo_row["classes"] > 0 and theo_row["pay"] > 0
assert ok(call("save_staff", "sage-and-stone", {"email": "newteacher@example.com", "name": "Nova Teacher", "pay_base": 35}))["invited"] is True
bad(call("save_staff", "sage-and-stone", {"email": "newteacher@example.com", "name": "Nova Again"}), "already on the team")
bad(call("save_staff", "sage-and-stone", {"email": "nope", "name": "X Y"}))
owner_row = [t for t in tm["team"] if t["role"] == "owner"][0]
bad(call("save_staff", "sage-and-stone", dict(owner_row, role="teacher")), "a studio keeps an owner")
bad(call("remove_staff", owner_row["id"]))
bad(call("remove_staff", theo_row["id"]), "teachers with upcoming classes can't be removed")
nova = person("newteacher@example.com", "Nova")
as_user(nova)
assert call("get_me")["roles"][0]["slug"] == "sage-and-stone", "an invite becomes yours when you sign in"
assert call("teach_home")["teaching"] is True
as_user(maya)
nova_id = [t for t in call("team", "sage-and-stone")["team"] if t["name"] == "Nova Teacher"][0]["id"]
ok(call("remove_staff", nova_id))
as_user(nova)
assert call("get_me")["roles"] == []

# --- insights, reviews, settings, export
as_user(maya)
ins = call("insights", "sage-and-stone", 28)
assert ins["visits"] > 0 and ins["classes"] > 0 and ins["heat"] and ins["funnel"]["started"] > 0 and ins["top"]
rv = call("manage_reviews", "sage-and-stone")["reviews"]
ok(call("reply_review", rv[0]["id"], "Thank you!"))
n_before = T.studios.get(slug="sage-and-stone")["rating_n"]
ok(call("hide_review", rv[0]["id"], True))
assert T.studios.get(slug="sage-and-stone")["rating_n"] == n_before - 1
ok(call("hide_review", rv[0]["id"], False))
st = call("manage_settings", "sage-and-stone")
bad(call("save_studio", "sage-and-stone", dict(st["studio"], name="x")))
ok(call("save_studio", "sage-and-stone", dict(st["studio"], cancel_hours=6, accent="nope")))
assert T.studios.get(slug="sage-and-stone")["cancel_hours"] == 6 and T.studios.get(slug="sage-and-stone")["accent"] == "sage"
ok(call("save_room", "sage-and-stone", {"name": "Studio B", "rows": 2, "cols": 3, "blocked": ["A1", "Z9"]}))
assert T.rooms.get(name="Studio B")["blocked"] == ["A1"]
bad(call("save_room", "sage-and-stone", {"name": "Tiny", "rows": 1, "cols": 1, "blocked": ["A1"]}))
for kind in ("clients", "bookings", "passes"):
    ex = ok(call("export_csv", "sage-and-stone", kind))
    assert ex["csv"].count("\n") > 3 and ex["filename"].endswith(".csv")
bad(call("export_csv", "sage-and-stone", "secrets"))

# --- teachers: subs and pay
as_user(theo)
th = call("teach_home", (now - _dt.timedelta(days=30)).isoformat(), now.isoformat())
assert th["teaching"] and th["upcoming"] and th["pay"]["lines"] and th["pay"]["total"] > 0
assert any(x["status"] == "open" for x in th["my_subs"]), "the demo has Theo's open sub request"
theo_future = [c for c in th["upcoming"] if c["start"] > now.isoformat() and c["title"] == "Sunrise Vinyasa"][0]
ok(call("request_sub", theo_future["id"], "Dentist"))
bad(call("request_sub", theo_future["id"]), "one open request per class")
my = [x for x in call("teach_home")["my_subs"] if x["class"]["id"] == theo_future["id"]][0]
bad(call("cover_sub", my["id"]), "you can't cover your own request")
maya_class = T.classes.search(title="Lunch Flow")[0].get_id()
bad(call("request_sub", maya_class), "only your own classes")
as_user(samir)
assert any(x["id"] == my["id"] for x in call("teach_home")["open_subs"])
ok(call("cover_sub", my["id"]))
cov = T.classes.get_by_id(theo_future["id"])
assert cov["teacher"]["name"] == "Samir Haddad" and cov["orig_teacher"]["name"] == "Theo Martin"
bad(call("cover_sub", my["id"]))
as_user(theo)
bad(call("withdraw_sub", my["id"]))
as_user(bob)
bad(call("withdraw_sub", my["id"]))
assert call("teach_home")["teaching"] is False

# --- the practice page, reflections, reviews, pausing, friends, follows
as_user(bob)
prc = call("my_practice")
assert prc["upcoming"] and prc["passes"]
past = [c for c in T.classes.search(studio=T.studios.get(slug="sage-and-stone")) if c["start"] < now - _dt.timedelta(hours=3)][0]
pb = T.bookings.add_row(klass=past, user=bob, studio=past["studio"], pass_used=T.passes.get_by_id(bp["id"]), start=past["start"],
                        status="checked_in", created=now, updated=now, is_demo=False, reviewed=False)
bad(call("reflect", b["id"], 5), "reflections are for after class")
ok(call("reflect", pb.get_id(), 9, "Felt great"))
assert pb["mood"] == 5
bad(call("review_class", pb.get_id(), 0))
ok(call("review_class", pb.get_id(), 4, "Lovely"))
bad(call("review_class", pb.get_id(), 4, "Again"), "one review per class")
as_user(ana)
bad(call("reflect", pb.get_id(), 3), "not your booking")
bad(call("review_class", pb.get_id(), 3))
as_user(bob)
bad(call("pause_pass", bp["id"], 2), "intro passes can't be paused")
bad(call("friend_pass_send", "sage-and-stone"), "friend passes come with a pack or membership")
monthly = [p for p in call("get_studio", "sage-and-stone")["products"] if p["kind"] == "unlimited"][0]
mp = ok(call("buy_product", monthly["id"]))["pass_"]
code = ok(call("friend_pass_send", "sage-and-stone"))["code"]
ok(call("friend_pass_send", "sage-and-stone"))
bad(call("friend_pass_send", "sage-and-stone"), "two a month")
paused = ok(call("pause_pass", mp["id"], 9))["pass_"]
assert paused["state"] == "paused" and paused["paused_until"]
bad(call("pause_pass", mp["id"], 1), "one pause")
as_user(ana)
bad(call("friend_pass_send", "lumen-hot-yoga"), "needs a pack or membership there")
as_user(None)
fp = call("friend_pass_get", code)
assert fp["from"] == "Bob" and not fp["claimed"]
bad(call("friend_pass_get", "nope"))
as_user(ana)
bad(call("friend_pass_claim", code), "friend passes are for a first visit")
carl = person("carl@example.com", "Carl")
as_user(carl)
assert ok(call("friend_pass_claim", code))["slug"] == "sage-and-stone"
assert any(p["kind"] == "friend" for p in call("my_practice")["passes"])
as_user(bob)
bad(call("friend_pass_claim", code))
assert any(n["kind"] == "friend" for n in call("inbox")["items"])
assert ok(call("toggle_follow", "studio", "sage-and-stone"))["following"] is True
assert "sage-and-stone" in call("discover")["follows"]["studios"]
assert ok(call("toggle_follow", "studio", "sage-and-stone"))["following"] is False
assert ok(call("toggle_follow", "teacher", theo_staff["id"]))["following"] is True
bad(call("toggle_follow", "planet", "x"))
bad(call("toggle_follow", "studio", "nope"))

# --- opening a studio + admin approval
as_user(carl)
bad(call("create_studio", {"name": "Hi"}))
bad(call("create_studio", {"name": "Carl's Corner Yoga"}), "needs a neighbourhood")
new = ok(call("create_studio", {"name": "Carl's Corner Yoga", "neighbourhood": "Villeray", "styles": ["Yin", "Bogus"], "accent": "lake", "rows": 3, "cols": 3}))
assert new["status"] == "review" and new["slug"] == "carl-s-corner-yoga"
assert call("get_studio", new["slug"])["can_manage"], "owners preview their studio in review"
assert call("get_me")["manages"]
as_user(None)
bad(call("get_studio", new["slug"]))
as_user(carl)
assert denied("admin_studios") and denied("admin_set_studio", new["slug"], "live")
as_user(admin)
assert any(s["slug"] == new["slug"] for s in call("admin_studios")["studios"])
ok(call("admin_set_studio", new["slug"], "live", True))
bad(call("admin_set_studio", new["slug"], "weird"))
assert len(call("manage_list")) == 7, "admins can manage every studio"
as_user(None)
assert call("get_studio", new["slug"])["studio"]["status"] == "live"
as_user(admin)
ov = call("admin_overview")
assert ov["studios"] == 6 and ov["studios_review"] == 1

# --- demo data: remove keeps real data, reload doesn't double
ok(call("demo_remove"))
assert M["DemoData"].state() == "removed" and not T.users.search(is_demo=True)
assert [s["slug"] for s in call("discover")["studios"]] == [new["slug"]], "only the real studio is left"
assert not [b_ for b_ in T.bookings.search(user=bob)], "bookings at demo studios went with them"
assert M["DemoData"].state() == "removed", "removed demo data doesn't come back by itself"
ok(call("demo_load"))
n1 = len(T.classes.search())
ok(call("demo_load"))
assert len(T.classes.search()) == n1, "reloading replaces the demo instead of doubling it"
assert len(call("discover")["studios"]) == 6
# one waiver per person per studio, nobody booked twice into one class, and every demo class list opens
seen_w = {}
for w_ in T.waivers.search():
    k_ = (w_["studio"].get_id(), w_["user"].get_id())
    assert k_ not in seen_w, "two demo waivers for one person at one studio"
    seen_w[k_] = 1
seen_b = {}
for b_ in T.bookings.search():
    if b_["user"] is None:
        continue
    k_ = (b_["klass"].get_id(), b_["user"].get_id())
    assert k_ not in seen_b, "someone is booked twice into one demo class"
    seen_b[k_] = 1
sage_ = T.studios.get(slug="sage-and-stone")
as_user(sage_["owner"])
for c_ in T.classes.search(studio=sage_):
    r_ = call("roster", c_.get_id()); assert "class" in r_ and "error" not in r_, ("class list of %s" % c_["title"], r_)
# demo data loaded before the fix: the one-time cleanup removes doubled demo waivers and bookings, then never runs again
DD_ = M["DemoData"]
cls_ = next(iter(T.classes.search(studio=sage_)))
bk_ = next(iter(T.bookings.search(klass=cls_, is_demo=True)), None)
if bk_ is not None:
    T.bookings.add_row(klass=cls_, user=bk_["user"], studio=sage_, status=bk_["status"], start=bk_["start"], is_demo=True)
w0_ = next(iter(T.waivers.search(studio=sage_, is_demo=True)))
T.waivers.add_row(studio=sage_, user=w0_["user"], signed=w0_["signed"], signature="dup", emergency="", health="", share=False, is_demo=True)
M["common"].set_setting("demo_dedupe_v1", "")
assert DD_.dedupe_once() >= 1
assert len(T.waivers.search(studio=sage_, user=w0_["user"])) == 1
if bk_ is not None:
    assert len(T.bookings.search(klass=cls_, user=bk_["user"])) == 1
assert DD_.dedupe_once() == 0, "it runs only once"
# a real person with two waiver rows at one studio still gets a class list (and C.waiver picks the newest)
u_ = next(iter(T.waivers.search(studio=sage_)))["user"]
T.waivers.add_row(studio=sage_, user=u_, signed=M["common"].now(), signature="Again", emergency="", health="", share=False, is_demo=True)
assert M["common"].waiver(sage_, u_)["signature"] == "Again"
b2_ = next(iter(T.bookings.search(studio=sage_, user=u_)), None)
if b2_ is not None:
    r_ = call("roster", b2_["klass"].get_id()); assert "class" in r_ and "error" not in r_, ("class list with a doubled waiver", r_)
as_user(admin)

# ---------------------------------------------------------------------------------- Privacy & Terms
if "legal_server" in M:
    as_user(ana)
    st = call("legal_state")
    assert st["signedIn"] and st["accepted_version"] is None
    ok(call("legal_accept", st["version"], "signup"))
    assert ana["legal_source"] == "signup" and call("legal_state")["accepted_version"] == st["version"]

# ---------------------------------------------------------------------------------- every callable is covered by a permission check
# A callable that changes data without require_user / a C.require_* check is a security hole. List the public ones here.
PUBLIC = {"get_me", "submit_feedback", "legal_state", "legal_accept", "discover", "get_studio", "get_class", "friend_pass_get"}
for name, (f, need) in sorted(anvil.server.CALLABLES.items()):
    if name in PUBLIC:
        continue
    assert need, "%s is callable by anyone: add require_user=True (or list it in PUBLIC in test_server.py)" % name

print("ALL OK (%d server functions)" % len(anvil.server.CALLABLES))
