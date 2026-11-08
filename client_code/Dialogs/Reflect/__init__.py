from anvil import *

from ._anvil_designer import ReflectTemplate
from ... import hb, state


class Reflect(ReflectTemplate):
    """After class: mood (1-5) + a private note (reflect), and an optional public review (review_class) once.
    Closes with True when something was saved."""

    def __init__(self, booking=None, **properties):
        super().__init__(**properties)
        self.b: dict = booking or {}
        c: dict = self.b["class"]
        self.mood = self.b.get("mood") or 0
        self.stars = 0
        hb.text(self.dom_nodes["lead"], "%s · %s. Only you see your journal." % (c["title"], hb.date(c["start"])))
        for i in range(1, 6):
            hb.face(hb.loose(self.dom_nodes)["face_%d" % i], i)
        self.note_box.text = self.b.get("note") or ""
        state.set_control_attr(self.note_box, "aria-label", "A note for future you")
        state.set_control_attr(self.review_box, "aria-label", "Your review")
        self.review_part.visible = not self.b.get("reviewed")
        self._draw()

    def _draw(self):
        for i in range(1, 6):
            m = getattr(self, "mood_%d" % i)
            m.classes["on"] = i == self.mood
            state.set_attr(m, "aria-pressed", "true" if i == self.mood else "false")
            s = getattr(self, "star_%d" % i)
            s.classes["on"] = i <= self.stars
            state.set_attr(s, "aria-pressed", "true" if i <= self.stars else "false")

    def mood_click(self, event):
        self.mood = int(event.currentTarget.getAttribute("data-mood"))
        self._draw()

    def star_click(self, event):
        self.stars = int(event.currentTarget.getAttribute("data-star"))
        self.review_box.visible = True
        self._draw()

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        if not self.mood and not self.stars:
            state.toast("Choose how you feel (or some stars) first.")
            return
        self.save_button.enabled = False
        try:
            ok = True
            if self.mood:
                ok = state.call("reflect", self.b["id"], self.mood, self.note_box.text or "") is not None
            if ok and self.stars:
                ok = state.call("review_class", self.b["id"], self.stars, self.review_box.text or "") is not None
        finally:
            self.save_button.enabled = True
        if ok:
            state.toast("Saved. Thank you for the review!" if self.stars else "Saved to your journal.", "ok")
            self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
