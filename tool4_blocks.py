from qgis.core import Qgis, QgsProject, QgsSettings, QgsExpression, QgsVectorLayer, QgsField, QgsPoint, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerProxyModel, QgsWkbTypes
from qgis.gui import QgsExpressionBuilderDialog
from qgis.PyQt.QtCore import QVariant

import os
import processing

from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_BLOCKS = ["blocks_db", "blocks_workspace"]
FIELDS_MANDATORY_PROCESS = ["blocks_dib_pieza", "blocks_polygon_layer", "blocks_lines_layer", "blocks_3d_layer"]


class BlocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}
        self.points_layer = None

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.databases = self.utils.read_database_config()
        self.fill_db()

        #self.parent.dlg.blocks_polygon_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        #print(self.parent.dlg.blocks_polygon_layer.filters())
        self.parent.dlg.blocks_filter_expr_btn.clicked.connect(self.open_expr_builder)
        self.parent.dlg.blocks_filter_expr_select_btn.clicked.connect(self.load_blocks)


    def fill_db(self):
        """ fill databases combobox """

        for database in self.databases:
            self.parent.dlg.blocks_db.addItem(self.databases[database]["name"], {"value": database})


    def connect_db(self):
        """ get blocks from database """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_BLOCKS):
            return False

        # connect to database
        db = self.databases[self.parent.dlg.blocks_db.currentData()["value"]]
        self.blocks_db_obj = utils_database(self.parent.plugin_dir, db)
        self.blocks_db = self.blocks_db_obj.open_database()


    def load_blocks(self):
        """ read blocks from db and paint points """

        self.connect_db()

        exp = QgsExpression(self.parent.dlg.blocks_filter_expr.text())

        if exp.hasParserError():
           raise Exception(exp.parserErrorString())

        if not exp.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Expression not valid: '{exp.dump()}'", level=Qgis.Warning, duration=3)
            return

        # check if expression is valid
        sql = f"SELECT * FROM view_arcmap_edit WHERE {exp.dump()}"
        rows = self.blocks_db_obj.get_rows(sql)
        if not rows or rows == None or len(rows) == 0:
            self.parent.dlg.messageBar.pushMessage(f"No registers for expression '{sql}'", level=Qgis.Warning, duration=3)
            return

        self.draw_blocks(rows)


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(self.parent.iface.activeLayer())
        if expr_dialog.exec_():
            self.parent.dlg.blocks_filter_expr.setText(expr_dialog.expressionText())


    def draw_blocks(self, rows):
        """ draw blocks from given database rows """

        blocks_layer_uri = "PointZ?crs=epsg:25831&field=cod_pieza:integer&field=num_pieza:integer&field=nom_nivel:string(10)&field=cod_tnivel:string(2)&field=dib_pieza:string(10)"
        blocks_layer = QgsVectorLayer(blocks_layer_uri, "points", "memory")

        QgsProject.instance().addMapLayer(blocks_layer)
        #group.addChildNode(QgsLayerTreeLayer(blocks_layer))

        blocks_layer.startEditing()

        for row in rows:
            fields = QgsFields()
            fields.append(QgsField("cod_pieza", QVariant.Int))
            fields.append(QgsField("num_pieza", QVariant.Int))
            fields.append(QgsField("nom_nivel", QVariant.String))
            fields.append(QgsField("cod_tnivel", QVariant.String))
            fields.append(QgsField("dib_pieza", QVariant.String))
            feature = QgsFeature(fields)

            point = QgsPoint(row[4], row[5], row[6])
            geometry = QgsGeometry.fromPoint(point)
            feature.setGeometry(geometry)
            feature.setAttributes([row[0], row[1], row[2], row[3], row[12]])
            blocks_layer.addFeature(feature)

        blocks_layer.commitChanges()
        self.parent.iface.setActiveLayer(blocks_layer)
        self.parent.iface.zoomToActiveLayer()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_points.qml")
        blocks_layer.loadNamedStyle(symbology_path)

        path = os.path.join(self.parent.dlg.blocks_workspace.filePath(), "blocks")
        self.utils.make_permanent(blocks_layer, path)

        self.points_layer = blocks_layer


    def process_blocks(self):
        """ get blocks from database """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_PROCESS):
            return False

        if not self.points_layer:
            active_layer = self.parent.iface.activeLayer()
            if active_layer and active_layer.name() == "points":
                self.points_layer = active_layer
            else:
                self.parent.dlg.messageBar.pushMessage(f"No block points available, select blocks first in order to draw a polygon.", level=Qgis.Warning, duration=3)
                return

        self.draw_polygon()
        self.draw_line()
        self.draw_polygon3d()


    def draw_polygon(self):
        """ draw polygon from convex hull """

        # apply geoprocess convex hull
        params = {
            'INPUT': self.points_layer,
            'FIELD': 'dib_pieza',
            'TYPE': 3,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }

        result = processing.run("qgis:minimumboundinggeometry", params)
        QgsProject.instance().addMapLayer(result['OUTPUT'])

        self.parent.iface.setActiveLayer(result['OUTPUT'])
        self.parent.iface.zoomToActiveLayer()

        result['OUTPUT'].setName("polygon")
        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_polygon.qml")
        result['OUTPUT'].loadNamedStyle(symbology_path)

        path = os.path.join(self.parent.dlg.blocks_workspace.filePath(), "blocks")
        self.utils.make_permanent(result['OUTPUT'], path)


    def get_points_2d(self):
        """ get all points from PointZ vector layer """

        points_2d = []
        for feature in self.points_layer.getFeatures():
            attr = feature.attributes()
            
            if attr[5] == self.parent.dlg.blocks_dib_pieza.text():
                geom = feature.geometry()
                points = [geom.asPoint()]
                for pt in points:
                    points_2d.append(QgsGeometry.fromPointXY(pt))  # Removes Z dimension

        return points_2d


    def draw_polygon_complete(self):
        """ draw polygon from given points """

        points_2d = self.get_points_2d()

        # Ensure we have enough points to form a polygon
        if len(points_2d) <= 2:
            self.parent.dlg.messageBar.pushMessage(f"Not enought points to draw a polygon.", level=Qgis.Warning, duration=3)
            return

        # create polygon layer
        polygon_layer_uri = "Polygon?crs=epsg:25831&field=dib_pieza:string(10)"
        polygon_layer = QgsVectorLayer(polygon_layer_uri, "polygon", "memory")

        QgsProject.instance().addMapLayer(polygon_layer)
        polygon_layer.startEditing()

        # Close the polygon by repeating the first point at the end
        geom = QgsGeometry.fromPolygonXY([[p.asPoint() for p in points_2d] + [points_2d[0].asPoint()]])
        feature = QgsFeature()
        feature.setGeometry(geom)
        feature.setAttributes([self.parent.dlg.blocks_dib_pieza.text()])
        polygon_layer.addFeature(feature)
        polygon_layer.commitChanges()

        self.parent.iface.setActiveLayer(polygon_layer)
        self.parent.iface.zoomToActiveLayer()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_polygon.qml")
        polygon_layer.loadNamedStyle(symbology_path)

        path = os.path.join(self.parent.dlg.blocks_workspace.filePath(), "blocks")
        self.utils.make_permanent(polygon_layer, path)


    def draw_line(self):
        """ draw line from given points """

        points_2d = self.get_points_2d()

        # Ensure we have enough points to form a points
        if len(points_2d) < 2:
            self.parent.dlg.messageBar.pushMessage(f"Not enought points to draw a line.", level=Qgis.Warning, duration=3)
            return

        # create line layer
        line_layer_uri = "LineString?crs=epsg:25831&field=dib_pieza:string(10)"
        line_layer = QgsVectorLayer(line_layer_uri, "linestring", "memory")

        QgsProject.instance().addMapLayer(line_layer)
        line_layer.startEditing()

        # not necessary to repeat the last point 
        geom = QgsGeometry.fromPolylineXY([p.asPoint() for p in points_2d])
        feature = QgsFeature()
        feature.setGeometry(geom)
        feature.setAttributes([self.parent.dlg.blocks_dib_pieza.text()])
        line_layer.addFeature(feature)
        line_layer.commitChanges()

        self.parent.iface.setActiveLayer(line_layer)
        self.parent.iface.zoomToActiveLayer()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_linestring.qml")
        line_layer.loadNamedStyle(symbology_path)

        path = os.path.join(self.parent.dlg.blocks_workspace.filePath(), "blocks")
        self.utils.make_permanent(line_layer, path)


    def draw_polygon3d(self):
        """ draw line from given points """

        points_3d = []
        for feature in self.points_layer.getFeatures():
            geom = feature.geometry()
            points = [geom.asPoint()]
            for pt in points:
                points_3d.append(pt)  # Keep X, Y, and Z

        # Ensure we have enough points to form a points
        if len(points_3d) <= 2:
            self.parent.dlg.messageBar.pushMessage(f"Not enought points to draw a line.", level=Qgis.Warning, duration=3)
            return

        # create line layer
        polygon3d_layer_uri = "PolygonZ?crs=epsg:25831&field=dib_pieza:string(10)"
        polygon3d_layer = QgsVectorLayer(polygon3d_layer_uri, "polygon3d", "memory")

        QgsProject.instance().addMapLayer(polygon3d_layer)
        polygon3d_layer.startEditing()

        # Close the polygon by repeating the first point at the end
        geom = QgsGeometry.fromPolygonXY([[p for p in points_3d] + [points_3d[0]]])
        print(geom)
        feature = QgsFeature()
        feature.setGeometry(geom)
        feature.setAttributes([self.parent.dlg.blocks_dib_pieza.text()])
        polygon3d_layer.addFeature(feature)
        polygon3d_layer.commitChanges()

        self.parent.iface.setActiveLayer(polygon3d_layer)
        self.parent.iface.zoomToActiveLayer()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_polygon3d.qml")
        polygon3d_layer.loadNamedStyle(symbology_path)

        path = os.path.join(self.parent.dlg.blocks_workspace.filePath(), "blocks")
        self.utils.make_permanent(polygon3d_layer, path)
