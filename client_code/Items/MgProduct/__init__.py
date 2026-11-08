from anvil import *

from ._anvil_designer import MgProductTemplate
from ... import hb


class MgProduct(MgProductTemplate):
    """A pass for sale in the back office. item = {p, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p: dict = self.item["p"]
        d = self.dom_nodes
        self.card.classes["off"] = not p.get("active")
        hb.text(d["kind"], hb.KIND.get(p.get("kind"), p.get("kind")))
        d["kind"].className = "ui-badge" + (" clay" if p.get("intro_only") else "")
        self.hidden.visible = not p.get("active")
        hb.text(d["name"], p["name"])
        hb.text(d["price"], hb.money(p.get("price")))
        hb.text(d["what"], "%s · %s" % ("Unlimited" if p.get("credits") is None else hb.plural(p["credits"], "class", "classes"), hb.plural(p.get("days") or 30, "day")))
        hb.text(d["sold"], "%d sold" % (p.get("sold") or 0))

    @handle("edit_button", "click")
    def edit_button_click(self, **event_args):
        self.item["host"].edit(self.item["p"])
