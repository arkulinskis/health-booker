from anvil import *

from ._anvil_designer import WeekColTemplate
from ... import hb


class WeekCol(WeekColTemplate):
    """One day of the back-office week. item = {label, today, blocks, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        hb.text(self.dom_nodes["label"], it["label"])
        self.dom_nodes["label"].className = "mg-col-h" + (" today" if it.get("today") else "")
        self.blocks_panel.items = [{"c": c, "host": it["host"]} for c in it["blocks"]]
