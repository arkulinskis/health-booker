import anvil.server
from anvil import *

from ._anvil_designer import WaiverTemplate
from ... import hb, state


class Waiver(WaiverTemplate):
    """A studio's waiver, signed once per studio before the first booking (sign_waiver). Closes with True when signed."""

    def __init__(self, studio=None, waiver_text="", **properties):
        super().__init__(**properties)
        self.studio: dict = studio or {}
        hb.text(self.dom_nodes["lead"], "%s asks every new student to sign this once. It takes 20 seconds." % self.studio.get("name"))
        hb.text(self.dom_nodes["text"], waiver_text)
        self.signature_box.text = (state.me() or {}).get("name") or ""
        state.set_control_attr(self.signature_box, "autocomplete", "name")

    @handle("sign_button", "click")
    def sign_button_click(self, **event_args):
        sig = (self.signature_box.text or "").strip()
        if len(sig) < 3:
            self.message.text, self.message.visible = "Type your full name to sign.", True
            return
        self.sign_button.enabled = False
        try:
            r = anvil.server.call("sign_waiver", self.studio["slug"], sig, self.emergency_box.text or "",
                                  self.health_box.text or "", bool(self.share_box.checked))
        finally:
            self.sign_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        self.raise_event("x-close-alert", value=True)

    @handle("cancel_button", "click")
    def cancel_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
