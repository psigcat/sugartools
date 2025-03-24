from qgis.core import Qgis, QgsProject, QgsLayerTreeLayer, QgsFeature

import os

from .utils import utils


FIELDS_MANDATORY = ["relblocks_id", "relblocks_table"]
RELTABLE_ID = "rel_"


class RelblocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent

        self.utils = utils(self.parent)

        self.preselect_layer()


    def preselect_layer(self):
        """ preselect reltable """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer):
                layer_name = layer.layer().name()
                if RELTABLE_ID in layer_name:
                    relblocks_table = QgsProject.instance().mapLayersByName(layer_name)[0]
                    self.parent.dlg.relblocks_table.setLayer(relblocks_table)


    def process_relblocks(self):
        """ process relations """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        id_block = int(self.parent.dlg.relblocks_id.text())
        reltable = self.parent.dlg.relblocks_table.currentText()

        # !!!for now static!!!
        ua = "r1"
        position = "S"

        # write to relations table
        reltable_layer = QgsProject.instance().mapLayersByName(reltable)[0]
        reltable_layer.startEditing()
        feature = QgsFeature()
        feature.setAttributes([
            None,
            id_block,
            ua,
            position,
            '',
            ''
        ])
        reltable_layer.addFeature(feature)
        reltable_layer.commitChanges()
