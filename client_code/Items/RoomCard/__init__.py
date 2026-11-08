from anvil import *

from ._anvil_designer import RoomCardTemplate
from ... import hb


class RoomCard(RoomCardTemplate):
    """A room in Settings: name, rows x mats per row, and the mats (tap one to block it: a pillar, the door).
    item = {r (edited in place), host}; host.save_room(r)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r: dict = self.item["r"]
        self.r = r
        self.name_box.text = r.get("name") or ""
        self.rows_box.text = str(r.get("rows") or 1)
        self.cols_box.text = str(r.get("cols") or 1)
        self.draw()

    def _n(self, box):
        try:
            return max(1, min(10, int(float(box.text or 1))))
        except ValueError:
            return 1

    def draw(self):
        r = self.r
        hb.text(self.dom_nodes["note"], "Tap a mat to block it (a pillar, the door). %d mats." % (r["rows"] * r["cols"] - len(r["blocked"])))
        self.mats.draw(r, edit=True, on_pick=self.toggle)

    def toggle(self, spot):
        if spot in self.r["blocked"]:
            self.r["blocked"].remove(spot)
        else:
            self.r["blocked"].append(spot)
        self.draw()

    @handle("rows_box", "change")
    def rows_box_change(self, **event_args):
        self.r["rows"] = self._n(self.rows_box)
        self.draw()

    @handle("cols_box", "change")
    def cols_box_change(self, **event_args):
        self.r["cols"] = self._n(self.cols_box)
        self.draw()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        self.r["name"] = self.name_box.text or ""
        self.r["rows"], self.r["cols"] = self._n(self.rows_box), self._n(self.cols_box)
        self.item["host"].save_room(self.r)
