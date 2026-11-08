from anvil import *

from ._anvil_designer import FriendLinkTemplate
from ... import hb, state


class FriendLink(FriendLinkTemplate):
    """The friend pass link just made: copy it and send it to a friend."""

    def __init__(self, studio="", link="", **properties):
        super().__init__(**properties)
        self.link = link
        hb.text(self.dom_nodes["text"], "Send this link to a friend who's never been to %s. Their first class is free." % studio)
        self.link_box.text = link
        state.set_control_attr(self.link_box, "readonly", "readonly")

    @handle("copy_button", "click")
    def copy_button_click(self, **event_args):
        hb.copy(self.link, "Copied. Send it to your friend!")

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=None)
