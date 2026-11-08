from anvil import *

from ._anvil_designer import MgClassTemplate
from ... import hb


class MgClass(MgClassTemplate):
    """A class on the Today board: fill bar, checked in, first-timers, the class list (or Restore if cancelled).
    item = {c, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c: dict = self.item["c"]
        d = self.dom_nodes
        st = hb.ms(c["start"])
        now = hb.now_ms()
        live = st <= now < st + (c.get("minutes") or 60) * 60000
        cancelled = c.get("status") == "cancelled"
        self.row.classes["cancelled"] = cancelled
        self.row.classes["now"] = live
        clock, ampm = hb.time_parts(c["start"])
        hb.text(d["t_clock"], clock)
        hb.text(d["t_ampm"], ampm)
        hb.text(d["t_sub"], hb.mins(c.get("minutes")))
        hb.text(d["title"], c["title"])
        self.live.visible = live
        self.cancelled.visible = cancelled
        hb.text(d["meta"], "%s%s · %s" % ((c.get("teacher") or {}).get("name") or "", " (sub)" if c.get("sub") else "", (c.get("room") or {}).get("name") or ""))
        pct = int(round((c.get("booked") or 0) * 100.0 / c["capacity"])) if c.get("capacity") else 0
        hb.text(d["fill_top"], "%s / %s booked%s" % (c.get("booked"), c.get("capacity"), " · %d waiting" % c["waiting"] if c.get("waiting") else ""))
        self.bar.classes["full"] = pct >= 100
        d["bar_fill"].style.width = "%d%%" % min(100, pct)
        hb.text(d["fill_bottom"], "%s checked in%s" % (c.get("checked_in", 0), " · " + hb.plural(c["first_timers"], "first-timer") if c.get("first_timers") else ""))
        self.roster_button.visible = not cancelled
        self.restore_button.visible = cancelled and st > now

    @handle("roster_button", "click")
    def roster_button_click(self, **event_args):
        self.item["host"].roster(self.item["c"]["id"])

    @handle("restore_button", "click")
    def restore_button_click(self, **event_args):
        self.item["host"].restore(self.item["c"]["id"])
