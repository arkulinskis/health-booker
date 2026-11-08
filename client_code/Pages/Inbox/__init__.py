from anvil import *

from ._anvil_designer import InboxTemplate
from ... import router, state


class Inbox(InboxTemplate):
    """#inbox: messages from studios and the app (waitlist moves, cancellations, subs, studio notes, replies to
    reviews). Opening the page marks everything read. Server: inbox, inbox_read."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        d: dict = state.call("inbox") or {"items": [], "unread": 0}
        self.items_panel.items = [{"n": n} for n in d["items"]]
        self.empty.visible = not d["items"]
        if d.get("unread"):
            state.call_quiet("inbox_read", None)
            me = state.me()
            if me:
                me["unread"] = 0
