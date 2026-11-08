from anvil import *

from ._anvil_designer import ShopTemplate
from ... import hb, state


class Shop(ShopTemplate):
    """Choose and get a pass (buy_product; paid at the studio). products come from the server with .eligible.
    Closes with the new pass dict, or None."""

    def __init__(self, studio=None, products=None, klass=None, **properties):
        super().__init__(**properties)
        self.studio: dict = studio or {}
        self.products = products or []
        ok = [p for p in self.products if p.get("eligible")]
        intro = [p for p in ok if p.get("intro_only")]
        self.pick = (intro or ok or [None])[0]
        hb.text(self.dom_nodes["lead"], ("To book %s, you need a pass for %s." % (klass["title"], self.studio.get("name")))
                if klass else "Passes for %s." % self.studio.get("name"))
        self.draw()

    def draw(self):
        pid = self.pick["id"] if self.pick else None
        self.products_panel.items = [{"p": p, "on": p["id"] == pid, "host": self} for p in self.products]
        self.get_button.enabled = self.pick is not None

    def choose(self, p):
        self.pick = p
        k = state.focus_key()
        self.draw()
        state.refocus(self.products_panel, k)

    @handle("get_button", "click")
    def get_button_click(self, **event_args):
        if not self.pick:
            return
        self.get_button.enabled = False
        try:
            r = state.call("buy_product", self.pick["id"])
        finally:
            self.get_button.enabled = True
        if r:
            state.toast("Pass added to your wallet. Pay at the desk on your first visit." if self.pick.get("price")
                        else "Pass added to your wallet.", "ok")
            self.raise_event("x-close-alert", value=r["pass_"])

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
