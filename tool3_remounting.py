from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import Qgis, QgsProject

import os
import xlrd


from .utils import utils


COMBO_SELECT = "(Select)"
FIELDS_DEFAULT = {
    "remounting_part": "num_pieza",
    "remounting_coordx": "coord_x",
    "remounting_coordy": "coord_y",
    "remounting_origen": "origen",
    "remounting_destiny": "destino",
    "remounting_remounting": "Clase Rem",
    "remounting_labels": "num_pieza"
}
FIELDS_MANDATORY_REMOUNTING = ["remounting_excel", "remounting_sheet", "remounting_part", "remounting_coordx", "remounting_coordy", "remounting_origen", "remounting_destiny", "remounting_remounting", "remounting_labels"]


class RemountingTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.book = None
        self.sheet = None

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.parent.dlg.remounting_excel.fileChanged.connect(self.load_excel)


    def process_remounting(self):
        """ process """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_REMOUNTING):
            return False

        print("process")


    def load_excel(self):
        """ load sheets from excel """

        if self.book:
            self.parent.dlg.remounting_sheet.currentIndexChanged.disconnect(self.load_excel_sheet)

        self.parent.dlg.remounting_sheet.clear()
        self.parent.dlg.remounting_sheet.addItem(COMBO_SELECT)

        file_path = self.parent.dlg.remounting_excel.filePath()
        self.book = xlrd.open_workbook(file_path)
        print("The number of worksheets is {0}".format(self.book.nsheets))
        print("Worksheet name(s): {0}".format(self.book.sheet_names()))

        for index in range(self.book.nsheets):
            sheet = self.book.sheet_by_index(index)
            self.parent.dlg.remounting_sheet.addItem(sheet.name)

        self.parent.dlg.remounting_sheet.currentIndexChanged.connect(self.load_excel_sheet)


    def load_excel_sheet(self):
        """ load columns from excel sheet """

        index = self.parent.dlg.remounting_sheet.currentIndex()
        self.sheet = self.book.sheet_by_index(index)

        self.clear_parts()
        for column_index in range(self.sheet.ncols):
            name = self.sheet.cell_value(0, column_index)
            self.fill_parts(name)

        self.select_default()


    def clear_parts(self):
        """ empty column combo boxes """

        self.parent.dlg.remounting_part.clear()
        self.parent.dlg.remounting_part.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_coordx.clear()
        self.parent.dlg.remounting_coordx.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_coordy.clear()
        self.parent.dlg.remounting_coordy.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_origen.clear()
        self.parent.dlg.remounting_origen.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_destiny.clear()
        self.parent.dlg.remounting_destiny.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_remounting.clear()
        self.parent.dlg.remounting_remounting.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_labels.clear()
        self.parent.dlg.remounting_labels.addItem(COMBO_SELECT)


    def fill_parts(self, name):
        """ fill column combo boxes """

        self.parent.dlg.remounting_part.addItem(name)
        self.parent.dlg.remounting_coordx.addItem(name)
        self.parent.dlg.remounting_coordy.addItem(name)
        self.parent.dlg.remounting_origen.addItem(name)
        self.parent.dlg.remounting_destiny.addItem(name)
        self.parent.dlg.remounting_remounting.addItem(name)
        self.parent.dlg.remounting_labels.addItem(name)


    def select_default(self):
        """ select default values for column combo boxes """

        for key in FIELDS_DEFAULT:
            widget = self.parent.dlg.tabWidgetMain.widget(2).findChild(QComboBox, key)
            widget.setCurrentText(FIELDS_DEFAULT[key])