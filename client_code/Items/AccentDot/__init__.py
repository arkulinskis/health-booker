from anvil import *

from ._anvil_designer import AccentDotTemplate
from ... import hb, state


class AccentDot(AccentDotTemplate):
    """A studio colour to choose (Open a studio, Settings). item = {key, on, host}; host.pick_accent(key)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        hb.set_acc(self.btn, it["key"])
        self.btn.classes["on"] = bool(it.get("on"))
        state.set_attr(self.btn, "aria-checked", "true" if it.get("on") else "false")
        state.set_attr(self.btn, "aria-label", "Colour: " + it["key"])
        state.set_attr(self.btn, "data-key", "acc:" + it["key"])

    def btn_click(self, event):
        self.item["host"].pick_accent(self.item["key"])
