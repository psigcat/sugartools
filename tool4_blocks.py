from qgis.core import Qgis, QgsProject, QgsSettings, QgsExpression, QgsVectorLayer, QgsPoint, QgsPointXY, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerProxyModel, QgsWkbTypes, QgsLayerTreeLayer
from qgis.gui import QgsExpressionBuilderDialog
from qgis.PyQt.QtCore import QVariant

import os
import processing
import numpy as np
from scipy.spatial import ConvexHull


from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_BLOCKS = ["blocks_db", "blocks_workspace"]
FIELDS_MANDATORY_PROCESS = ["blocks_workspace", "blocks_dib_pieza", "blocks_polygon_layer", "blocks_lines_layer", "blocks_3d_layer"]
POLYGON_LAYER_ID = "_2D"
LINE_LAYER_ID = "_lin2D"
THREED_LAYER_ID = "_3D"


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
        self.preselect_layers()

        #self.parent.dlg.blocks_polygon_layer.setFilters(QgsMapLayerProxyModel.VectorLayer)
        #print(self.parent.dlg.blocks_polygon_layer.filters())
        self.parent.dlg.blocks_filter_expr_btn.clicked.connect(self.open_expr_builder)
        self.parent.dlg.blocks_filter_expr_select_btn.clicked.connect(self.load_blocks)


    def fill_db(self):
        """ fill databases combobox """

        self.parent.dlg.blocks_db.clear()
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


    def preselect_layers(self):
        """ preselect layers """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer):
                layer_name = layer.layer().name()
                print(layer_name, POLYGON_LAYER_ID in layer_name)
                if POLYGON_LAYER_ID in layer_name:
                    polygon_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                    self.parent.dlg.blocks_polygon_layer.setLayer(polygon_layer)
                elif LINE_LAYER_ID in layer_name:
                    line_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                    self.parent.dlg.blocks_lines_layer.setLayer(line_layer)
                elif THREED_LAYER_ID in layer_name:
                    threed_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                    self.parent.dlg.blocks_3d_layer.setLayer(threed_layer)


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
        self.preselect_layers()


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

        self.utils.make_permanent(blocks_layer, self.parent.dlg.blocks_workspace.filePath())

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
            #'FIELD': 'dib_pieza',
            'TYPE': 3,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        result = processing.run("qgis:minimumboundinggeometry", params)

        layer = result['OUTPUT']

        # insert field dib_pieza as id_bloque
        layer.startEditing()
        new_field = QgsField("id_bloque", QVariant.Int)
        layer.dataProvider().addAttributes([new_field])
        layer.updateFields()

        field_index = layer.fields().indexFromName("id_bloque")
        feature = list(layer.getFeatures())[0]
        layer.changeAttributeValue(feature.id(), field_index, int(self.parent.dlg.blocks_dib_pieza.text()))
        layer.commitChanges()

        # QgsProject.instance().addMapLayer(layer)
        # self.utils.make_permanent(layer, self.parent.dlg.blocks_workspace.filePath())

        # write output to selected layer
        params = {
            'SOURCE_LAYER': layer,
            'SOURCE_FIELD': '',
            'TARGET_LAYER': self.parent.dlg.blocks_polygon_layer.currentText(),
            'TARGET_FIELD': '',
            'ACTION_ON_DUPLICATE': 0
        }
        processing.run("etl_load:appendfeaturestolayer", params)


    def draw_line(self):
        """ draw line """

        points_2d = self.get_points_2d()

        # Ensure we have enough points to form a points
        if len(points_2d) < 2:
            self.parent.dlg.messageBar.pushMessage(f"Not enought points to draw a line.", level=Qgis.Warning, duration=3)
            return

        # get minimum x and maximum x point
        min_x = 1000000000
        max_x = 0
        for p in points_2d:
            if p.asPoint().x() < min_x:
                min_x = p.asPoint().x()
                min_x_y = p.asPoint().y()
            if p.asPoint().x() > max_x:
                max_x = p.asPoint().x()
                max_x_y = p.asPoint().y()

        min_point = QgsPointXY(min_x, min_x_y)
        max_point = QgsPointXY(max_x, max_x_y)

        # create line layer
        line_layer_uri = "MultiLineString?crs=epsg:25831&field=id_bloque:integer"
        line_layer = QgsVectorLayer(line_layer_uri, "linestring", "memory")

        #QgsProject.instance().addMapLayer(line_layer)
        line_layer.startEditing()

        # draw line from minimum x to maximum x point
        geom = QgsGeometry.fromPolylineXY([min_point, max_point])
        feature = QgsFeature()
        feature.setGeometry(geom)
        feature.setAttributes([int(self.parent.dlg.blocks_dib_pieza.text())])
        line_layer.addFeature(feature)
        line_layer.commitChanges()

        # self.parent.iface.setActiveLayer(line_layer)
        # self.parent.iface.zoomToActiveLayer()

        # symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks_linestring.qml")
        # line_layer.loadNamedStyle(symbology_path)

        #self.utils.make_permanent(line_layer, self.parent.dlg.blocks_workspace.filePath())

        # write output to selected layer
        params = {
            'SOURCE_LAYER': line_layer,
            'SOURCE_FIELD': '',
            'TARGET_LAYER': self.parent.dlg.blocks_lines_layer.currentText(),
            'TARGET_FIELD': '',
            'ACTION_ON_DUPLICATE': 0
        }
        processing.run("etl_load:appendfeaturestolayer", params)

        QgsProject.instance().removeMapLayer(line_layer)


    def draw_polygon3d(self):
        """ draw 3d convex hull """

        layer = self.points_layer

        if not layer or layer.wkbType() not in [QgsWkbTypes.PointZ, QgsWkbTypes.MultiPointZ]:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a PointZ or MultiPointZ layer.: '{layer.name()}'", level=Qgis.Warning, duration=3)
            return

        points = []

        for feature in layer.getFeatures():
            geom = feature.geometry()
            
            # Extract Z values properly
            if geom.isMultipart():
                for pt in geom.asMultiPoint():
                    if isinstance(pt, QgsPoint) and pt.is3D():
                        points.append((pt.x(), pt.y(), pt.z()))
            else:
                pt = geom.constGet()
                points.append((pt.x(), pt.y(), pt.z()))

        if not points or len(points) < 4:
            self.parent.dlg.messageBar.pushMessage("A 3D convex hull requires at least 4 unique points.", level=Qgis.Warning, duration=3)
            return

        # Convert list to NumPy array for SciPy processing
        points_array = np.array(points)

        # Compute 3D convex hull
        hull = ConvexHull(points_array)

        # Create new PolygonZ layer
        crs = layer.crs().authid()
        hull_layer = QgsVectorLayer("PolygonZ?crs=" + crs + "&field=id_bloque:integer", "3D Convex Hull", "memory")
        provider = hull_layer.dataProvider()

        merged_polygons = []  # Store all faces to merge later

        # Create polygon faces from convex hull simplices
        for simplex in hull.simplices:
            hull_points = [f"{points_array[i, 0]} {points_array[i, 1]} {points_array[i, 2]}" for i in simplex]
            
            # Convert to WKT (Well-Known Text) format to keep Z values
            wkt_polygon = f"POLYGONZ(({', '.join(hull_points)}, {hull_points[0]}))"  # Close the ring
            
            merged_polygons.append(wkt_polygon)  # Collect for merging

        # Merge all polygons into a single geometry
        merged_wkt = f"MULTIPOLYGONZ({', '.join(merged_polygons)})"
        merged_geom = QgsGeometry.fromWkt(merged_wkt)

        # Add the merged feature to the new layer
        feature = QgsFeature()
        feature.setGeometry(merged_geom)
        feature.setAttributes([int(self.parent.dlg.blocks_dib_pieza.text())])
        provider.addFeature(feature)
        hull_layer.updateExtents()

        #QgsProject.instance().addMapLayer(hull_layer)
        #self.utils.make_permanent(hull_layer, self.parent.dlg.blocks_workspace.filePath())

        # fix geometries
        params = {
            'INPUT': hull_layer,
            'METHOD': 1,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }
        result = processing.run("native:fixgeometries", params)

        # write output to selected layer
        params = {
            'SOURCE_LAYER': result['OUTPUT'],
            'SOURCE_FIELD': '',
            'TARGET_LAYER': self.parent.dlg.blocks_3d_layer.currentText(),
            'TARGET_FIELD': '',
            'ACTION_ON_DUPLICATE': 0
        }
        processing.run("etl_load:appendfeaturestolayer", params)

        QgsProject.instance().removeMapLayer(hull_layer)


    def get_points_2d(self):
        """ get all points from PointZ vector layer """

        points_2d = []
        for feature in self.points_layer.getFeatures():
            attr = feature.attributes()
            
            #if attr[5] == self.parent.dlg.blocks_dib_pieza.text():
            geom = feature.geometry()
            points = [geom.asPoint()]
            for pt in points:
                points_2d.append(QgsGeometry.fromPointXY(pt))  # Removes Z dimension

        return points_2d
