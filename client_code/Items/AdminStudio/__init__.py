from anvil import *

from ._anvil_designer import AdminStudioTemplate
from ... import hb, router, state


class AdminStudio(AdminStudioTemplate):
    """A studio in Admin > Studios: publish (review -> live), pause, feature it on Discover. item = admin_studios row."""

    def __init__(self, **properties):
        super().__init__(**properties)
        s: dict = self.item
        d = self.dom_nodes
        hb.set_acc(self.row, s.get("accent"))
        d["name_link"].setAttribute("href", router.href("studio", s["slug"]))
        hb.text(d["name_link"], s["name"])
        self.demo.visible = bool(s.get("demo"))
        hb.text(d["line1"], "%s · %s" % (s.get("neighbourhood") or "", s.get("tagline") or ""))
        hb.text(d["line2"], "Owner: %s%s · %s upcoming classes · added %s" % (s.get("owner") or "", (" (%s)" % s["owner_email"]) if s.get("owner_email") else "",
                                                                            s.get("classes", 0), hb.full_date(s.get("created"))))
        self.status_box.items = [("Live", "live"), ("In review", "review"), ("Paused", "paused")]
        self.status_box.selected_value = s.get("status")
        state.set_control_attr(self.status_box, "aria-label", "Status of " + s["name"])
        self.featured_box.checked = bool(s.get("featured"))
        state.set_attr(self.manage_link, "href", router.href("manage", s["slug"]))

    @handle("status_box", "change")
    def status_box_change(self, **event_args):
        if state.call("admin_set_studio", self.item["slug"], self.status_box.selected_value, None) is not None:
            state.toast("Saved", "ok")

    @handle("featured_box", "change")
    def featured_box_change(self, **event_args):
        if state.call("admin_set_studio", self.item["slug"], None, bool(self.featured_box.checked)) is not None:
            state.toast("Saved", "ok")
