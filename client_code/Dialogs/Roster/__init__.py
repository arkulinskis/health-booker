from anvil import *

from ._anvil_designer import RosterTemplate
from ... import hb, state


class Roster(RosterTemplate):
    """The class list (Teach and Manage): check in, no-show, forgive a late cancel, mark a pass paid, add a walk-in.
    .changed tells the page to reload after the dialog closes. Server: roster, set_attendance, forgive, mark_paid,
    add_walkin."""

    def __init__(self, class_id=None, **properties):
        super().__init__(**properties)
        self.class_id = class_id
        self.changed = False
        state.set_control_attr(self.walkin_name, "aria-label", "Walk-in name")
        state.set_control_attr(self.walkin_email, "aria-label", "Walk-in account email")
        self.load()

    def load(self):
        d = state.call("roster", self.class_id)
        if not d:
            return
        c: dict = d["class"]
        people = [p for p in d["people"] if p["status"] != "waitlist"]
        waiting = [p for p in d["people"] if p["status"] == "waitlist"]
        n_in = len([p for p in people if p["status"] == "checked_in"])
        started = hb.ms(c["start"]) < hb.now_ms()
        hb.text(self.dom_nodes["title"], c["title"])
        hb.text(self.dom_nodes["summary"], "%s · %s · %d checked in of %s booked · %s mats" % (
            hb.when(c["start"]), (c.get("teacher") or {}).get("name") or "", n_in, c.get("booked"), c.get("capacity")))
        mgr = bool(d.get("can_manage"))
        self.people_panel.items = [{"p": p, "mgr": mgr, "started": started, "host": self} for p in people]
        self.nobody.visible = not people
        self.wait_part.visible = bool(waiting)
        self.wait_panel.items = [{"title": p["name"], "sub": "Joined " + hb.ago(p.get("wl_at")), "who": str(i + 1)}
                                 for i, p in enumerate(waiting)]
        self.walkin.visible = mgr

    def attend(self, booking_id, status):
        self.changed = True
        if state.call("set_attendance", booking_id, status) is not None:
            self.load()

    def forgive(self, booking_id):
        self.changed = True
        if state.call("forgive", booking_id):
            state.toast("Forgiven: their credit is back.", "ok")
            self.load()

    def paid(self, pass_id):
        self.changed = True
        if hb.mark_paid(pass_id):
            self.load()

    @handle("walkin_button", "click")
    def walkin_button_click(self, **event_args):
        self.changed = True
        if state.call("add_walkin", self.class_id, self.walkin_name.text or "", self.walkin_email.text or ""):
            state.toast("Added and checked in.", "ok")
            self.walkin_name.text = self.walkin_email.text = ""
            self.load()

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=self.changed)
