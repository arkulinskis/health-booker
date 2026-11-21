from anvil import *

from ._anvil_designer import KindnessRowTemplate
from ... import hb, state


class KindnessRow(KindnessRowTemplate):
    """One "ask for kindness" request on the Today board. item = {k: request dict, host}; the buttons call
    host.kindness(request, forgive, reply)."""

    def __init__(self, **properties):
        super().__init__(**properties)
        k: dict = self.item["k"]
        d = self.dom_nodes
        kind = "no-show" if k.get("kind") == "no_show" else "late cancel"
        hb.text(d["initials"], state.initials(k.get("who")))
        hb.text(d["title"], "%s · %s" % (k.get("who"), kind))
        visits = k.get("visits") or 0
        hb.text(d["sub"], "%s, %s · %s · asked %s" % (k.get("class"), hb.date(k["start"]) if k.get("start") else "",
                                                   ("first visit" if not visits else hb.plural(visits, "class", "classes") + " here"),
                                                   hb.ago(k.get("created"))))
        hb.text(d["reason"], k.get("reason") or "Other")
        hb.text(d["note"], k.get("note") or "")
        d["note"].hidden = not k.get("note")
        state.set_control_attr(self.reply_box, "aria-label", "Optional note back to %s" % hb.first_name(k.get("who")))

    def _answer(self, forgive):
        for b in (self.keep_button, self.forgive_button):
            b.enabled = False
        try:
            self.item["host"].kindness(self.item["k"], forgive, self.reply_box.text or "")
        finally:
            if self.parent is not None:
                for b in (self.keep_button, self.forgive_button):
                    b.enabled = True

    @handle("forgive_button", "click")
    def forgive_button_click(self, **event_args):
        self._answer(True)

    @handle("keep_button", "click")
    def keep_button_click(self, **event_args):
        self._answer(False)
