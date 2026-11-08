from anvil import *

from ._anvil_designer import MgReviewTemplate
from ... import hb, state


class MgReview(MgReviewTemplate):
    """A review in the back office: reply, hide / show. item = {r, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        r: dict = self.item["r"]
        d = self.dom_nodes
        self.card.classes["hidden-rev"] = bool(r.get("hidden"))
        hb.stars(d["stars"], r.get("stars") or 0)
        hb.text(d["who"], "%s · %s · %s" % (r.get("who"), r.get("class"), hb.ago(r.get("created"))))
        hb.text(d["text"], r.get("text") or "(no text)")
        self.reply_box.text = r.get("reply") or ""
        state.set_control_attr(self.reply_box, "aria-label", "Public reply to " + (r.get("who") or "this review"))
        self.hide_button.text = "Show again" if r.get("hidden") else "Hide"

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if state.call("reply_review", self.item["r"]["id"], self.reply_box.text or "") is not None:
            state.toast("Reply saved.", "ok")

    @handle("hide_button", "click")
    def hide_button_click(self, **event_args):
        if state.call("hide_review", self.item["r"]["id"], not self.item["r"].get("hidden")) is not None:
            self.item["host"].load()
