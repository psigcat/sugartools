from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import Qgis, QgsProject, QgsPointXY, QgsDistanceArea

import os
import xlrd
import xlwt
import math


from .utils import utils


COMBO_SELECT = "(Select)"
FIELDS_DEFAULT = {
    "remounting_part": "num_pieza",
    "remounting_coordx": "coord_x",
    "remounting_coordy": "coord_y",
    "remounting_origin": "Origen",
    "remounting_target": "Destino",
    "remounting_remounting": "Clase Rem",
    "remounting_labels": "num_pieza",
    "remounting_colors": "color_tremon"
}
FIELDS_MANDATORY_REMOUNTING = ["remounting_excel", "remounting_sheet", "remounting_part", "remounting_coordx", "remounting_coordy", "remounting_origin", "remounting_target", "remounting_remounting", "remounting_labels"]


class RemountingTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.book = None
        self.sheet = None
        self.col_indexes = {}
        self.parts = {}

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.parent.dlg.remounting_excel.fileChanged.connect(self.load_excel)


    def process_remounting(self):
        """ process """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_REMOUNTING):
            return False

        print("process")

        self.read_parts()
        #print(self.parts)

        # save excel
        # file_path = self.parent.dlg.remounting_excel.filePath()
        # self.wb = xlwt.Workbook(file_path)
        # index = self.parent.dlg.remounting_sheet.currentIndex() - 1
        # self.process_parts(self.wb.get_sheet(index))
        # self.wb.save(file_path)


    def read_parts(self):
        """ read parts row by row """

        for rx in range(1, self.sheet.nrows):
            #print(rx, self.sheet.row(rx))

            part_index = self.col_indexes[self.parent.dlg.remounting_part.currentText()]
            coordx_index = self.col_indexes[self.parent.dlg.remounting_coordx.currentText()]
            coordy_index = self.col_indexes[self.parent.dlg.remounting_coordy.currentText()]
            origin_index = self.col_indexes[self.parent.dlg.remounting_origin.currentText()]
            target_index = self.col_indexes[self.parent.dlg.remounting_target.currentText()]
            remounting_index = self.col_indexes[self.parent.dlg.remounting_remounting.currentText()]
            labels_index = self.col_indexes[self.parent.dlg.remounting_labels.currentText()]
            #colors_index = self.col_indexes[self.parent.dlg.remounting_colors.currentText()]

            part = int(self.sheet.cell_value(rx, part_index))
            coordx = int(self.sheet.cell_value(rx, coordx_index))
            coordy = int(self.sheet.cell_value(rx, coordy_index))
            origin = int(self.sheet.cell_value(rx, origin_index))
            target = int(self.sheet.cell_value(rx, target_index))
            remounting = int(self.sheet.cell_value(rx, remounting_index))
            labels = int(self.sheet.cell_value(rx, labels_index))
            #colors = self.sheet.cell_value(rx, colors_index)

            #print(rx, part, coordx, coordy, origin, target, remounting, labels)
            self.parts[part] = {
                "row_num": rx,
                "part_num": part,
                "coordx": coordx,
                "coordy": coordy,
                "origin": origin,
                "target": target,
                "remounting": remounting,
                "labels": labels
            }


    def process_parts(self, sheet):
        """ calculate parts """

        for i in self.parts:
            part = self.parts[i]
            #print(part)
            if part["origin"] != 0 and part["target"] != 0:
                self.calculate_remounting(part, sheet)


    def calculate_remounting(self, part, sheet):
        """ calculate azimut, etc. """

        origin_num = part["origin"]
        target_num = part["target"]
        origin = self.parts[origin_num]
        target = self.parts[target_num]
        #print(origin, target)

        incx = origin["coordx"] - target["coordx"]
        incy = origin["coordy"] - target["coordy"]
        incxmo = math.sqrt(math.pow(incx, 2))
        incymo = math.sqrt(math.pow(incy, 2))

        origin_point = QgsPointXY(origin["coordx"], origin["coordy"])
        target_point = QgsPointXY(target["coordx"], target["coordy"])
        disthorizontal = QgsDistanceArea().measureLine(origin_point, target_point)
        azimut = self.calculate_azimut(incx, incy, incxmo, incymo)

        #print(part["row_num"], part["part_num"], incx, incy, incxmo, incymo, disthorizontal, azimut)

        row = part["row_num"]
        sheet.write(row, self.col_indexes["incx"], incx)
        sheet.write(row, self.col_indexes["incy"], incy)
        sheet.write(row, self.col_indexes["incxmo"], incxmo)
        sheet.write(row, self.col_indexes["incymo"], incymo)
        sheet.write(row, self.col_indexes["disthorizontal"], disthorizontal)
        sheet.write(row, self.col_indexes["azimut"], azimut)


    def calculate_azimut(self, incx, incy, incxmo, incymo):
        """ calculate azimut """

        vatan = 0
        if incx != 0 and incx != 0:
            vatan = math.atan(incx / incy) * (180 / math.pi)

        vazimut = vatan

        if incx >= 0 and incy >= 0:
            vazimut = math.atan(incxmo / incymo) * (180 / math.pi)
        elif incx >= 0 and incy < 0:
            vazimut = 90 + (math.atan(incymo / incxmo) * (180 / math.pi))
        elif incx < 0 and incy < 0:
            vazimut = 180 + (math.atan(incxmo / incymo) * (180 / math.pi))
        elif incx < 0 and incy >= 0:
            vazimut = 270 + (math.atan(incymo / incxmo) * (180 / math.pi))

        return round(vazimut, 2)


    def load_excel(self):
        """ load sheets from excel """

        if self.book:
            self.parent.dlg.remounting_sheet.currentIndexChanged.disconnect(self.load_excel_sheet)

        self.parent.dlg.remounting_sheet.clear()
        self.parent.dlg.remounting_sheet.addItem(COMBO_SELECT)
        self.clear_parts()

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

        index = self.parent.dlg.remounting_sheet.currentIndex() - 1
        self.sheet = self.book.sheet_by_index(index)
        print("Sheet '{0}' has {1} rows and {2} columns".format(self.sheet.name, self.sheet.nrows, self.sheet.ncols))

        for column_index in range(self.sheet.ncols):
            name = self.sheet.cell_value(0, column_index)
            self.col_indexes[name] = column_index
            self.fill_parts(name)
        print(self.col_indexes)

        self.select_default()


    def clear_parts(self):
        """ empty column combo boxes """

        self.parent.dlg.remounting_part.clear()
        self.parent.dlg.remounting_part.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_coordx.clear()
        self.parent.dlg.remounting_coordx.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_coordy.clear()
        self.parent.dlg.remounting_coordy.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_origin.clear()
        self.parent.dlg.remounting_origin.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_target.clear()
        self.parent.dlg.remounting_target.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_remounting.clear()
        self.parent.dlg.remounting_remounting.addItem(COMBO_SELECT)
        self.parent.dlg.remounting_labels.clear()
        self.parent.dlg.remounting_labels.addItem(COMBO_SELECT)


    def fill_parts(self, name):
        """ fill column combo boxes """

        self.parent.dlg.remounting_part.addItem(name)
        self.parent.dlg.remounting_coordx.addItem(name)
        self.parent.dlg.remounting_coordy.addItem(name)
        self.parent.dlg.remounting_origin.addItem(name)
        self.parent.dlg.remounting_target.addItem(name)
        self.parent.dlg.remounting_remounting.addItem(name)
        self.parent.dlg.remounting_labels.addItem(name)


    def select_default(self):
        """ select default values for column combo boxes """

        for key in FIELDS_DEFAULT:
            widget = self.parent.dlg.tabWidgetMain.widget(2).findChild(QComboBox, key)
            widget.setCurrentText(FIELDS_DEFAULT[key])
