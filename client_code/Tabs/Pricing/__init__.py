from anvil import *

from ._anvil_designer import PricingTemplate
from ... import hb, state


class Pricing(PricingTemplate):
    """Back office > Pricing: the passes for sale (intro offers, drop-ins, packs, memberships), how many sold, edit or
    hide them. Server: manage_products, save_product."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.load()

    def load(self):
        d = state.call("manage_products", self.slug)
        if d is None:
            return
        self.d: dict = d
        self.products_panel.items = [{"p": p, "host": self} for p in d["products"]]

    def edit(self, p):
        from ...Dialogs.ProductForm import ProductForm
        if hb.ask(ProductForm(slug=self.slug, product=p, kinds=self.d["kinds"])):
            self.load()

    @handle("new_button", "click")
    def new_button_click(self, **event_args):
        self.edit(None)
