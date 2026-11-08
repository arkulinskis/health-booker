import anvil.server
from anvil import *

from ._anvil_designer import StaffFormTemplate
from ... import hb, state


class StaffForm(StaffFormTemplate):
    """Invite someone to the team (by email: access when they sign in with it) or edit role, styles, bio and pay
    rule (save_staff). The example line shows what a full and an empty class pay. Closes with True when saved."""

    def __init__(self, slug="", staff=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        self.is_new = staff is None
        t: dict = staff or {"name": "", "email": "", "role": "teacher", "teaches": True, "styles": [], "bio": "",
                            "pay_base": 40, "pay_per_head": 3, "pay_after": 8}
        self.t = t
        hb.text(self.dom_nodes["title"], "Add to the team" if self.is_new else "Edit " + (t.get("name") or ""))
        self.name_box.text = t.get("name") or ""
        self.email_field.visible = self.is_new
        self.role_box.items = [("Teacher", "teacher"), ("Front desk", "desk"), ("Owner", "owner")]
        self.role_box.selected_value = t.get("role") or "teacher"
        self.teaches_box.checked = bool(t.get("teaches"))
        self.styles = set(t.get("styles") or [])
        self.bio_box.text = t.get("bio") or ""
        self.base_box.text = str(t.get("pay_base") or 0)
        self.head_box.text = str(t.get("pay_per_head") or 0)
        self.after_box.text = str(t.get("pay_after") or 0)
        self.save_button.text = "Add" if self.is_new else "Save"
        for box in (self.base_box, self.head_box, self.after_box):
            box.add_event_handler("change", self._example)
        self.draw_styles()
        self._example()

    def draw_styles(self):
        self.styles_panel.items = [{"group": "style", "key": s, "label": s, "on": s in self.styles, "host": self} for s in hb.STYLES]

    def chip_panel_for(self, group):
        return self.styles_panel

    def chip(self, group, key):
        if key in self.styles:
            self.styles.discard(key)
        else:
            self.styles.add(key)
        self.draw_styles()

    def _num(self, box):
        try:
            return float(box.text or 0)
        except ValueError:
            return 0.0

    def _example(self, **event_args):
        b, h, a = self._num(self.base_box), self._num(self.head_box), self._num(self.after_box)
        self.example.text = "A class of 12 pays %s; an empty one pays %s." % (hb.money0(b + h * max(0, 12 - a)), hb.money0(b))

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        v = {"id": self.t.get("id"), "name": self.name_box.text or "", "email": self.email_box.text or "",
             "role": self.role_box.selected_value, "teaches": bool(self.teaches_box.checked),
             "styles": [s for s in hb.STYLES if s in self.styles], "bio": self.bio_box.text or "",
             "pay_base": self.base_box.text or "0", "pay_per_head": self.head_box.text or "0", "pay_after": self.after_box.text or "0"}
        r = anvil.server.call("save_staff", self.slug, v)
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        state.toast("Invited. They get access when they sign in with that email." if r.get("invited") else "Saved.", "ok")
        self.raise_event("x-close-alert", value=True)

    @handle("close_button", "click")
    def close_button_click(self, **event_args):
        self.raise_event("x-close-alert", value=False)
