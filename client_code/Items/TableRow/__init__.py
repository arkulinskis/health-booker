from anvil import *

from ._anvil_designer import TableRowTemplate
from ... import hb


class TableRow(TableRowTemplate):
    """One row of a small table drawn as a grid (pay statement, insights). item = {cells: [(text, css class)], cls}.
    The grid's columns come from the row class (cls) in app.css."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        row = self.dom_nodes["row"]
        row.className = "hb-trow " + (it.get("cls") or "")
        hb.fill(row, [(t, c or "c", None) for t, c in it["cells"]])
