from qgis.core import Qgis, QgsProject, QgsLayerTreeLayer, QgsFeature
from PyQt5.QtWidgets import QTableWidget, QTableWidgetItem, QPushButton, QWidget, QHBoxLayout

import os

from .utils import utils


FIELDS_MANDATORY = ["relblocks_table"]
RELTABLE_ID = "rel_"


class RelblocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent

        self.utils = utils(self.parent)
        self.table = self.parent.dlg.relblocks_relations

        self.reset_ui()


    def reset_ui(self):
        """ reset UI """

        self.table.clear()
        self.preselect_layer()
        self.setup_table()


    def preselect_layer(self):
        """ preselect reltable """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer):
                layer_name = layer.layer().name()
                layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                if RELTABLE_ID in layer_name:
                    self.parent.dlg.relblocks_table.setLayer(layer)


    def setup_table(self):
        """ create table elements """

        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Block id", "UA (arqueological unit)", "Position", "Action"])

        # Populate table with first empty row
        self.table.setRowCount(1)
        row = 0
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setItem(row, 2, QTableWidgetItem(""))
        self.add_action_buttons(row)


    def add_action_buttons(self, row):
        """add buttons to action cell"""

        cell_widget = QWidget()
        layout = QHBoxLayout(cell_widget)
        layout.setContentsMargins(0, 0, 0, 0)

        button = QPushButton("Add Row")
        button.clicked.connect(self.add_row)
        layout.addWidget(button)

        if row > 0:
            button = QPushButton("Remove Row")
            button.clicked.connect(lambda: self.remove_row(row))
            layout.addWidget(button)

        cell_widget.setLayout(layout)
        self.table.setCellWidget(row, 3, cell_widget)


    def remove_row(self, row):
        """ remove row from table"""

        self.table.removeRow(row)

        # Update button connections (because row indices shift)
        for r in range(self.table.rowCount()):
            widget = self.table.cellWidget(r, 3)
            if widget:
                layout = widget.layout()
                if layout.count() > 1:
                    remove_button = layout.itemAt(1).widget()
                    remove_button.clicked.disconnect()
                    remove_button.clicked.connect(lambda checked, r=r: self.remove_row(r))


    def add_row(self):
        """Add a new row to the table"""

        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))
        self.table.setItem(row, 2, QTableWidgetItem(""))
        self.add_action_buttons(row)


    def process_relblocks(self):
        """ process relations """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        i = 0
        for r in range(self.table.rowCount()):
            id = self.table.item(r, 0).text()
            ua = self.table.item(r, 1).text()
            position = self.table.item(r, 2).text()

            if id != None and ua != None and position != None and id != "" and ua != "" and position != "":
                self.write_feature(id, ua, position)
                i += 1

        self.parent.dlg.messageBar.pushMessage(f"{i} Relations written to table: '{self.parent.dlg.relblocks_table.currentText()}'", level=Qgis.Success)


    def write_feature(self, id, ua, position):
        """ write feature to reltable """

        reltable = self.parent.dlg.relblocks_table.currentText()
        reltable_layer = QgsProject.instance().mapLayersByName(reltable)[0]
        reltable_layer.startEditing()
        feature = QgsFeature()
        feature.setAttributes([
            None,
            id,
            ua,
            position,
            None,
            None
        ])
        reltable_layer.addFeature(feature)
        reltable_layer.commitChanges()
