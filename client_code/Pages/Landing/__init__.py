from anvil import *

from ._anvil_designer import LandingTemplate
from ... import state

# The app's video on the Addanapp YouTube channel (APP_MAKER/youtube/manifest.json), shown in the Watch section.
YT_VIDEO = "4BjAXdLkvMY"


class Landing(LandingTemplate):
    """#landing (Persuade): students and studio owners. The hero picture is HTML/CSS + an inline SVG; the Watch
    section plays the YouTube video only when pressed; then features, "what studios told us", steps and questions.
    Static copy lives in the template."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.guest_cta.visible = not me
        self.member_cta.visible = bool(me)
        self.dom_nodes["yt_cover"].addEventListener("click", self._play)

    def _play(self, event):
        """Swap the video's cover for YouTube's player (privacy-enhanced); nothing loads from YouTube before this click."""
        self.dom_nodes["yt_frame"].innerHTML = (
            '<iframe src="https://www.youtube-nocookie.com/embed/' + YT_VIDEO + '?autoplay=1&rel=0&playsinline=1" '
            'title="Health Booker video" allow="autoplay; encrypted-media; picture-in-picture; fullscreen" allowfullscreen '
            'referrerpolicy="strict-origin-when-cross-origin"></iframe>')
