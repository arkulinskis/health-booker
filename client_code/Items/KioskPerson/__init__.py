from anvil import *

from ._anvil_designer import KioskPersonTemplate
from ... import hb, state


class KioskPerson(KioskPersonTemplate):
    """A name to tap on the kiosk (check in, or undo). item = {p, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p: dict = self.item["p"]
        self.btn.classes["in"] = bool(p.get("in"))
        state.set_attr(self.btn, "aria-pressed", "true" if p.get("in") else "false")
        hb.text(self.dom_nodes["name"], p.get("name"))
        hb.text(self.dom_nodes["sub"], ("Checked in" if p.get("in") else ("Mat " + p["spot"]) if p.get("spot") else "Tap to check in") +
                (" · first visit" if p.get("first") else ""))

    def btn_click(self, event):
        self.item["host"].tap(self.item["p"])
