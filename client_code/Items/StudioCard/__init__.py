from anvil import *
import anvil.js

from ._anvil_designer import StudioCardTemplate
from ... import hb, router, state


class StudioCard(StudioCardTemplate):
    """A studio in Discover > Studios. item = {s, fav, me, host}. The name is the link; the heart follows it."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        s: dict = it["s"]
        self.s = s
        d = self.dom_nodes
        hb.set_acc(self.card, s.get("accent"))
        self.featured.visible = bool(s.get("featured"))
        d["name_link"].setAttribute("href", router.href("studio", s["slug"]))
        hb.text(d["name_link"], s["name"])
        hb.text(d["hood"], s.get("neighbourhood"))
        if s.get("rating_n"):
            hb.stars(d["stars"], s.get("rating") or 0)
            hb.text(d["rating"], " %.1f (%d)" % (float(s.get("rating") or 0), s["rating_n"]))
        else:
            hb.text(d["rating"], "New on Health Booker")
        hb.text(d["tagline"], s.get("tagline"))
        hb.fill(d["tags"], [(x, "hb-tag", None) for x in (s.get("styles") or [])[:4]])
        intro: dict = s.get("intro") or {}
        self.intro.visible = bool(intro)
        if intro:
            hb.text(d["intro_name"], "New here? " + (intro.get("name") or ""))
            hb.text(d["intro_price"], hb.money(intro.get("price")))
        self.fav_button.visible = bool(it.get("me"))
        fav = bool(it.get("fav"))
        self.fav_button.text = "Unfollow " + s["name"] if fav else "Follow " + s["name"]
        self.fav_button.role = ["btn", "btn-icon", "btn-sm", "fav", "ic-heartfill" if fav else "ic-heart"]
        anvil.js.get_dom_node(self.card).addEventListener("click", self._open)

    def _open(self, event):
        if event.target.closest("a, button"):
            return
        router.go("studio", self.s["slug"])

    @handle("fav_button", "click")
    def fav_button_click(self, **event_args):
        self.item["host"].follow_studio(self.s["slug"])
