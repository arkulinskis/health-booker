from anvil import *

from ._anvil_designer import DayGroupTemplate
from ... import hb


class DayGroup(DayGroupTemplate):
    """A day heading ("Tomorrow 6 November") and that day's classes. item = {label, sub, rows, tpl}: tpl "teach"
    shows Items/TeachClass rows (a teacher's view), otherwise Items/ClassRow."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        hb.text(self.dom_nodes["label"], it["label"])
        hb.text(self.dom_nodes["sub"], it["sub"])
        if it.get("tpl") == "teach":
            from ..TeachClass import TeachClass
            self.rows_panel.item_template = TeachClass
        self.rows_panel.items = it["rows"]
