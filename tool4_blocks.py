from qgis.core import Qgis, QgsProject, QgsSettings, QgsExpression, QgsVectorLayer, QgsPoint, QgsPointXY, QgsFeature, QgsGeometry, QgsFields, QgsField, QgsMapLayerProxyModel, QgsWkbTypes, QgsLayerTreeLayer, QgsGeometryValidator, QgsProviderRegistry
from qgis.gui import QgsExpressionBuilderDialog
from qgis.PyQt.QtCore import QVariant

import os
import processing
import numpy as np
from scipy.spatial import ConvexHull
import sqlite3
import math
import sip


from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_BLOCKS = ["blocks_db", "blocks_workspace"]
FIELDS_MANDATORY_PROCESS = ["blocks_workspace", "blocks_dib_pieza", "blocks_polygon_layer", "blocks_lines_layer", "blocks_3d_layer"]
POLYGON_LAYER_ID = "_2d"
LINE_LAYER_ID = "_lin2d"
THREED_LAYER_ID = "_3d"


class BlocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}
        self.points_layer = None

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.parent.dlg.blocks_polygon_layer.setAllowEmptyLayer(True, "None")
        self.parent.dlg.blocks_lines_layer.setAllowEmptyLayer(True, "None")
        self.parent.dlg.blocks_3d_layer.setAllowEmptyLayer(True, "None")

        self.parent.dlg.blocks_draw_box.setEnabled(False)
        self.databases = self.utils.read_database_config()
        self.utils.fill_db_combo(self.parent.dlg.blocks_db, self.databases)
        self.preselect_layers()

        self.parent.dlg.blocks_filter_expr_btn.clicked.connect(self.open_expr_builder)
        self.parent.dlg.blocks_filter_expr_select_btn.clicked.connect(self.load_blocks)


    def reset_ui(self):
        """ reset UI """

        self.parent.dlg.blocks_filter_expr.setText(r""""dib_pieza" = '102'""")
        self.parent.dlg.blocks_dib_pieza.setText("")


    def connect_db(self):
        """ get blocks from database """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_BLOCKS):
            return False

        if not self.parent.dlg.blocks_db.currentData()["value"]:
            self.parent.dlg.messageBar.pushMessage("Please select a database connection", level=Qgis.Warning, duration=3)
            return False

        # connect to database
        db = self.databases[self.parent.dlg.blocks_db.currentData()["value"]]
        self.blocks_db_obj = utils_database(self.parent.plugin_dir, db)
        self.blocks_db = self.blocks_db_obj.open_database()

        return True


    def preselect_layers(self):
        """ preselect layers """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer):
                layer_name = layer.layer().name()
                layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                if POLYGON_LAYER_ID.lower() in layer_name.lower():
                    self.parent.dlg.blocks_polygon_layer.setLayer(layer)
                elif LINE_LAYER_ID.lower() in layer_name.lower():
                    self.parent.dlg.blocks_lines_layer.setLayer(layer)
                elif THREED_LAYER_ID.lower() in layer_name.lower():
                    self.parent.dlg.blocks_3d_layer.setLayer(layer)


    def load_blocks(self):
        """ read blocks from db and paint points """

        if not self.connect_db() or self.connect_db() == None:
            self.parent.dlg.messageBar.pushMessage(f"No valid database connection!", level=Qgis.Warning, duration=3)
            return

        if not os.path.exists(self.parent.dlg.blocks_workspace.filePath()):
            self.parent.dlg.messageBar.pushMessage(f"No valid workspace path '{self.parent.dlg.blocks_workspace.filePath()}'", level=Qgis.Warning, duration=3)
            return

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
            self.parent.dlg.messageBar.pushMessage(f"No registers for expression '{sql}'", level=Qgis.Warning)
            return

        dib_pieza = self.parent.dlg.blocks_filter_expr.text()
        dib_pieza = dib_pieza.replace(r""""dib_pieza" = """, "")
        dib_pieza = dib_pieza.replace("'", "").replace('"', "").strip()
        self.parent.dlg.blocks_dib_pieza.setText(dib_pieza)

        self.draw_blocks(dib_pieza, rows)
        self.parent.dlg.blocks_draw_box.setEnabled(True)
        self.preselect_layers()

        self.parent.dlg.messageBar.pushMessage(f"Blocks selected", level=Qgis.Success)


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(self.parent.iface.activeLayer())
        if expr_dialog.exec():
            self.parent.dlg.blocks_filter_expr.setText(expr_dialog.expressionText())


    def draw_blocks(self, dib_pieza, rows):
        """ draw blocks from given database rows """

        layer_name = dib_pieza
        
        blocks_layer_uri = "PointZ?crs=epsg:25831&field=cod_pieza:integer&field=num_pieza:integer&field=nom_nivel:string(10)&field=cod_tnivel:string(2)&field=dib_pieza:string(10)"
        blocks_layer = QgsVectorLayer(blocks_layer_uri, layer_name, "memory")
        QgsProject.instance().addMapLayer(blocks_layer)

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

        self.utils.save_layer_gpkg(blocks_layer, os.path.join(self.parent.dlg.blocks_workspace.filePath(), "helper"))

        self.points_layer = blocks_layer


    def process_blocks(self):
        """ get blocks from database """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_PROCESS):
            return False

        if sip.isdeleted(self.points_layer):
            self.parent.dlg.messageBar.pushMessage(f"No block points available, load blocks first (or select points layer with name <dib_pieza> if available) in order to draw a polygon.", level=Qgis.Critical, duration=10)
            return

        if self.points_layer is None:
            active_layer = self.parent.iface.activeLayer()

            if not active_layer or active_layer.name() != self.parent.dlg.blocks_dib_pieza.text():
                self.parent.dlg.messageBar.pushMessage(f"No block points available, select blocks first in order to draw a polygon.", level=Qgis.Critical, duration=3)
                return

            self.points_layer = active_layer

        if self.points_layer.wkbType() not in [QgsWkbTypes.Type.PointZ, QgsWkbTypes.Type.MultiPointZ]:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a PointZ or MultiPointZ layer.", level=Qgis.Critical, duration=3)
            return

        convex_hull = self.get_convex_hull()
        self.draw_polygon(convex_hull)
        self.draw_line(convex_hull)
        
        if not self.draw_polygon3d():
            self.parent.dlg.messageBar.pushMessage(f"Polygons and lines written to selected layers, but not polygons3d", level=Qgis.Success)
            return

        self.parent.dlg.messageBar.pushMessage(f"Polygons, lines and polygons3d written to selected layers", level=Qgis.Success)

        # reset for next round of loading points and drawing forms
        self.parent.dlg.blocks_draw_box.setEnabled(False)

        # remove previously imported points layer if exists
        QgsProject.instance().removeMapLayer(self.points_layer)


    def get_convex_hull(self):
        """ get convex hull from points layer """

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
        new_field = QgsField("id_bloque", QVariant.String)
        layer.dataProvider().addAttributes([new_field])
        layer.updateFields()

        field_index_id = layer.fields().indexFromName("id_bloque")
        feature = list(layer.getFeatures())[0]
        layer.changeAttributeValue(feature.id(), field_index_id, self.parent.dlg.blocks_dib_pieza.text())
        
        field_index_area = layer.fields().indexFromName("area")
        if field_index_area != -1:
            layer.renameAttribute(field_index_area, 'SHAPE_Area')

        field_index_permiter = layer.fields().indexFromName("perimeter")
        if field_index_permiter != -1:
            layer.renameAttribute(field_index_permiter, 'SHAPE_Length')
        
        layer.commitChanges()

        return layer


    def draw_polygon(self, convex_hull):
        """ draw polygon from convex hull """

        polygon_layer = self.parent.dlg.blocks_polygon_layer.currentLayer()
        if polygon_layer is None:
            return

        # save layer before processing
        if polygon_layer.isEditable():
            polygon_layer.commitChanges()
            #polygon_layer.rollBack()

        if not polygon_layer or polygon_layer.wkbType() != QgsWkbTypes.Type.MultiPolygon:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiPolygon layer.", level=Qgis.Critical, duration=3)
            return

        write_layer = convex_hull

        # smooth polygon
        if self.parent.dlg.blocks_smooth_polygons.isChecked():
            params = {
                'INPUT': layer,
                'ITERATIONS': 1,
                'OFFSET': 0.25,
                'MAX_ANGLE': 180,
                'OUTPUT': 'TEMPORARY_OUTPUT'
            }
            result = processing.run("native:smoothgeometry", params)
            write_layer = result['OUTPUT']

        # write output to selected layer
        params = {
            #'SOURCE_LAYER': layer,
            'SOURCE_LAYER': write_layer,
            'SOURCE_FIELD': '',
            'TARGET_LAYER': self.parent.dlg.blocks_polygon_layer.currentText(),
            'TARGET_FIELD': '',
            'ACTION_ON_DUPLICATE': 0
        }
        processing.run("etl_load:appendfeaturestolayer", params)


    def draw_line(self, convex_hull):
        """ draw line """

        line_layer = self.parent.dlg.blocks_lines_layer.currentLayer()
        if line_layer is None:
            return

        # save layer before processing
        if line_layer.isEditable():
            line_layer.commitChanges()
            #line_layer.rollBack()

        if not line_layer or line_layer.wkbType() != QgsWkbTypes.Type.MultiLineString:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiLineString layer.", level=Qgis.Critical, duration=3)
            return

        top_points = self.get_points_top_3d()
        line_features = self.get_points_random_3d(convex_hull, top_points)

        if not top_points:
            return

        # create line layer
        line_layer_uri = "MultiLineString?crs=epsg:25831&field=id_bloque:string(10)"
        line_layer = QgsVectorLayer(line_layer_uri, "linestring", "memory")

        line_layer.startEditing()

        # Create a line connecting the 3 highest Z points
        feature = QgsFeature()
        geom = QgsGeometry.fromPolyline([top_points[1], top_points[0], top_points[2]])
        feature.setGeometry(geom)
        feature.setAttributes([self.parent.dlg.blocks_dib_pieza.text()])

        # field_index_permiter = line_layer.fields().indexFromName("perimeter")
        # if field_index_permiter != -1:
        #     line_layer.renameAttribute(field_index_permiter, 'SHAPE_Length')
        
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
                line_feature.setAttributes([self.parent.dlg.blocks_dib_pieza.text()])
                line_features.append(line_feature)

        return line_features


    def draw_polygon3d(self):
        """ draw 3d convex hull and append directly to the target layer provider """

        threed_layer = self.parent.dlg.blocks_3d_layer.currentLayer()
        if threed_layer is None:
            return

        if not threed_layer or threed_layer.wkbType() != QgsWkbTypes.Type.MultiPolygonZ:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiPolygonZ layer.", level=Qgis.Critical, duration=3)
            return False

        # Layer validation checks are the same
        if threed_layer.wkbType() != QgsWkbTypes.Type.MultiPolygonZ:
            self.parent.dlg.messageBar.pushMessage(f"The active layer is not a MultiPolygonZ layer.", level=Qgis.Critical, duration=3)
            return False

        points = self.get_points_3d()

        if not points or len(points) < 4:
            self.parent.dlg.messageBar.pushMessage(f"A 3D convex hull requires at least 4 unique points.", level=Qgis.Critical, duration=3)
            return False

        points_array = np.array(points)
        hull = ConvexHull(points_array)

        # GeometryCollection Z WKT construction
        polygon_components = [] # List to hold the WKT for each component: '((ring))'

        # Iterate through hull simplices (triangular faces)
        for simplex in hull.simplices:
            ring_points_wkt = []
            for i in simplex:
                x, y, z = points_array[i]
                ring_points_wkt.append(f"{x} {y} {z}") 

            # Close the ring
            ring_points_wkt.append(ring_points_wkt[0])

            # Component format for MultiPolygon Z is ((ring))
            component_wkt = f"(({', '.join(ring_points_wkt)}))"
            polygon_components.append(component_wkt)

        # 3. Combine components into the final WKT
        # WKT format: MULTIPOLYGON Z (((r1)), ((r2)), ...)
        merged_wkt = f"MULTIPOLYGON Z ({', '.join(polygon_components)})"

        # Parse the final WKT string
        merged_geom = QgsGeometry.fromWkt(merged_wkt)

        if not merged_geom or merged_geom.isEmpty():
            self.parent.dlg.messageBar.pushMessage(f"CRITICAL ERROR: Failed to parse GEOMETRYCOLLECTION Z WKT.", level=Qgis.Critical, duration=3)
            return False

        # Append to Target Layer Provider
        provider = threed_layer.dataProvider()
        new_feature = QgsFeature(threed_layer.fields())
        new_feature.setGeometry(merged_geom) 
        dib_pieza = self.parent.dlg.blocks_dib_pieza.text()

        # Find the field indices based on the target layer's field names
        fid_field_idx = threed_layer.fields().indexFromName('fid')
        id_bloque_field_idx = threed_layer.fields().indexFromName('id_bloque')

        # Ensure attributes are set correctly for the target layer's schema
        if fid_field_idx != -1:
             all_fids = list(provider.allFeatureIds())
             max_fid = max(all_fids) if all_fids else 0
             new_feature[fid_field_idx] = max_fid + 1
        if id_bloque_field_idx != -1:
             new_feature[id_bloque_field_idx] = dib_pieza

        threed_layer.startEditing()
        success = provider.addFeatures([new_feature])

        if success:
            threed_layer.commitChanges()
            self.parent.dlg.messageBar.pushMessage(f"SUCCESS: Feature successfully appended to GeoPackage layer '{threed_layer.name()}' via data provider.", level=Qgis.Success, duration=3)
            threed_layer.triggerRepaint()
            return True
        else:
            threed_layer.rollBack()
            self.parent.dlg.messageBar.pushMessage(f"FAILURE: Provider failed to add feature. The GeoPackage rejected the geometry during the edit commit.", level=Qgis.Critical, duration=3)
            return False


    def all_points_valid(self):
        """ check if all points have valid dib_pieza """

        for feature in self.points_layer.getFeatures():
            attr = feature.attributes()

            if attr[4] != self.parent.dlg.blocks_dib_pieza.text():
                return False

        return True


    def get_points_3d(self):
        """ get all points from PointZ vector layer """

        points = []
        # Define the acceptable WKB types for points
        point_types = [QgsWkbTypes.Type.Point, QgsWkbTypes.Type.PointZ, QgsWkbTypes.Type.MultiPoint, QgsWkbTypes.Type.MultiPointZ]

        for feature in self.points_layer.getFeatures():
            geom = feature.geometry()
            wkb_type = geom.wkbType()
            
            # 1. Skip the feature if it's not a point or multipoint type
            if wkb_type not in point_types:
                # print(f"Skipping non-point geometry type: {QgsWkbTypes.displayString(wkb_type)}")
                continue

            # 2. Handle MultiPoint/MultiPointZ features
            if geom.isMultipart():
                # Safe call to asMultiPoint() because we checked the type above
                for pt in geom.asMultiPoint():
                    # Check for 3D capability using pt.is3D()
                    if pt.is3D():
                        points.append((pt.x(), pt.y(), pt.z()))
            # 3. Handle single Point/PointZ features
            else:
                pt = geom.constGet()
                # Ensure the point is 3D before extracting coordinates
                if pt.is3D():
                    points.append((pt.x(), pt.y(), pt.z()))

        return points


    def get_points_2d(self):
        """ get all points from PointZ vector layer """

        points_2d = []
        for feature in self.points_layer.getFeatures():
            geom = feature.geometry()
            points = [geom.asPoint()]
            for pt in points:
                points_2d.append(QgsGeometry.fromPointXY(pt))  # Removes Z dimension

        return points_2d
