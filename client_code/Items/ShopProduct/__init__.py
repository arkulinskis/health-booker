from anvil import *

from ._anvil_designer import ShopProductTemplate
from ... import hb, state


class ShopProduct(ShopProductTemplate):
    """A pass to choose in the Shop dialog. item = {p, on, host}; intro offers are disabled for returning students."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        p: dict = it["p"]
        d = self.dom_nodes
        hb.text(d["name"], p["name"])
        self.first.visible = bool(p.get("intro_only"))
        hb.text(d["price"], hb.money(p.get("price")))
        what = "Unlimited classes" if p.get("kind") == "unlimited" or p.get("credits") is None else hb.plural(p["credits"], "class", "classes")
        hb.text(d["what"], "%s · valid %s%s%s" % (what, hb.plural(p.get("days") or 30, "day"),
                                                 (" · " + p["about"]) if p.get("about") else "",
                                                 "" if p.get("eligible") else " · for new students"))
        self.btn.classes["on"] = bool(it.get("on"))
        state.set_attr(self.btn, "aria-checked", "true" if it.get("on") else "false")
        state.set_attr(self.btn, "data-key", "p:" + p["id"])
        if not p.get("eligible"):
            state.set_attr(self.btn, "disabled", "disabled")

    def btn_click(self, event):
        if self.item["p"].get("eligible"):
            self.item["host"].choose(self.item["p"])
