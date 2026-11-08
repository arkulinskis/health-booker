from anvil import *
from anvil.js import window

from ._anvil_designer import BookedTemplate
from ... import hb, router


class Booked(BookedTemplate):
    """The confirmation after booking: a breathing circle (or the waitlist place) and the facts, with
    Add to calendar and My practice."""

    def __init__(self, booking=None, **properties):
        super().__init__(**properties)
        b: dict = booking or {}
        c: dict = b["class"]
        s: dict = c.get("studio") or {}
        d = self.dom_nodes
        self.c = c
        wait = b.get("status") == "waitlist"
        hb.set_acc(self.box, s.get("accent"))
        self.wait_part.visible = wait
        self.booked_part.visible = not wait
        hb.text(d["wait_title"], "You're #%s on the waitlist" % (b.get("waitlist_pos") or 1))
        hb.text(d["title"], c["title"])
        hb.text(d["when"], hb.when(c["start"]))
        hb.text(d["where"], (s.get("name") or "") + (", " + s["address"] if s.get("address") else ""))
        self.mat_line.visible = bool(b.get("spot"))
        hb.text(d["mat"], "Mat %s" % b.get("spot"))
        self.pass_line.visible = bool(b.get("pass_name"))
        hb.text(d["pass_name"], b.get("pass_name"))
        self.cancel_line.visible = not wait and bool(b.get("cancel_by"))
        hb.text(d["cancel_by"], "Free to cancel until " + hb.when(b.get("cancel_by")))
        self._n = 0
        self._timer = None

    @handle("", "show")
    def form_show(self, **event_args):
        if self.booked_part.visible:
            self._timer = window.setInterval(self._breathe, 4000)

    @handle("", "hide")
    def form_hide(self, **event_args):
        if self._timer:
            window.clearInterval(self._timer)
            self._timer = None

    def _breathe(self):
        self._n += 1
        hb.text(self.dom_nodes["breath"], "Breathe out" if self._n % 2 else "Breathe in")

    @handle("ics_button", "click")
    def ics_button_click(self, **event_args):
        hb.ics(self.c)

    @handle("practice_button", "click")
    def practice_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
        router.go("practice")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
