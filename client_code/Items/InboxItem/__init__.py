from anvil import *

from ._anvil_designer import InboxItemTemplate
from ... import hb, state

ICON = {"waitlist": "clock", "cancelled": "x", "sub": "swap", "nudge": "chat", "reply": "star", "forgiven": "heart",
        "friend": "gift", "team": "users", "studio": "door", "pause": "calendar"}


class InboxItem(InboxItemTemplate):
    """One message. item = {n}: unread ones are marked; a studio's colour and a link when there is one."""

    def __init__(self, **properties):
        super().__init__(**properties)
        n: dict = self.item["n"]
        s = n.get("studio")
        d = self.dom_nodes
        self.card.classes["new"] = not n.get("read")
        if s:
            hb.set_acc(self.card, s.get("accent"))
        d["icon"].className = "ic ic-" + ICON.get(n.get("kind"), "bell")
        hb.text(d["title"], n.get("title"))
        hb.text(d["body"], n.get("body") or "")
        d["body"].hidden = not n.get("body")
        self.studio.visible = bool(s)
        hb.text(d["studio_name"], (s or {}).get("name") or "")
        self.open_link.visible = bool(n.get("link"))
        if n.get("link"):
            state.set_attr(self.open_link, "href", n["link"])
        hb.text(d["when"], hb.ago(n.get("created")))
