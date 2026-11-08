from anvil import *
import anvil.js

from ._anvil_designer import ClassRowTemplate
from ... import hb, router


class ClassRow(ClassRowTemplate):
    """One class on a schedule (Discover, a studio's schedule, Practice > Upcoming).
    item = {c, mine, mode, b, solo, host}: mode "market" shows the studio, "studio" hides it, "upcoming" adds the
    booking line (mat, pass, calendar, cancel). The title is the real link; the rest of the card opens it too.
    host.book_row(c, button) / host.cancel_row(b) do the work and reload the page."""

    def __init__(self, **properties):
        super().__init__(**properties)
        it: dict = self.item
        c: dict = it["c"]
        self.c = c
        mode = it.get("mode") or "market"
        mine = it.get("mine")
        s: dict = c.get("studio") or {}
        d = self.dom_nodes
        hb.set_acc(self.card, s.get("accent"))
        self.card.classes["cancelled"] = c.get("status") == "cancelled"
        clock, ampm = hb.time_parts(c["start"])
        hb.text(d["t_clock"], clock)
        hb.text(d["t_ampm"], ampm)
        hb.text(d["t_sub"], hb.mins(c.get("minutes")))
        self._href = router.href("class", c["id"], "solo" if it.get("solo") else "")
        d["title_link"].setAttribute("href", self._href)
        hb.text(d["title_link"], c["title"])
        show_studio = mode != "studio"
        self.studio_link.visible = show_studio
        self.hood.visible = show_studio
        if show_studio:
            from ... import state
            state.set_attr(self.studio_link, "href", router.href("studio", s.get("slug")))
            hb.text(d["studio_name"], s.get("name"))
            hb.text(d["hood_text"], s.get("neighbourhood"))
        hb.text(d["teacher"], (c.get("teacher") or {}).get("name") or "")
        hb.leaves(d["leaves"], c.get("intensity"))
        hb.fill(d["tags"], hb.class_tags(c))
        left, low = hb.spots(c)
        hb.text(d["left"], left)
        d["left"].className = "hb-left" + (" low" if low else "")
        booked = mine in ("booked", "checked_in")
        self.state_booked.visible = booked
        self.state_wait.visible = mine == "waitlist"
        self.book_button.visible = not booked and mine != "waitlist" and c.get("status") != "cancelled"
        full = (c.get("left") or 0) <= 0
        self.book_button.text = "Join waitlist" if full else "Book"
        self.book_button.role = ["btn", "btn-sm"] if full else ["btn", "btn-sm", "btn-primary"]
        self.extra.visible = mode == "upcoming"
        if mode == "upcoming":
            b: dict = it["b"]
            wait = b["status"] == "waitlist"
            hb.text(d["mat_badge"], ("#%s on the waitlist" % b.get("waitlist_pos")) if wait else
                    ("Mat " + b["spot"]) if b.get("spot") else "Any mat")
            d["mat_badge"].className = "ui-badge warn" if wait else "ui-badge"
            hb.text(d["pass_name"], b.get("pass_name"))
            self.cal_button.visible = b["status"] == "booked"
            self.cancel_button.text = "Leave waitlist" if wait else "Cancel"
        anvil.js.get_dom_node(self.card).addEventListener("click", self._open)

    def _open(self, event):
        if event.target.closest("a, button"):
            return
        router.go("class", self.c["id"], "solo" if self.item.get("solo") else "")

    @handle("book_button", "click")
    def book_button_click(self, **event_args):
        self.item["host"].book_row(self.c, self.book_button)

    @handle("cal_button", "click")
    def cal_button_click(self, **event_args):
        hb.ics(self.c)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.item["host"].cancel_row(self.item["b"])
