from anvil import *

from ._anvil_designer import MatchResultTemplate
from ... import hb


class MatchResult(MatchResultTemplate):
    """A suggested class in the matcher. item = {c, why, host}; host.pick(class id)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        c: dict = self.item["c"]
        d = self.dom_nodes
        hb.set_acc(self.btn, (c.get("studio") or {}).get("accent"))
        hb.text(d["title"], c["title"])
        hb.text(d["studio"], (c.get("studio") or {}).get("name"))
        hb.text(d["when"], hb.when(c["start"]))
        hb.text(d["why"], self.item.get("why") or "")

    def btn_click(self, event):
        self.item["host"].pick(self.item["c"]["id"])
