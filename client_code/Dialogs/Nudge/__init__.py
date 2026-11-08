from anvil import *

from ._anvil_designer import NudgeTemplate
from ... import hb, state


def template(c, tag, studio):
    first = hb.first_name(c.get("name"))
    tags = c.get("tags") or []
    if tag == "drifting" or "drifting" in tags:
        return "Hi %s, we miss you on the mat! Your pass is still waiting. Is there a time that would suit you better? - %s" % (first, studio)
    if tag == "intro" or "intro" in tags:
        return ("Hi %s, so glad you came in! How are you finding the classes? If you have questions about which pass fits you, "
                "just reply at the desk. - %s" % (first, studio))
    if tag == "expiring" or "expiring" in tags:
        return "Hi %s, a heads-up that your pass ends soon. We'd love to keep practising with you! - %s" % (first, studio)
    return "Hi %s, thanks for practising with us. - %s" % (first, studio)


class Nudge(NudgeTemplate):
    """A friendly personal note to one client or a group (nudge, one call per person). Closes with True when sent."""

    def __init__(self, slug="", studio="", people=None, tag=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.people = people or []
        one = len(self.people) == 1
        hb.text(self.dom_nodes["title"], ("Message " + self.people[0]["name"]) if one else "Message %d people" % len(self.people))
        self.msg_box.text = template(self.people[0] if one else {"name": "{name}", "tags": [tag]}, tag, studio)
        state.set_control_attr(self.msg_box, "aria-label", "Your message")

    @handle("send_button", "click")
    def send_button_click(self, **event_args):
        text = self.msg_box.text or ""
        self.send_button.enabled = False
        try:
            for c in self.people:
                if state.call("nudge", self.slug, c["id"], text.replace("{name}", hb.first_name(c.get("name")))) is None:
                    return
        finally:
            self.send_button.enabled = True
        state.toast("Sent to %s." % hb.plural(len(self.people), "person", "people"), "ok")
        self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
