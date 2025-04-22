from qgis.core import Qgis, QgsProject, QgsSettings, QgsExpression, QgsVectorLayer, QgsPoint, QgsPointXY, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerProxyModel, QgsWkbTypes, QgsLayerTreeLayer, QgsGeometryValidator, QgsProviderRegistry
from qgis.gui import QgsExpressionBuilderDialog
from qgis.PyQt.QtCore import QVariant

import os
import processing
import numpy as np
from scipy.spatial import ConvexHull
import sqlite3
import math


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
                layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                if POLYGON_LAYER_ID in layer_name:
                    self.parent.dlg.blocks_polygon_layer.setLayer(layer)
                elif LINE_LAYER_ID in layer_name:
                    self.parent.dlg.blocks_lines_layer.setLayer(layer)
                elif THREED_LAYER_ID in layer_name:
                    self.parent.dlg.blocks_3d_layer.setLayer(layer)


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

        self.parent.dlg.messageBar.pushMessage(f"Blocks selected", level=Qgis.Success)


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(self.parent.iface.activeLayer())
        if expr_dialog.exec_():
            self.parent.dlg.blocks_filter_expr.setText(expr_dialog.expressionText())


    def draw_blocks(self, rows):
        """ draw blocks from given database rows """

        layer_name = "points"

        # remove previously imported points layer if exists
        points_layer = self.utils.get_layer_from_tree(layer_name)
        if points_layer:
            QgsProject.instance().removeMapLayer(points_layer)
        
        blocks_layer_uri = "PointZ?crs=epsg:25831&field=cod_pieza:integer&field=num_pieza:integer&field=nom_nivel:string(10)&field=cod_tnivel:string(2)&field=dib_pieza:string(10)"
        blocks_layer = QgsVectorLayer(blocks_layer_uri, layer_name, "memory")

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

            if not active_layer or active_layer.name() != "points":
                self.parent.dlg.messageBar.pushMessage(f"No block points available, select blocks first in order to draw a polygon.", level=Qgis.Critical, duration=3)
                return

            self.points_layer = active_layer

        if self.points_layer.wkbType() not in [QgsWkbTypes.PointZ, QgsWkbTypes.MultiPointZ]:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a PointZ or MultiPointZ layer.", level=Qgis.Critical, duration=3)
            return

        convex_hull = self.draw_polygon()
        self.draw_line(convex_hull)
        self.draw_polygon3d()

        self.parent.dlg.messageBar.pushMessage(f"Polygons, lines and polygons3d written to selected layers", level=Qgis.Success)


    def draw_polygon(self):
        """ draw polygon from convex hull """

        polygon_layer_name = self.parent.dlg.blocks_polygon_layer.currentText()
        polygon_layer = QgsProject.instance().mapLayersByName(polygon_layer_name)[0]

        if not polygon_layer or polygon_layer.wkbType() != QgsWkbTypes.MultiPolygon:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiPolygon layer.", level=Qgis.Critical, duration=3)
            return

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

        return layer


    def draw_line(self, convex_hull):
        """ draw line """

        line_layer_name = self.parent.dlg.blocks_lines_layer.currentText()
        line_layer = QgsProject.instance().mapLayersByName(line_layer_name)[0]

        if not line_layer or line_layer.wkbType() != QgsWkbTypes.MultiLineString:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiLineString layer.", level=Qgis.Critical, duration=3)
            return

        top_points = self.get_points_top_3d()
        line_features = self.get_points_random_3d(convex_hull, top_points)

        if not top_points:
            return

        # create line layer
        line_layer_uri = "MultiLineString?crs=epsg:25831&field=id_bloque:integer"
        line_layer = QgsVectorLayer(line_layer_uri, "linestring", "memory")

        line_layer.startEditing()

        # Create a line connecting the 3 highest Z points
        feature = QgsFeature()
        geom = QgsGeometry.fromPolyline([top_points[1], top_points[0], top_points[2]])
        feature.setGeometry(geom)
        feature.setAttributes([int(self.parent.dlg.blocks_dib_pieza.text())])
        line_layer.addFeature(feature)

        # Add lines from each of this points to closest points on convex hull
        for line_feature in line_features:
            line_layer.addFeature(line_feature)

        line_layer.commitChanges()
        
        # Add the new layer to the project
        #QgsProject.instance().addMapLayer(line_layer)

        # write output to selected layer
        params = {
            'SOURCE_LAYER': line_layer,
            'SOURCE_FIELD': '',
            'TARGET_LAYER': self.parent.dlg.blocks_lines_layer.currentText(),
            'TARGET_FIELD': '',
            'ACTION_ON_DUPLICATE': 0
        }
        processing.run("etl_load:appendfeaturestolayer", params)

        #QgsProject.instance().removeMapLayer(line_layer)


    def get_points_top_3d(self):
        """ get 3 points with highest Z values """

        # Extract features and sort by Z value
        features = [f for f in self.points_layer.getFeatures()]

        # Sort features by Z values in descending order
        features.sort(key=lambda f: f.geometry().constGet().z(), reverse=True)

        # Get the top 3 points with Z values
        top_points = [f.geometry().vertexAt(0) for f in features[:3]]

        if len(top_points) < 3:
            self.parent.dlg.messageBar.pushMessage(f"Not enough points in the layer, minimum 3.", level=Qgis.Critical, duration=3)
            return None

        return top_points


    def get_points_random_3d(self, convex_hull, top_points):
        """ get 3 points from convex hull closest to top_points and make line """

        hull_features = [f.geometry() for f in convex_hull.getFeatures()]

        # Extract convex hull points
        convex_hull_points = []
        for geom in hull_features:
              # Extract outer ring
            if geom.isMultipart():
                convex_hull_points.extend(geom.asMultiPolygon()[0][0])
            else:
                convex_hull_points.extend(geom.asPolygon()[0])

        # Convert convex hull points to QgsPoint to match Z-enabled points
        convex_hull_points = [QgsPoint(hp.x(), hp.y(), 0) for hp in convex_hull_points]

        # Compute convex hull centroid
        sum_x = sum(p.x() for p in convex_hull_points)
        sum_y = sum(p.y() for p in convex_hull_points)
        centroid = QgsPoint(sum_x / len(convex_hull_points), sum_y / len(convex_hull_points), 0)

        # Function to compute angle from centroid
        def compute_angle(p):
            return math.degrees(math.atan2(p.y() - centroid.y(), p.x() - centroid.x())) % 360
        
        # Assign hull points to 3 angle groups (0-120, 120-240, 240-360)
        hull_sections = {0: [], 1: [], 2: []}
        for p in convex_hull_points:
            angle = compute_angle(p)
            section = int(angle // 120)  # Determine which third it belongs to
            hull_sections[section].append(p)

        if not all(hull_sections.values()):
            print("Not enough convex hull points in each section!")
            return None

        used_sections = set()
        line_features = []
        for idx, p in enumerate(top_points):
            # Select a section not already used
            available_sections = [s for s in [0, 1, 2] if s not in used_sections]
            if not available_sections:
                self.parent.dlg.messageBar.pushMessage(f"Not enough distinct hull sections!", level=Qgis.Critical, duration=3)
                break

            # Choose the closest hull point from an available section
            best_section = min(available_sections, key=lambda s: min(p.distance(hp) for hp in hull_sections[s]))
            closest_hull_point = min(hull_sections[best_section], key=lambda hp: p.distance(hp))
            used_sections.add(best_section)  # Mark this section as used

            # avoid making line between two identical points
            if p.x() != closest_hull_point.x() and p.y() != closest_hull_point.y():

                # Create a line feature
                line_feature = QgsFeature()
                line_feature.setGeometry(QgsGeometry.fromPolyline([p, closest_hull_point]))
                line_feature.setAttributes([int(self.parent.dlg.blocks_dib_pieza.text())])
                line_features.append(line_feature)

        return line_features


    def draw_polygon3d(self):
        """ draw 3d convex hull """

        threed_layer_name = self.parent.dlg.blocks_3d_layer.currentText()
        threed_layer = QgsProject.instance().mapLayersByName(threed_layer_name)[0]

        if not threed_layer or threed_layer.wkbType() != QgsWkbTypes.MultiPolygonZ:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiPolygonZ layer.", level=Qgis.Critical, duration=3)
            return

        points = self.get_points_3d()

        if not points or len(points) < 4:
            self.parent.dlg.messageBar.pushMessage("A 3D convex hull requires at least 4 unique points.", level=Qgis.Warning, duration=3)
            return

        # Convert list to NumPy array for SciPy processing
        points_array = np.array(points)

        # Compute 3D convex hull
        hull = ConvexHull(points_array)

        # Create new PolygonZ layer
        crs = self.points_layer.crs().authid()
        hull_layer = QgsVectorLayer("MultiPolygonZ?crs=" + crs + "&field=id_bloque:integer&field=fid:integer", "3D Convex Hull", "memory")
        provider = hull_layer.dataProvider()

        hull_faces = []  # Store triangular faces

        # Iterate through hull simplices (triangular faces)
        for simplex in hull.simplices:
            hull_points = [f"{points_array[i, 0]} {points_array[i, 1]} {points_array[i, 2]}" for i in simplex]

            # Convert to WKT (Well-Known Text) for 3D surface representation
            wkt_triangle = f"POLYGONZ(({', '.join(hull_points)}, {hull_points[0]}))"  # Close the ring

            hull_faces.append(wkt_triangle)

        # Create a MultiPolygonZ to hold all faces
        merged_wkt = f"MULTIPOLYGONZ({', '.join(hull_faces)})"
        merged_geom = QgsGeometry.fromWkt(merged_wkt)

        if not merged_geom or merged_geom.isEmpty():
            print("Merged geometry is empty!")

        # validator = QgsGeometryValidator(merged_geom)
        # errors = validator.validateGeometry(merged_geom)

        # if errors:
        #     print("Geometry errors found:")
        #     for error in errors:
        #         print(error.what())

        # if merged_geom and not merged_geom.isEmpty() and merged_geom.isGeosValid():
        #     fixed_geom = merged_geom
        # else:
        #     print("Geometry is empty or invalid, attempting to fix...")
        #     fixed_geom = merged_geom.makeValid()
        #     if not fixed_geom or not fixed_geom.isGeosValid():
        #         print("Failed to fix the geometry.")
        #         return

        # Add the merged feature to the new layer
        feature = QgsFeature()

        # Ensure the geometry is not empty before adding
        if merged_geom and not merged_geom.isEmpty():
            # Check the validity of the geometry
            if not merged_geom.isGeosValid():
                print("Invalid geometry detected. Forcing valid MultiPolygonZ...")

                # Reconstruct as MultiPolygonZ without losing Z values
                merged_geom = QgsGeometry.fromWkt(merged_geom.asWkt())  # Force re-parsing

                # Optional: Convert it explicitly to MultiPolygonZ
                if merged_geom.isMultipart():
                    merged_geom.convertToMultiType()

            # Double-check that the geometry is still MultiPolygonZ
            if merged_geom.wkbType() == QgsWkbTypes.MultiPolygonZ:
                print("Geometry is now valid MultiPolygonZ, adding to layer...")
                feature.setGeometry(merged_geom)
                feature.setAttributes([
                    int(self.parent.dlg.blocks_dib_pieza.text()),
                    len(list(threed_layer.getFeatures())) + 1
                ])
                hull_layer.startEditing()
                hull_layer.addFeature(feature)
                hull_layer.commitChanges()
            else:
                print("Failed to ensure MultiPolygonZ format, skipping feature.")

        else:
            print("Merged geometry is empty, skipping.")
            return

        #QgsProject.instance().addMapLayer(hull_layer)

        result = processing.run("native:mergevectorlayers", {
            'LAYERS': [hull_layer, threed_layer],
            'OUTPUT': 'TEMPORARY_OUTPUT'
            #'INVALID_FEATURES': 'IGNORE'
        })

        merged_layer = result['OUTPUT']
        merged_layer.setName(self.parent.dlg.blocks_3d_layer.currentText())

        #QgsProject.instance().addMapLayer(result['OUTPUT'])

        # delete fields
        fid_field = merged_layer.fields().indexFromName('fid')
        layer_field = merged_layer.fields().indexFromName('layer')
        path_field = merged_layer.fields().indexFromName('path')
        merged_layer.startEditing()
        merged_layer.dataProvider().deleteAttributes([fid_field, layer_field, path_field])
        merged_layer.commitChanges()
        merged_layer.updateFields()

        threed_layer_path = QgsProviderRegistry.instance().decodeUri(threed_layer.dataProvider().name(), threed_layer.publicSource())['path']
        layer_name = self.parent.dlg.blocks_3d_layer.currentText()

        # temporary remove 3d layer before loading new one with additional feature again
        QgsProject.instance().removeMapLayer(threed_layer)

        #Save the new layer to the GeoPackage (mandatory has to be a separate gpkg file with only that layer with a Multipolygon3D geometry)
        params = {
            'INPUT': merged_layer,
            #'LAYER_NAME': layer_name,
            'OUTPUT': threed_layer_path,
            'ACTION_ON_EXISTING_FILE': 0
        }
        processing.run("native:savefeatures", params)

        new_layer = QgsVectorLayer(threed_layer_path, layer_name, "ogr")
        QgsProject.instance().addMapLayer(new_layer)

        #threed_layer.dataProvider().setDataSourceUri(threed_layer_path)
        #threed_layer.dataProvider().reloadData()
        #threed_layer.triggerRepaint()
        #threed_layer.reload()

        #self.refresh_datasources(new_layer_path)


        # unsuccessfull test in order to write merged layer in existing multilayer gpkg

        #Delete existing layer using GDAL's ogr2ogr (not necessary because overwriting file)
        # try:
        #     conn = sqlite3.connect(threed_layer_path)
        #     cursor = conn.cursor()
        #     cursor.execute(f"DROP TABLE IF EXISTS \"{layer_name}\"") 
        #     cursor.execute(f"DELETE FROM gpkg_contents WHERE table_name = \"{layer_name}\"")
        #     cursor.execute(f"DELETE FROM gpkg_geometry_columns WHERE table_name = \"{layer_name}\"")
        #     conn.commit()
        #     conn.close()
        #     print(f"Deleted existing layer: {layer_name}")
        # except Exception as e:
        #     print(f"Error deleting existing layer: {e}")

        # saved_layer = QgsVectorLayer(threed_layer_path + f"|layername={layer_name}", layer_name, "ogr")

        #Save the new layer to the GeoPackage
        # params = {'INPUT': saved_layer,
        #           'OUTPUT': f"{threed_layer_path}|layername={layer_name}",
        #           #'OUTPUT': threed_layer_path,
        #           #'LAYER_NAME': layer_name,
        #           'ACTION_ON_EXISTING_FILE':1
        # }
        # processing.run("native:savefeatures", params)

        # params = {'INPUT': merged_layer,
        #           'OPTIONS': '-update -nln ' + layer_name,
        #           'OUTPUT': threed_layer_path,
        #           'DRIVER_NAME': 'GPKG'
        # }
        # processing.run("gdal:convertformat", params)

        # write output to selected layer
        # params = {
        #     'SOURCE_LAYER': merged_layer,
        #     'TARGET_LAYER': threed_layer_path,
        #     'ACTION_ON_DUPLICATE': 0,
        #     'INVALID_FEATURES': 'IGNORE'
        # }
        # processing.run("etl_load:appendfeaturestolayer", params)

        #QgsProject.instance().removeMapLayer(hull_layer)


    # def refresh_datasources(self, file_path):
    #     """ refresh data sources of loaded layers """

    #     #self.refresh_datasource(file_path, self.parent.dlg.blocks_polygon_layer.currentText())
    #     #self.refresh_datasource(file_path, self.parent.dlg.blocks_lines_layer.currentText())
    #     self.refresh_datasource(file_path, self.parent.dlg.blocks_3d_layer.currentText())


    # def refresh_datasource(self, file_path, layer_name):
    #     """ refresh data sources of loaded layers """

    #     print(layer_name, file_path)
    #     refresh_layer = QgsProject.instance().mapLayersByName(layer_name)[0]
    #     print(refresh_layer)

    #     refresh_layer.dataProvider().setDataSourceUri(file_path)
    #     refresh_layer.dataProvider().reloadData()
    #     refresh_layer.triggerRepaint()
    #     refresh_layer.reload()

    #     self.parent.iface.mapCanvas().refresh()


    def get_points_3d(self):
        """ get all points from PointZ vector layer """

        points = []
        for feature in self.points_layer.getFeatures():
            geom = feature.geometry()
            
            # Extract Z values properly
            if geom.isMultipart():
                for pt in geom.asMultiPoint():
                    if isinstance(pt, QgsPoint) and pt.is3D():
                        points.append((pt.x(), pt.y(), pt.z()))
            else:
                pt = geom.constGet()
                points.append((pt.x(), pt.y(), pt.z()))

        return points


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
