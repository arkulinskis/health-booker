from anvil import *

from ._anvil_designer import DayChipTemplate
from ... import hb, state


class DayChip(DayChipTemplate):
    """One day in Discover's week strip. item = {key, top, num, count, on, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        hb.text(self.dom_nodes["top"], it["top"])
        hb.text(self.dom_nodes["num"], it["num"])
        hb.text(self.dom_nodes["count"], hb.plural(it["count"], "class", "classes"))
        self.btn.classes["on"] = bool(it.get("on"))
        state.set_attr(self.btn, "aria-pressed", "true" if it.get("on") else "false")
        state.set_attr(self.btn, "data-key", "day:" + it["key"])

    def btn_click(self, event):
        self.item["host"].pick_day(self.item["key"])
