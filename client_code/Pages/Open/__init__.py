import anvil.server
from anvil import *

from ._anvil_designer import OpenTemplate
from ... import hb, router, state


class Open(OpenTemplate):
    """#open: "List your studio". A one-page form with a live preview of the studio card. Creates the studio (in
    review until an admin publishes it; admins' studios go live at once), its first room, the owner as staff and four
    starter passes. Server: create_studio. Signed-out visitors see the pitch and a sign-up button."""

    def __init__(self, args=(), **properties):
        super().__init__(**properties)
        me = state.me()
        self.guest.visible = not me
        self.member.visible = bool(me)
        if not me:
            return
        self.styles = set(hb.STYLES[:2])
        self.accent = "sage"
        mine = [r["name"] for r in me.get("roles") or [] if r.get("role") == "owner"]
        hb.text(self.dom_nodes["lead"], "Two minutes now; you can change everything later in Manage." +
                (" You already run %s." % ", ".join(mine) if mine else ""))
        hb.text(self.dom_nodes["hint"], "You're an admin, so it goes live straight away." if me.get("is_admin") else
                "An admin reviews new studios (usually within a day). Meanwhile you can set up everything and preview your page.")
        self.lang_box.items = [("English", "English"), ("Français", "Français"), ("English and Français", "both")]
        state.set_control_attr(self.lang_box, "aria-label", "Languages you teach in")
        for box in (self.name_box, self.tagline_box, self.hood_box, self.city_box, self.rows_box, self.cols_box):
            box.add_event_handler("change", self._changed)
        self.draw_choices()
        self.preview_draw()

    def draw_choices(self):
        self.styles_panel.items = [{"group": "style", "key": s, "label": s, "on": s in self.styles, "host": self} for s in hb.STYLES]
        self.accent_panel.items = [{"key": k, "on": k == self.accent, "host": self} for k in hb.ACCENTS]

    def chip_panel_for(self, group):
        return self.styles_panel

    def chip(self, group, key):
        if key in self.styles:
            self.styles.discard(key)
        else:
            self.styles.add(key)
        self.draw_choices()
        self.preview_draw()

    def pick_accent(self, key):
        self.accent = key
        k = state.focus_key()
        self.draw_choices()
        state.refocus(self.accent_panel, k)
        self.preview_draw()

    def _changed(self, **event_args):
        self.preview_draw()

    def _num(self, box, default):
        try:
            return max(1, min(10, int(box.text or default)))
        except ValueError:
            return default

    def values(self):
        lang = self.lang_box.selected_value or "English"
        return {"name": (self.name_box.text or "").strip(), "tagline": self.tagline_box.text or "",
                "neighbourhood": (self.hood_box.text or "").strip(), "city": self.city_box.text or "",
                "address": self.address_box.text or "", "about": self.about_box.text or "",
                "styles": [s for s in hb.STYLES if s in self.styles], "accent": self.accent,
                "rows": self._num(self.rows_box, 4), "cols": self._num(self.cols_box, 5),
                "languages": ["English", "Français"] if lang == "both" else [lang]}

    def preview_draw(self):
        v, d = self.values(), self.dom_nodes
        hb.set_acc(self.preview, v["accent"])
        hb.text(d["p_name"], v["name"] or "Your studio")
        hb.text(d["p_hood"], v["neighbourhood"] or "Neighbourhood")
        hb.text(d["p_tag"], v["tagline"] or "Your tagline")
        hb.fill(d["p_styles"], [(s, "hb-tag", None) for s in v["styles"][:4]])
        hb.text(d["p_room"], "Room: %d mats" % (v["rows"] * v["cols"]))

    @handle("open_button", "click")
    def open_button_click(self, **event_args):
        v = self.values()
        if len(v["name"]) < 3 or not v["neighbourhood"]:
            self.message.text, self.message.visible = "Give your studio a name (3+ letters) and a neighbourhood.", True
            return
        self.message.visible = False
        self.open_button.enabled = False
        try:
            r = anvil.server.call("create_studio", v)
        finally:
            self.open_button.enabled = True
        if not r.get("ok"):
            self.message.text, self.message.visible = r.get("error") or "That didn't work.", True
            return
        state.set_me(anvil.server.call("get_me"))
        state.toast("Your studio is live!" if r.get("status") == "live" else "Studio created. It's in review; set it up meanwhile.", "ok")
        router.go("manage", r["slug"])

    @handle("start_button", "click")
    def start_button_click(self, **event_args):
        router.need_account("#open", "Create your free account first, then open your studio.")
