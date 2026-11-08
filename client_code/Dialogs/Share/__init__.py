from anvil import *

from ._anvil_designer import ShareTemplate
from ... import hb


class Share(ShareTemplate):
    """Share a studio: the marketplace page link, or the direct booking link (#studio/<slug>/solo)."""

    def __init__(self, name="", slug="", **properties):
        super().__init__(**properties)
        self.slug = slug
        hb.text(self.dom_nodes["title"], "Share " + name)

    @handle("page_button", "click")
    def page_button_click(self, **event_args):
        hb.copy(hb.link("#studio/" + self.slug))

    @handle("solo_button", "click")
    def solo_button_click(self, **event_args):
        hb.copy(hb.link("#studio/" + self.slug + "/solo"))

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
