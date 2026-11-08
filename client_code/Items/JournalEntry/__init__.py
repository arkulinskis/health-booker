from anvil import *
from anvil.js import window

from ._anvil_designer import JournalEntryTemplate
from ... import hb, state


class JournalEntry(JournalEntryTemplate):
    """A class in the journal: date, class, the note, and the mood face (press it to reflect). item = {b, host}."""

    def __init__(self, **properties):
        super().__init__(**properties)
        b: dict = self.item["b"]
        c: dict = b["class"]
        d = self.dom_nodes
        hb.set_acc(self.row, (c.get("studio") or {}).get("accent"))
        hb.text(d["month"], window.HBD.fmt.monthShort(c["start"]))
        hb.text(d["day"], window.HBD.fmt.dayNum(c["start"]))
        hb.text(d["title"], c["title"])
        hb.text(d["meta"], "%s · %s" % ((c.get("studio") or {}).get("name") or "", (c.get("teacher") or {}).get("name") or ""))
        hb.text(d["note"], ('"%s"' % b["note"]) if b.get("note") else "")
        d["note"].hidden = not b.get("note")
        if b.get("mood"):
            hb.face(d["face"], b["mood"])
            hb.text(d["face_word"], hb.MOODS[int(b["mood"]) - 1])
            state.set_attr(self.face_btn, "aria-label", "Reflection: " + hb.MOODS[int(b["mood"]) - 1] + ". Edit it")
        else:
            d["face"].className = "ic ic-plus"
            hb.text(d["face_word"], "How was it?")
            state.set_attr(self.face_btn, "aria-label", "Add a reflection for " + c["title"])

    def face_click(self, event):
        self.item["host"].reflect(self.item["b"])
