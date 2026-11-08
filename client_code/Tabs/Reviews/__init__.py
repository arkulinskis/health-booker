from anvil import *

from ._anvil_designer import ReviewsTemplate
from ... import hb, state


class Reviews(ReviewsTemplate):
    """Back office > Reviews: reply publicly, or hide a review that breaks the rules (hidden ones don't count).
    Server: manage_reviews, reply_review, hide_review."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.load()

    def load(self):
        d = state.call("manage_reviews", self.slug)
        if d is None:
            return
        hb.text(self.dom_nodes["lead"], (("Rated %s · " % hb.rating_text(d.get("rating"), d["rating_n"])) if d.get("rating_n") else "") +
                "Only people who came to a class can review it. Reply publicly, or hide a review that breaks the rules "
                "(abuse, personal details); hidden reviews don't count.")
        self.reviews_panel.items = [{"r": r, "host": self} for r in d["reviews"]]
        self.empty.visible = not d["reviews"]
