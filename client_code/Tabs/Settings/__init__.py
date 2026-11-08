from anvil import *

from ._anvil_designer import SettingsTemplate
from ... import hb, router, state


class Settings(SettingsTemplate):
    """Back office > Settings: the studio profile (styles, amenities, languages, cancel window, colour, waiver), share
    links, the kiosk, CSV exports, and rooms (rows x mats per row; tap a mat to block it).
    Server: manage_settings, save_studio, save_room, export_csv."""

    def __init__(self, slug="", studio=None, **properties):
        super().__init__(**properties)
        self.slug = slug
        state.set_attr(self.kiosk_link, "href", router.href("kiosk", slug))
        self.load()

    def load(self):
        d = state.call("manage_settings", self.slug)
        if d is None:
            return
        self.d: dict = d
        s = d["studio"]
        self.name_box.text = s.get("name") or ""
        self.tagline_box.text = s.get("tagline") or ""
        self.hood_box.text = s.get("neighbourhood") or ""
        self.city_box.text = s.get("city") or ""
        self.address_box.text = s.get("address") or ""
        self.about_box.text = s.get("about") or ""
        self.amen_box.text = ", ".join(s.get("amenities") or [])
        self.lang_box.text = ", ".join(s.get("languages") or [])
        self.cancel_box.text = str(s.get("cancel_hours"))
        self.waiver_box.text = s.get("waiver_text") or ""
        self.styles = set(s.get("styles") or [])
        self.accent = s.get("accent") or "sage"
        self.rooms: list = [dict(r, blocked=list(r.get("blocked") or [])) for r in d["rooms"]]
        self.draw_choices()
        self.draw_rooms()

    def draw_choices(self):
        self.styles_panel.items = [{"group": "style", "key": x, "label": x, "on": x in self.styles, "host": self} for x in self.d["styles"]]
        self.accent_panel.items = [{"key": k, "on": k == self.accent, "host": self} for k in self.d["accents"]]

    def draw_rooms(self):
        self.rooms_panel.items = [{"r": r, "host": self} for r in self.rooms]

    def chip_panel_for(self, group):
        return self.styles_panel

    def chip(self, group, key):
        if key in self.styles:
            self.styles.discard(key)
        else:
            self.styles.add(key)
        self.draw_choices()

    def pick_accent(self, key):
        self.accent = key
        k = state.focus_key()
        self.draw_choices()
        state.refocus(self.accent_panel, k)

    @handle("save_button", "click")
    def save_button_click(self, **event_args):
        split = lambda t: [x.strip() for x in (t or "").split(",") if x.strip()]
        try:
            hours = float(self.cancel_box.text or 12)
        except ValueError:
            hours = 12
        v = {"name": self.name_box.text or "", "tagline": self.tagline_box.text or "", "neighbourhood": self.hood_box.text or "",
             "city": self.city_box.text or "", "address": self.address_box.text or "", "about": self.about_box.text or "",
             "styles": [x for x in self.d["styles"] if x in self.styles], "amenities": split(self.amen_box.text),
             "languages": split(self.lang_box.text), "cancel_hours": hours, "accent": self.accent, "waiver_text": self.waiver_box.text or ""}
        if state.call("save_studio", self.slug, v):
            state.toast("Saved.", "ok")

    def save_room(self, r):
        if state.call("save_room", self.slug, r):
            state.toast("Room saved.", "ok")
            self.load()

    @handle("add_room_button", "click")
    def add_room_button_click(self, **event_args):
        self.rooms.append({"id": None, "name": "Room %d" % (len(self.rooms) + 1), "rows": 3, "cols": 4, "blocked": []})
        self.draw_rooms()

    @handle("solo_button", "click")
    def solo_button_click(self, **event_args):
        hb.copy(hb.link("#studio/" + self.slug + "/solo"))

    @handle("page_button", "click")
    def page_button_click(self, **event_args):
        hb.copy(hb.link("#studio/" + self.slug))

    def _csv(self, kind):
        r = state.call("export_csv", self.slug, kind)
        if r:
            hb.download(r["filename"], r["csv"], "text/csv")
            state.toast("Downloaded " + r["filename"], "ok")

    @handle("csv_clients", "click")
    def csv_clients_click(self, **event_args):
        self._csv("clients")

    @handle("csv_bookings", "click")
    def csv_bookings_click(self, **event_args):
        self._csv("bookings")

    @handle("csv_passes", "click")
    def csv_passes_click(self, **event_args):
        self._csv("passes")
