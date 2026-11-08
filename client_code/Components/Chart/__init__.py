from anvil import *

from ._anvil_designer import ChartTemplate
from ... import hb


class Chart(ChartTemplate):
    """A chart drawn by theme/assets/hb-draw.js (HBD.chart): kind = heat | mood | hbars | cols | fillgrid, with hover
    tips. draw(kind, data) redraws it."""

    def __init__(self, **properties):
        super().__init__(**properties)

    def draw(self, kind, data):
        hb.chart(self.dom_nodes["box"], kind, data)
