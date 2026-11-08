from anvil import *

from ._anvil_designer import PassLineTemplate
from ... import hb


class PassLine(PassLineTemplate):
    """One of your passes at this studio (studio page side panel). item = {p}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p: dict = self.item["p"]
        hb.text(self.dom_nodes["name"], p["name"])
        self.unpaid.visible = not p.get("paid")
        hb.text(self.dom_nodes["left"], "Unlimited" if p.get("unlimited") else "%s left" % p.get("credits_left"))
