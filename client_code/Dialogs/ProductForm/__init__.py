import anvil.server
from anvil import *

from ._anvil_designer import ProductFormTemplate
from ... import hb, state


class ProductForm(ProductFormTemplate):
    """New or edited pass for sale (save_product). Closes with True when saved."""

    def __init__(self, slug="", product=None, kinds=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        p: dict = product or {"name": "", "kind": "pack", "credits": 10, "days": 180, "price": 0, "intro_only": False, "about": "", "active": True}
        self.p = p
        hb.text(self.dom_nodes["title"], "Edit pass" if p.get("id") else "New pass")
        self.name_box.text = p.get("name") or ""
        self.kind_box.items = [(hb.KIND.get(k, k), k) for k in kinds or []]
        self.kind_box.selected_value = p.get("kind")
        self.credits_box.text = "" if p.get("credits") is None else str(p["credits"])
        self.days_box.text = str(p.get("days") or 30)
        self.price_box.text = str(p.get("price") or 0)
        self.about_box.text = p.get("about") or ""
        self.intro_box.checked = bool(p.get("intro_only"))
        self.active_box.checked = bool(p.get("active"))

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        v = {"id": self.p.get("id"), "name": self.name_box.text or "", "kind": self.kind_box.selected_value,
             "credits": int(float(self.credits_box.text)) if (self.credits_box.text or "").strip() else None,
             "days": self.days_box.text or "30", "price": self.price_box.text or "0", "about": self.about_box.text or "",
             "intro_only": bool(self.intro_box.checked), "active": bool(self.active_box.checked)}
        r = anvil.server.call("save_product", self.slug, v)
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        state.toast("Saved.", "ok")
        self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
