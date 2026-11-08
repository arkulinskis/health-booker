from anvil import *

from ._anvil_designer import ProductCardTemplate
from ... import hb


class ProductCard(ProductCardTemplate):
    """A pass for sale on a studio's Pricing tab. item = {p, host}; host.buy(p)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        p: dict = self.item["p"]
        d = self.dom_nodes
        self.first.visible = bool(p.get("intro_only"))
        hb.text(d["name"], p["name"])
        hb.text(d["price"], hb.money(p.get("price")))
        what = "Unlimited classes" if p.get("credits") is None else hb.plural(p["credits"], "class", "classes")
        hb.text(d["what"], "%s · valid %s" % (what, hb.plural(p.get("days") or 30, "day")))
        hb.text(d["about"], p.get("about") or "")
        self.get_button.visible = bool(p.get("eligible"))
        self.only_new.visible = not p.get("eligible")

    @handle("get_button", "click")
    def get_button_click(self, **event_args):
        self.item["host"].buy(self.item["p"])
