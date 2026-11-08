from anvil import *

from ._anvil_designer import ClassBlockTemplate
from ... import hb


class ClassBlock(ClassBlockTemplate):
    """A class in the back-office week (press to edit). item = {c, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c: dict = self.item["c"]
        d = self.dom_nodes
        self.btn.classes["cancelled"] = c.get("status") == "cancelled"
        self.btn.classes["ws"] = c.get("kind") == "workshop"
        hb.text(d["title"], "%s %s" % (hb.time(c["start"]), c["title"]))
        hb.text(d["sub"], "%s%s · %s/%s" % (hb.first_name((c.get("teacher") or {}).get("name")), " (sub)" if c.get("sub") else "",
                                           c.get("booked"), c.get("capacity")))
        pct = int(round((c.get("booked") or 0) * 100.0 / c["capacity"])) if c.get("capacity") else 0
        self.bar.classes["full"] = pct >= 100
        d["bar_fill"].style.width = "%d%%" % min(100, pct)

    def btn_click(self, event):
        self.item["host"].edit(self.item["c"])
