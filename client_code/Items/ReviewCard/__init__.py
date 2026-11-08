from anvil import *

from ._anvil_designer import ReviewCardTemplate
from ... import hb


class ReviewCard(ReviewCardTemplate):
    """A review (studio page, class page, Teach). item = {r, studio, mode}: mode "teach" shows the class instead of
    the reviewer; the studio's public reply shows under it."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        r: dict = it["r"]
        d = self.dom_nodes
        hb.stars(d["stars"], r.get("stars") or 0)
        hb.text(d["when"], hb.ago(r.get("created")))
        hb.text(d["body"], r.get("text") or "")
        if it.get("mode") == "teach":
            hb.text(d["who"], r.get("class") or "")
        else:
            hb.text(d["who"], (r.get("who") or "") + " · " + (r.get("class") or "") + (
                (" with " + r["teacher"]) if r.get("teacher") and it.get("mode") == "studio" else ""))
        self.reply.visible = bool(r.get("reply"))
        if r.get("reply"):
            hb.text(d["reply_from"], (it.get("studio") or "The studio") + ":")
            hb.text(d["reply_text"], r["reply"])
        self.card.classes["tight"] = it.get("mode") != "studio"
