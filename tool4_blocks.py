from qgis.core import Qgis, QgsProject

import os


from .utils import utils



class BlocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent

        self.utils = utils(self.parent)
