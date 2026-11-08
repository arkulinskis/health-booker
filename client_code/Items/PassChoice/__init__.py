from anvil import *

from ._anvil_designer import PassChoiceTemplate
from ... import hb, state


class PassChoice(PassChoiceTemplate):
    """Which of your passes pays for this class (class page). item = {p, on, host}; host.pick_pass(id)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        p: dict = it["p"]
        hb.text(self.dom_nodes["name"], p["name"])
        hb.text(self.dom_nodes["left"], "Unlimited" if p.get("unlimited") else "%s left" % p.get("credits_left"))
        self.btn.classes["on"] = bool(it.get("on"))
        state.set_attr(self.btn, "aria-checked", "true" if it.get("on") else "false")
        state.set_attr(self.btn, "data-key", "pass:" + p["id"])

    def btn_click(self, event):
        self.item["host"].pick_pass(self.item["p"]["id"])
