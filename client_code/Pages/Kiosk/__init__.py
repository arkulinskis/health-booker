import anvil.server
from anvil import *
from anvil.js import window

from ._anvil_designer import KioskTemplate
from ... import hb, router, state


class Kiosk(KioskTemplate):
    """#kiosk/<slug>: full-screen self check-in for a tablet at the front desk (staff signed in; the frame is hidden).
    Today's remaining classes with the people booked (first name + initial); students tap their name. Refreshes
    quietly every minute. Server: kiosk_day, set_attendance."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        self.slug = args[0] if args else ""
        self.q = ""
        self.welcome.visible = False
        state.set_control_attr(self.search_box, "aria-label", "Find your name")
        state.set_attr(self.exit_link, "href", router.href("manage", self.slug))
        self.load(False)
        self._timer = window.setInterval(self._tick, 60000)
        self._clock = window.setInterval(self._show_clock, 15000)
        self._wtimer = None

    def leave(self):
        window.clearInterval(self._timer)
        window.clearInterval(self._clock)

    def load(self, quiet=True):
        a = hb.start_of_day()
        b = hb.start_of_day(1)
        d = state.call_quiet("kiosk_day", self.slug, a, b) if quiet else state.call("kiosk_day", self.slug, a, b)
        if not d:
            return
        self.d: dict = d
        hb.set_acc(self.page, d["studio"].get("accent"))
        hb.text(self.dom_nodes["title"], "Welcome to " + d["studio"]["name"])
        self._show_clock()
        self.draw()

    def draw(self):
        self.classes_panel.items = [{"c": c, "q": self.q, "host": self} for c in self.d["classes"]]
        self.empty.visible = not self.d["classes"]

    def _show_clock(self):
        hb.text(self.dom_nodes["clock"], hb.time(str(window.HBD.fmt.nowIso())))

    def _tick(self):
        if window.document.activeElement != state.control(self.search_box):
            self.load(True)

    @handle("search_box", "change")
    def search_box_change(self, **event_args):
        self.q = self.search_box.text or ""
        self.draw()

    def tap(self, p):
        was_in = bool(p.get("in"))
        if state.call_quiet("set_attendance", p["id"], "booked" if was_in else "checked_in") is None:
            state.toast("That didn't work. Ask at the desk.", "error")
            return
        if not was_in:
            first = bool(p.get("first"))
            hb.text(self.dom_nodes["w_title"], "Welcome%s, %s" % ("" if first else " back", hb.first_name(p.get("name"))))
            hb.text(self.dom_nodes["w_text"], "So glad you're here. Grab a mat and make yourself at home." if first else "Your mat is waiting.")
            self.welcome.visible = True
            if self._wtimer:
                window.clearTimeout(self._wtimer)
            self._wtimer = window.setTimeout(self._hide_welcome, 2600)
        self.q = ""
        self.search_box.text = ""
        self.load(True)

    def _hide_welcome(self):
        self.welcome.visible = False

    def welcome_click(self, event):
        self._hide_welcome()
