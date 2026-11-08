import json

from anvil import *
import anvil.js
from anvil.js import window

from ._anvil_designer import MatGridTemplate


class MatGrid(MatGridTemplate):
    """The room drawn as mats (theme/assets/hb-draw.js HBD.matGrid). draw(room, taken, mine, selected, edit, on_pick):
    room = {rows, cols, blocked}; on_pick(spot) runs when a free mat (or, editing, any mat) is pressed."""

    def __init__(self, **properties):
        super().__init__(**properties)
        self._pick = None

    def draw(self, room, taken=None, mine=None, selected=None, edit=False, on_pick=None, front="Teacher", nokey=False):
        self._pick = on_pick
        opts = {"taken": list(taken or []), "mine": mine or "", "selected": selected or "", "edit": bool(edit),
                "front": front, "nokey": bool(nokey)}
        r = {"rows": room.get("rows") or 1, "cols": room.get("cols") or 1, "blocked": list(room.get("blocked") or [])}
        window.HBD.matGrid(self.dom_nodes["box"], json.dumps(r), json.dumps(opts), self._picked)

    def _picked(self, spot):
        if self._pick:
            self._pick(str(spot))
