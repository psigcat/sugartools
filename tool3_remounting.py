from qgis.PyQt.QtWidgets import QComboBox
from qgis.core import Qgis, QgsProject, QgsPointXY, QgsDistanceArea, QgsVectorLayer, QgsFeature, QgsGeometry, QgsLayerTreeLayer, QgsFields, QgsField
from qgis.PyQt.QtCore import QVariant

import os
import xlrd
import math
import csv


from .utils import utils


SYMBOLOGY_DIR = "qml"
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
CSV_PARAMS = '?maxFields=20000&detectTypes=yes&crs=EPSG:25831&spatialIndex=no&subsetIndex=no&watchFile=no'


class RemountingTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.book = None
        self.sheet = None
        self.table = []
        self.tablekeys = None
        self.col_indexes = {}
        self.parts = {}
        self.points = {}
        self.lines = []
        self.lines_attr = []

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
        self.process_parts()
        file = self.write_csv()

        group = self.utils.create_group("Remounting")
        #self.load_csv_layer(file, group)
        self.create_point_layer(file, group)
        self.create_line_layer(file, group)


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
            colors_index = self.col_indexes[self.parent.dlg.remounting_colors.currentText()]

            part = int(self.sheet.cell_value(rx, part_index))
            coordx = int(self.sheet.cell_value(rx, coordx_index))
            coordy = int(self.sheet.cell_value(rx, coordy_index))
            origin = int(self.sheet.cell_value(rx, origin_index))
            target = int(self.sheet.cell_value(rx, target_index))
            remounting = int(self.sheet.cell_value(rx, remounting_index))
            labels = int(self.sheet.cell_value(rx, labels_index))
            color = self.sheet.cell_value(rx, colors_index)

            #print(rx, part, coordx, coordy, origin, target, remounting, labels)
            self.parts[part] = {
                "row_num": rx-1,
                "part_num": part,
                "coordx": coordx,
                "coordy": coordy,
                "origin": origin,
                "target": target,
                "remounting": remounting,
                "labels": labels,
                "color": color
            }


    def process_parts(self):
        """ calculate parts """

        for i in self.parts:
            part = self.parts[i]
            #print(part)
            if part["origin"] != 0 and part["target"] != 0:
                self.calculate_remounting(part)


    def calculate_remounting(self, part):
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

        eje = azimut
        if azimut > 180:
            eje = azimut - 180

        #distvertical = zDes - zOri  # modElements.vb line 132bis
        distvertical = 0
        distvertical = round(distvertical, 2)

        inclinacion = math.atan2(distvertical, disthorizontal)
        inclinacion = 180 * (inclinacion / math.pi)
        inclinacion = round(inclinacion, 2)
        inclinacion = abs(inclinacion)

        #print(part["row_num"], part["part_num"], incx, incy, incxmo, incymo, disthorizontal, azimut)

        row = part["row_num"]
        self.table[row]["incx"] = incx
        self.table[row]["incy"] = incy
        self.table[row]["incxmo"] = incxmo
        self.table[row]["incymo"] = incymo
        self.table[row]["disthorizontal"] = disthorizontal
        self.table[row]["azimut"] = azimut
        self.table[row]["eje"] = eje
        self.table[row]["distvertical"] = distvertical
        self.table[row]["inclinacion"] = inclinacion

        # save points for later making points layer
        self.save_points_lines(part, origin_point, target_point)


    def save_points_lines(self, part, origin_point, target_point):
        """ save points and lines """

        num_pieza = part["part_num"]
        str_pieza = "num"+str(num_pieza)
        if not str_pieza in self.points:
            self.points[str_pieza] = {
                "point": QgsPointXY(part["coordx"], part["coordy"]),
                "color": str(part["color"])
            }

        self.lines.append([origin_point, target_point])
        self.lines_attr.append({
            "origin": int(part["origin"]),
            "target": int(part["target"]),
            "color": str(part["color"])
        })


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
        """ load data from excel sheet """

        index = self.parent.dlg.remounting_sheet.currentIndex() - 1
        self.sheet = self.book.sheet_by_index(index)
        print("Sheet '{0}' has {1} rows and {2} columns".format(self.sheet.name, self.sheet.nrows, self.sheet.ncols))

        # load column indexes
        for column_index in range(self.sheet.ncols):
            name = self.sheet.cell_value(0, column_index)
            self.col_indexes[name] = column_index
            self.fill_parts(name)
        #print(self.col_indexes)

        self.select_default()

        # load all data into dict in order to save it later to csv file
        self.tablekeys = list(self.col_indexes.keys())
        for rx in range(1, self.sheet.nrows):
            row = {}
            for ry in range(self.sheet.ncols):
                col = self.tablekeys[ry]
                val = self.sheet.cell_value(rx, ry)
                type = self.sheet.cell_type(rx, ry)
                if type == 2: #number
                    val = int(val)
                row[col] = val
            self.table.append(row)
        #print(self.table)


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
        self.parent.dlg.remounting_colors.addItem(name)


    def select_default(self):
        """ select default values for column combo boxes """

        for key in FIELDS_DEFAULT:
            widget = self.parent.dlg.tabWidgetMain.widget(2).findChild(QComboBox, key)
            widget.setCurrentText(FIELDS_DEFAULT[key])


    def write_csv(self):
        """ write dict as csv file """

        # save excel
        file_path = self.parent.dlg.remounting_excel.filePath().split(".")[0]
        file = file_path + " - " + self.sheet.name + ".csv"

        with open(file, 'w', newline='') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.tablekeys)
            writer.writeheader()
            writer.writerows(self.table)

            self.parent.dlg.messageBar.pushMessage(f"Remountings done successfully, results saved to file '{file}'", level=Qgis.Success)

            return file


    # def load_csv_layer(self, file, group):
    #     """ load data from csv file as layer """

    #     file = os.path.abspath(file)
    #     uri = f"file:///{file}{CSV_PARAMS}&xField=coord_x&yField=coord_y"
    #     layer = QgsVectorLayer(uri, "points", "delimitedtext")

    #     symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "remounting_points.qml")
    #     layer.loadNamedStyle(symbology_path)
    #     #layer.triggerRepaint()

    #     QgsProject.instance().addMapLayer(layer, False)
    #     group.addChildNode(QgsLayerTreeLayer(layer))


    def create_point_layer(self, file, group):
        """ create line layer """

        layer = self.utils.create_vector_layer("points", "point", group, "&field=color:string(7)")

        layer.startEditing()
        i=0
        for str_pieza in self.points:
            fields = QgsFields()
            fields.append(QgsField("id", QVariant.Int))
            fields.append(QgsField("color", QVariant.String))
            feature = QgsFeature(fields)
            attr = self.points[str_pieza]
            num_pieza = str_pieza[3:]
            geometry = QgsGeometry.fromPointXY(attr["point"])
            feature.setGeometry(geometry)
            feature.setAttributes([num_pieza, attr["color"]])
            layer.addFeature(feature)
            i+=1
        layer.commitChanges()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "remounting_points.qml")
        layer.loadNamedStyle(symbology_path)
        #layer.triggerRepaint()

        path = file.split(".")[0] + ".gpkg"
        self.utils.make_permanent(layer, path)


    def create_line_layer(self, file, group):
        """ create point layer """

        layer = self.utils.create_vector_layer("lines", "linestring", group, "&field=color:string(7)")

        layer.startEditing()
        i=0
        for line in self.lines:
            fields = QgsFields()
            fields.append(QgsField("id", QVariant.Int))
            # fields.append(QgsField("origin", QVariant.Int))
            # fields.append(QgsField("target", QVariant.Int))
            fields.append(QgsField("color", QVariant.String))
            feature = QgsFeature(fields)
            geometry = QgsGeometry.fromPolylineXY(line)
            feature.setGeometry(geometry)
            attr = self.lines_attr[i]
            feature.setAttributes([i, attr["color"]])
            # feature.setAttributes([i, attr["origin"], attr["target"], attr["color"]])
            layer.addFeature(feature)
            i+=1
        layer.commitChanges()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "remounting_lines.qml")
        layer.loadNamedStyle(symbology_path)
        #layer.triggerRepaint()

        path = file.split(".")[0] + ".gpkg"
        self.utils.make_permanent(layer, path)
