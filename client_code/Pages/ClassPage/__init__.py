import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import ClassPageTemplate
from ... import hb, router, state


class ClassPage(ClassPageTemplate):
    """#class/<id>[/solo]: one class. Details, the teacher (follow, reviews), the room with pick-a-mat, which pass to
    use, then book / join the waitlist / cancel; after class, the reflection + review. Staff also get the class list.
    Server: get_class (+ book_class / cancel_booking through hb.book / hb.cancel)."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.id = args[0] if args else ""
        self.solo = len(args) > 1 and args[1] == "solo"
        if self.solo:
            hb.loose(window.document.documentElement).classList.add("hb-solo")
        self.spot = None
        self.pass_id = None
        self.load()

    def load(self):
        r = anvil.server.call("get_class", self.id)
        ok = bool(r) and r.get("ok") is not False
        self.not_found.visible = not ok
        self.main.visible = ok
        if not ok:
            return
        self.d: dict = r
        passes = r.get("passes") or []
        if passes and self.pass_id not in [p["id"] for p in passes]:
            self.pass_id = passes[0]["id"]
        self.draw()

    def draw(self):
        d = self.d
        c: dict = d["class"]
        s: dict = c["studio"]
        t = d.get("teacher")
        dn = self.dom_nodes
        me = state.me()
        window.document.title = c["title"] + " · Health Booker"
        hb.set_acc(self.page, s.get("accent"))
        state.set_attr(self.back_link, "href", router.href("studio", s["slug"], "solo" if self.solo else ""))
        hb.text(dn["back_text"], s["name"])
        hb.text(dn["title"], c["title"])
        hb.text(dn["when"], "%s%s · %s · %s" % (c.get("style") or "", " workshop" if c.get("kind") == "workshop" else "",
                                                 hb.when(c["start"]), hb.mins(c.get("minutes"))))
        tags = [x for x in hb.class_tags(c, True) if x[1] != "hb-tag" or x[0] not in (c.get("style"), hb.LEVEL.get(c.get("level")))]
        if c.get("sub") and t:
            tags = [x for x in tags if "sub" not in x[1]] + [("%s is subbing for %s" % (t["name"], c.get("orig_teacher")), "hb-tag sub", None)]
        hb.fill(dn["tags"], tags)
        hb.text(dn["level"], hb.LEVEL.get(c.get("level"), c.get("level")))
        hb.leaves(dn["leaves"], c.get("intensity"))
        hb.text(dn["intensity"], hb.INTENSITY[int(c.get("intensity") or 2)])
        hb.text(dn["room"], (c.get("room") or {}).get("name") or s["name"])
        hb.text(dn["hood"], s.get("neighbourhood"))
        hb.text(dn["mats"], "%s / %s" % (c.get("booked"), c.get("capacity")))
        hb.text(dn["waiting"], ("%d waiting" % c["waiting"]) if c.get("waiting") else "")
        hb.text(dn["about"], c.get("about"))
        self.address.visible = bool(s.get("address"))
        hb.text(dn["address_text"], "%s, %s" % (s["name"], s.get("address") or ""))
        self.teacher_card.visible = bool(t)
        if t:
            hb.text(dn["t_initials"], state.initials(t["name"]))
            hb.text(dn["t_name"], t["name"])
            hb.text(dn["t_bio"], t.get("bio"))
            self.tfollow_button.visible = bool(me)
            tf = t["id"] in d["follows"]["teachers"]
            self.tfollow_button.text = "Following" if tf else "Follow"
            self.tfollow_button.role = ["btn", "btn-sm", "ic-heartfill" if tf else "ic-heart"]
            state.set_control_attr(self.tfollow_button, "aria-pressed", "true" if tf else "false")
            self.reviews_panel.items = [{"r": r, "mode": "class"} for r in d.get("reviews") or []]
        self.roster_button.visible = bool(d.get("is_staff"))
        self.draw_book()

    def draw_book(self):
        d = self.d
        c: dict = d["class"]
        s: dict = c["studio"]
        b = d.get("booking")
        dn = self.dom_nodes
        me = state.me()
        for box in (self.cancelled_box, self.booked_box, self.wait_box, self.late_box, self.past_box, self.book_box):
            box.visible = False
        self.mats.visible = False
        if c.get("status") == "cancelled":
            self.cancelled_box.visible = True
            hb.text(dn["cancelled_text"], "This class was cancelled. " + (c.get("cancel_note") or ""))
            return
        if b and b["status"] in ("booked", "checked_in"):
            self.booked_box.visible = True
            past = bool(d.get("past"))
            hb.text(dn["booked_title"], "You came to this class" if past else "You're booked")
            hb.text(dn["booked_line"], ("Mat %s · " % b["spot"] if b.get("spot") else "Any mat · ") + (b.get("pass_name") or ""))
            hb.text(dn["booked_note"], "" if past else (
                "It's inside the %s-hour window: cancelling now counts against your pass." % s.get("cancel_hours")
                if b.get("late_if_cancel") else "Free to cancel until %s." % hb.when(b.get("cancel_by"))))
            self.reflect_button.visible = past
            self.reflect_button.text = "Edit your reflection" if b.get("mood") else "How do you feel?"
            self.booked_actions.visible = not past
            if d.get("room") and not past:
                self.mats.visible = True
                self.mats.draw(d["room"], d.get("taken"), b.get("spot"), None, nokey=True)
            return
        if b and b["status"] == "waitlist":
            self.wait_box.visible = True
            hb.text(dn["wait_title"], "You're #%s on the waitlist" % b.get("waitlist_pos"))
            return
        if b and b["status"] == "late":
            self.late_box.visible = True
            return
        if d.get("past"):
            self.past_box.visible = True
            return
        self.book_box.visible = True
        full = (c.get("left") or 0) <= 0
        ws = c.get("kind") == "workshop"
        hb.text(dn["book_title"], ("Workshop · " + hb.money(c.get("price"))) if ws else "Class is full" if full else "Book your mat")
        left, low = hb.spots(c)
        hb.text(dn["left"], left)
        dn["left"].className = "hb-left" + (" low" if low else "")
        show_mats = not full and bool(d.get("room")) and not ws
        self.pick_hint.visible = show_mats
        self.mats.visible = show_mats
        if show_mats:
            self.mats.draw(d["room"], d.get("taken"), None, self.spot, on_pick=self.pick_spot)
        passes = d.get("passes") or []
        self.passes_panel.visible = bool(me and passes and not ws)
        self.passes_panel.items = [{"p": p, "on": p["id"] == self.pass_id, "host": self} for p in passes] if (me and not ws) else []
        self.pass_note.visible = bool(me and not passes and not ws)
        if me and not passes and not ws:
            intro = [p for p in d.get("products") or [] if p.get("intro_only") and p.get("eligible")]
            hb.text(dn["pass_note_text"], ("New to %s? %s for %s. You'll choose a pass in the next step." % (
                s["name"], intro[0]["name"], hb.money(intro[0].get("price")))) if intro else "You'll choose a pass in the next step.")
        self.ws_note.visible = ws
        hb.text(dn["ws_note_text"], "Pay %s at the door. Free to cancel until %s hours before." % (s["name"], s.get("cancel_hours")))
        self.book_button.text = ("Join the waitlist" + (" (%d waiting)" % c["waiting"] if c.get("waiting") else "")) if full else (
            "Book mat " + self.spot if self.spot else "Book")
        self.book_button.role = ["btn", "btn-lg", "btn-block", "ic-clock"] if full else ["btn", "btn-primary", "btn-lg", "btn-block", "ic-check"]
        hb.text(dn["free_note"], "Free cancellation until %s hours before class." % s.get("cancel_hours"))

    # ---- choices
    def pick_spot(self, spot):
        self.spot = None if self.spot == spot else spot
        self.draw_book()

    def pick_pass(self, pid):
        self.pass_id = pid
        k = state.focus_key()
        self.draw_book()
        state.refocus(self.passes_panel, k)

    # ---- actions
    @handle("book_button", "click")
    def book_button_click(self, **event_args):
        self.book_button.enabled = False
        try:
            b = hb.book(self.d["class"], self.pass_id if self.d.get("passes") else None, self.spot)
        finally:
            self.book_button.enabled = True
        if b:
            self.spot = None
            self.load()

    def _booking(self):
        b = dict(self.d["booking"])
        b["class"] = self.d["class"]
        return b

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        if hb.cancel(self._booking()):
            self.load()

    @handle("leave_button", "click")
    def leave_button_click(self, **event_args):
        if hb.cancel(self._booking()):
            self.load()

    @handle("ics_button", "click")
    def ics_button_click(self, **event_args):
        hb.ics(self.d["class"])

    @handle("reflect_button", "click")
    def reflect_button_click(self, **event_args):
        if hb.reflect(self._booking()):
            self.load()

    @handle("roster_button", "click")
    def roster_button_click(self, **event_args):
        if hb.roster(self.id):
            self.load()

    @handle("tfollow_button", "click")
    def tfollow_button_click(self, **event_args):
        t = self.d["teacher"]
        r = state.call("toggle_follow", "teacher", t["id"])
        if r is None:
            return
        f = self.d["follows"]["teachers"]
        if r.get("following") and t["id"] not in f:
            f.append(t["id"])
        elif not r.get("following") and t["id"] in f:
            f.remove(t["id"])
        state.toast("You'll see %s's classes under \"Following\"." % hb.first_name(t["name"]) if r.get("following") else "Unfollowed.")
        self.draw()
