from anvil import *

from ._anvil_designer import SubCardTemplate
from ... import hb


class SubCard(SubCardTemplate):
    """A sub request: a colleague's (cover it in one tap) or your own (its status). item = {x, mine, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        x: dict = it["x"]
        c: dict = x.get("class") or {}
        d = self.dom_nodes
        mine = bool(it.get("mine"))
        self.card.classes["open"] = x.get("status") == "open" and not mine
        hb.text(d["title"], c.get("title"))
        hb.text(d["when"], hb.when(c.get("start")))
        hb.text(d["sub"], (c.get("studio") or {}).get("name", "") + ("" if mine else " · for " + (x.get("from") or "")) +
                ((' · "%s"' % x["reason"]) if x.get("reason") else "") + " · %s booked" % c.get("booked", 0))
        st = x.get("status")
        hb.text(d["badge"], ("Covered by " + (x.get("filled_by") or "")) if st == "filled" else "Waiting for a sub" if st == "open" else "Withdrawn")
        d["badge"].className = "ui-badge " + {"filled": "good", "open": "warn"}.get(st, "")
        d["badge"].hidden = not mine
        self.cover_button.visible = not mine

    @handle("cover_button", "click")
    def cover_button_click(self, **event_args):
        self.item["host"].cover(self.item["x"]["id"])
