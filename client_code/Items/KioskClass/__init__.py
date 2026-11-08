from anvil import *

from ._anvil_designer import KioskClassTemplate
from ... import hb


class KioskClass(KioskClassTemplate):
    """A class on the kiosk with the people booked (filtered by the name search). item = {c, q, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        c: dict = it["c"]
        q = (it.get("q") or "").lower()
        ppl = [p for p in c["people"] if not q or q in (p.get("name") or "").lower()]
        hb.text(self.dom_nodes["title"], "%s · %s" % (hb.time(c["start"]), c["title"]))
        hb.text(self.dom_nodes["sub"], "%s · %d of %d here" % ((c.get("teacher") or {}).get("name") or "",
                                                              len([p for p in c["people"] if p.get("in")]), len(c["people"])))
        self.people_panel.items = [{"p": p, "host": it["host"]} for p in ppl]
        hb.text(self.dom_nodes["none"], "" if ppl else ("No one by that name in this class." if q else "No one booked yet."))
