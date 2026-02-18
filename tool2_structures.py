from qgis.core import Qgis, QgsProject, QgsExpressionContextUtils, QgsLayerTreeLayer, QgsMapThemeCollection, QgsBookmark, QgsReferencedRectangle, QgsLayoutItemMap, QgsPointXY, QgsGeometry, QgsPolygon, QgsVectorLayer, QgsFeature, QgsRectangle, QgsPoint, QgsField, QgsFields, QgsWkbTypes
from qgis.PyQt.QtCore import QMetaType, QVariant

import os
import json
import numpy as np
from scipy.spatial import ConvexHull

from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_STRUCTURES_2d = ["structures_db", "structures_workspace", "structures_name"]
FIELDS_MANDATORY_STRUCTURES_3d = ["structures_db", "structures_layer_3d"]

FIELDS = "&field=nom_nivel:string(8)&field=num_pieza:integer&field=coord_x:real&field=coord_y:real&field=coord_z:real"
FIELDS_MAP_EMPTY = "&field=nom_nivel:string(8)&field=nom_est:string(10)&field=label:string(20)&field=t_est1:string(10)&field=planta:string(10)&field=morfologia_3d:string(10)&field=forma_2d:string(10)&field=white_layer:string(2)&field=black_layer:string(2)&field=rubefaccion:string(2)"
FIELDS_NS_EW_EMPTY = "&field=nom_nivel:string(8)&field=nom_est:string(10)&field=cod_sec:integer&field=nom_sec:string(10)&field=nom_estrat:string(10)&field=t_estrat"


class StructuresTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}
        self.active_structure = None

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.databases = self.utils.read_database_config()
        self.utils.fill_db_combo(self.parent.dlg.structures_db, self.databases)
        self.show_2d_or_3d()

        self.parent.dlg.structures_layer_3d.setAllowEmptyLayer(True, "None")
        if self.parent.iface.activeLayer():
            self.parent.dlg.structures_layer_3d.setLayer(self.parent.iface.activeLayer())


    def show_2d_or_3d(self):
        """ select type of process """

        self.parent.dlg.sections_2d.setVisible(self.parent.dlg.structures_check_2d.isChecked())
        self.parent.dlg.sections_3d.setVisible(self.parent.dlg.structures_check_3d.isChecked())


    def process_structures(self):
        """ get structures from database """

        is_2d = self.parent.dlg.structures_check_2d.isChecked()

        fields_mandatory = FIELDS_MANDATORY_STRUCTURES_2d
        if not is_2d:
            fields_mandatory = FIELDS_MANDATORY_STRUCTURES_3d

        if not self.utils.check_mandatory_fields(fields_mandatory):
            return False

        if not self.parent.dlg.structures_db.currentData()["value"]:
            self.parent.dlg.messageBar.pushMessage("Please select a database connection", level=Qgis.Warning, duration=3)
            return False

        # connect to database
        db = self.databases[self.parent.dlg.structures_db.currentData()["value"]]
        self.structures_db_obj = utils_database(self.parent.plugin_dir, db)
        self.structures_db = self.structures_db_obj.open_database()

        if is_2d:
            # save layout vars
            name = self.parent.dlg.structures_name.text()
            layout_manager = QgsProject.instance().layoutManager()
            layout = layout_manager.layoutByName("structures")
            QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_db", db["name"])
            QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", name)

            self.create_structures_2d(name)
        else:
            self.create_structures_3d()


    def create_structures_2d(self, name):
        """ create structures and visualize """

        # create group
        group_map = self.utils.create_group(name + "_map")
        group_map_helper = self.utils.create_group("helper", group_map)
        group_ew = self.utils.create_group(name + "_ew")
        group_ew_helper = self.utils.create_group("helper", group_ew)
        group_ns = self.utils.create_group(name + "_ns")
        group_ns_helper = self.utils.create_group("helper", group_ns)

        # get views from db
        rows_ew = self.create_structure(name, "ew", group_ew_helper)
        rows_ns = self.create_structure(name, "ns", group_ns_helper)

        if not rows_ew and not rows_ns:
            # trying without ew and ns
            rows = self.create_structure(name, "no", group_map_helper)
            self.active_structure = name

            if not rows_ew and not rows_ns:
                self.utils.remove_group(group_ew)
                self.utils.remove_group(group_ns)

                if rows:
                    self.create_structure_empty(name, "map", group_map)
                else:
                    self.utils.remove_group(group_map)
                    self.parent.dlg.messageBar.pushMessage(f"No structures found with name '{name}{type}'", level=Qgis.Warning, duration=3)

                return

        # create containers
        self.create_structure_empty(name, "ew", group_ew)
        self.create_structure_empty(name, "ns", group_ns)

        # get view formas map
        self.create_structure(name, "map", group_map_helper)
        self.active_structure = name

        # draw ns and ew for map
        self.create_structures_points(name, group_map_helper, rows_ew, "map_ew")
        self.create_structures_points(name, group_map_helper, rows_ew, "label", "map_ew")
        self.create_structures_points(name, group_map_helper, rows_ns, "map_ns")
        self.create_structures_points(name, group_map_helper, rows_ns, "label", "map_ns")

        # add empty layers
        self.create_structure_empty(name, "map", group_map)


    def create_structure(self, name, type, group):
        """ get structure from db and create as layer """

        db_type = type
        if type == "map" or type == "no":
            db_type = ""

        sql = f"SELECT * FROM view_formas WHERE nom_nivel='{name}{db_type}'"
        rows = self.structures_db_obj.get_rows(sql)
        if not rows or rows == None or len(rows) == 0:
            return False

        if type == "no":
            type = "map"

        layer = self.create_structures_points(name, group, rows, type)
        self.create_structures_points(name, group, rows, "label", type)
        bookmark = self.create_spatial_bookmark(name, type, layer)
        if type == "map":
            self.parent.iface.mapCanvas().setExtent(bookmark.extent())

        return rows


    def create_structure_empty(self, name, type, group):
        """ get empty structures """

        self.create_structures_empty(name, type, "polygon", group)
        self.create_structures_empty(name, type, "linestring", group)
        self.create_structures_empty(name, type, "multilinestring", group)
        self.create_map_theme(name, type)
        self.create_map_theme(name, type, True)


    def create_structures_empty(self, name, type, geom_type, group):
        """ create empty vector layer with given geom type """

        if type == "" or type == "ns" or type == "ew":
            field_names = FIELDS_NS_EW_EMPTY
        elif type == "map":
            field_names = FIELDS_MAP_EMPTY

        layer = self.utils.create_vector_layer(f"{name}_{type}_{geom_type}", geom_type, group, field_names)
        layer_path = os.path.join(self.parent.dlg.structures_workspace.filePath(), "structures", name, "layers_" + name)
        self.utils.save_layer_gpkg(layer, layer_path)

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, f"structures_{geom_type}.qml")
        layer.loadNamedStyle(symbology_path)

        if type == "map":

            self.utils.apply_dictionaries_to_layer(layer)
            self.utils.calculate_length_area(layer)


    def create_structures_points(self, name, group, rows, type, label_type=None):
        """ make vector layer with points """

        # invert NS or EW
        invert = 1
        invert_label = ""
        if self.parent.dlg.structures_ns_invert.isChecked() or self.parent.dlg.structures_ew_invert.isChecked():
            invert = -1
            invert_label = "_inverted"

        point_layer_uri = "Point?crs=epsg:25831" + FIELDS

        name_type = f"{type}"
        if type != "map":
            name_type = f"{type}{invert_label}"
        if label_type:
            name_type = f"{label_type}_label"
        point_layer = QgsVectorLayer(point_layer_uri, f"{name}_{name_type}", "memory")

        QgsProject.instance().addMapLayer(point_layer, False)
        group.addChildNode(QgsLayerTreeLayer(point_layer))

        point_layer.startEditing()

        # coordinates
        pos_x = 3 # x
        pos_y = 4 # y
        if type == "ns" or label_type == "ns":
            pos_x = 4 # y
            pos_y = 5 # z
        elif type == "ew" or label_type == "ew":
            pos_x = 3 # x
            pos_y = 5 # z

        for row in rows:
            feature = QgsFeature()
            point = QgsPointXY(row[pos_x] * invert, row[pos_y])
            geometry = QgsGeometry.fromPointXY(point)
            feature.setGeometry(geometry)

            field_values = [
                #int(row[2]),    # id = num_pieza
                row[0],         # nom_nivel
                #row[1],         # des_nivel
                int(row[2]),    # id = num_pieza
                row[3],         # coord_x
                row[4],         # coord_y
                row[5]          # coord_z
            ]
            feature.setAttributes(field_values)

            point_layer.addFeature(feature)
           
        point_layer.commitChanges()
        self.parent.iface.setActiveLayer(point_layer)
        self.parent.iface.zoomToActiveLayer()

        # apply style
        if type == "map_ew":
            type = "ew"
        elif type == "map_ns":
            type = "ns"
        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, f"structures_points_{type}.qml")
        point_layer.loadNamedStyle(symbology_path)
        point_layer.triggerRepaint()

        path = os.path.join(self.parent.dlg.structures_workspace.filePath(), "structures", name, "layers_" + name)
        self.utils.save_layer_gpkg(point_layer, path)

        return point_layer


    def create_map_theme(self, name, type, print=False):
        """ create map theme from given layers """

        mapThemesCollection = QgsProject.instance().mapThemeCollection()
        mapThemes = mapThemesCollection.mapThemes()
        layersToChanges = [
            #f"{name}_{type}",
            #f"{name}_{type}_label", 
            f"{name}_{type}_polygon",
            f"{name}_{type}_linestring",
            f"{name}_{type}_multilinestring",
        ]
        if type == "map":
            #layersToChanges.append(f"{name}_map_ns")
            #layersToChanges.append(f"{name}_map_ns_label")
            #layersToChanges.append(f"{name}_map_ew")
            #layersToChanges.append(f"{name}_map_ew_label")
            layersToChanges.append(f"{name}_map_polygon")
            layersToChanges.append(f"{name}_map_line")
            layersToChanges.append(f"{name}_map_multiline")

        for group in QgsProject.instance().layerTreeRoot().children():
            for subgroup in group.children():
                if isinstance(subgroup, QgsLayerTreeLayer):
                    subgroup.setItemVisibilityChecked(subgroup.name() in layersToChanges)
                else:
                    for subsubgroup in subgroup.children():
                        if isinstance(subsubgroup, QgsLayerTreeLayer):
                            subsubgroup.setItemVisibilityChecked(subsubgroup.name() in layersToChanges)
                        else:
                            subsubgroup.setItemVisibilityChecked(False)
        
        mapThemeRecord = QgsMapThemeCollection.createThemeFromCurrentState(
            QgsProject.instance().layerTreeRoot(),
            self.parent.iface.layerTreeView().layerTreeModel()
        )
        mapThemesCollection.insert(f"{name}_{type}", mapThemeRecord)


    def create_spatial_bookmark(self, name, type, layer):
        """ create map theme from given layers """

        bookmark = QgsBookmark()
        bookmark.setId(f"{name}_{type}")
        bookmark.setName(f"{name}_{type}")
        referenced_extent = QgsReferencedRectangle(layer.extent(), layer.crs())
        bookmark.setExtent(referenced_extent)
        bookmark_manager = QgsProject.instance().bookmarkManager()
        bookmark_manager.addBookmark(bookmark)

        return bookmark


    def apply_spatial_bookmarks(self, layout, bookmarks):
        """ create map theme from given layers """

        for bookmark in bookmarks:
            for item in layout.items():
                bookmark_extent = bookmark.name().split("_")[1]
                if isinstance(item, QgsLayoutItemMap) and item.id() == bookmark_extent:
                    #print("set extent", bookmark.name())
                    #item.setExtent(bookmark.extent())
                    self.set_extent_preserving_size(item, bookmark.extent())
                    break


    def set_extent_preserving_size(self, map_item: QgsLayoutItemMap, new_extent: QgsRectangle):
        """ Set Extent Without Changing Size of QgsLayoutItemMap """

        # Get current item width and height in layout units (e.g., mm)
        item_width = map_item.rect().width()
        item_height = map_item.rect().height()
        item_ratio = item_width / item_height

        # Calculate extent dimensions
        extent_width = new_extent.width()
        extent_height = new_extent.height()
        extent_ratio = extent_width / extent_height

        # Adjust extent to match item aspect ratio
        center = new_extent.center()

        if extent_ratio > item_ratio:
            # Extent is too wide, adjust height
            new_height = extent_width / item_ratio
            new_extent = QgsRectangle(
                center.x() - extent_width / 2,
                center.y() - new_height / 2,
                center.x() + extent_width / 2,
                center.y() + new_height / 2,
            )
        else:
            # Extent is too tall, adjust width
            new_width = extent_height * item_ratio
            new_extent = QgsRectangle(
                center.x() - new_width / 2,
                center.y() - extent_height / 2,
                center.x() + new_width / 2,
                center.y() + extent_height / 2,
            )

        # Now set the adjusted extent without changing item size
        map_item.setExtent(new_extent)
        map_item.refresh()


    def onLayoutLoaded(self):
        """ load spatial bookmarks when layout designer is opened """

        # print("active", self.active_structure)
        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName("structures")

        # set active structure to layout variable
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", self.active_structure)

        if self.active_structure:
            bookmark_manager = QgsProject.instance().bookmarkManager()
            bookmark_map = bookmark_manager.bookmarkById(f"{self.active_structure}_map")
            bookmark_ns = bookmark_manager.bookmarkById(f"{self.active_structure}_ns")
            bookmark_ew = bookmark_manager.bookmarkById(f"{self.active_structure}_ew")

            if bookmark_map and bookmark_ns and bookmark_ew:
                self.apply_spatial_bookmarks(layout, [bookmark_map, bookmark_ns, bookmark_ew])

        else:
            # set active structure to name extracted from first selected layer
            if self.parent.iface.activeLayer():
                name = self.parent.iface.activeLayer().name()
                name = name.split("_")[0]
                QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", name)


    def create_structures_3d(self):
        """ create structures 3d and visualize """

        polygon_layer_2d = self.parent.dlg.structures_layer_3d.currentLayer()
        if polygon_layer_2d is None:
            self.parent.dlg.messageBar.pushMessage(f"No polygon layer selected!", level=Qgis.Warning, duration=3)
            return

        # get nom_est from gpkg
        unique_nom_est = self.get_unique_nom_est(polygon_layer_2d)

        if not unique_nom_est:
            self.parent.dlg.messageBar.pushMessage(f"Layer not valid for creating 3d structures!", level=Qgis.Warning, duration=3)
            return

        # create 3d layer 
        polygon_layer_uri = "MultiPolygonZ?crs=epsg:25831&field=nom_est:string(10)"
        polygon_layer = QgsVectorLayer(polygon_layer_uri, f"{polygon_layer_2d.name()}_3d", "memory")
        #QgsProject.instance().addMapLayer(polygon_layer)

        # get all points from database
        for nom_est in unique_nom_est:
            rows = self.load_points_from_db(nom_est)
            if rows:
                points_layer = self.draw_points(rows, nom_est)

                # create 3d from points
                points = self.get_points_3d(points_layer)
                polygon_geom = self.create_3d_from_points(points)
                self.append_polygons_to_layer(polygon_layer, polygon_geom, nom_est)
            else:
                print("no rows for nom_est:", nom_est)

        # save to new layer in selected geopackage and show in QGIS
        gpkg_path = polygon_layer_2d.source().split("|")[0]
        self.utils.add_layer_to_gpkg(polygon_layer, gpkg_path, polygon_layer_2d.name())


    def get_unique_nom_est(self, layer):
        """ read every feature and create list of unique field values for nom_est """

        if not layer.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Layer failed to load!", level=Qgis.Warning, duration=3)
            return False

        # find index of 'nom_est' field
        idx = layer.fields().lookupField('nom_est')

        if idx == -1:
            self.parent.dlg.messageBar.pushMessage(f"Field 'nom_est' not found!", level=Qgis.Warning, duration=3)
            return False

        unique_list = layer.dataProvider().uniqueValues(idx)
        final_list = list(unique_list)

        return final_list


    def load_points_from_db(self, name):
        """ connect to database and load all points with level name = nom_est, "ns", "ew" """

        sql = f"SELECT * FROM view_formas WHERE nom_nivel='{name}' OR  nom_nivel='{name}ns' OR nom_nivel='{name}ew'"
        rows = self.structures_db_obj.get_rows(sql)
        if not rows or rows == None or len(rows) == 0:
            return False

        return rows


    def draw_points(self, rows, nom_est):
        """ draw blocks from given database rows """

        # temporary points layer
        points_layer_uri = "PointZ?crs=epsg:25831&field=nom_est:string(10)"
        points_layer = QgsVectorLayer(points_layer_uri, nom_est, "memory")
        #QgsProject.instance().addMapLayer(points_layer)

        points_layer.startEditing()

        for row in rows:
            fields = QgsFields()
            fields.append(QgsField("nom_est", QMetaType.QString))
            feature = QgsFeature(fields)

            point = QgsPoint(row[3], row[4], row[5]) #xy
            geometry = QgsGeometry.fromPoint(point)
            feature.setGeometry(geometry)
            feature.setAttributes([row[0]]) # nom_est
            points_layer.addFeature(feature)

        points_layer.commitChanges()
        #self.parent.iface.setActiveLayer(points_layer)
        #self.parent.iface.zoomToActiveLayer()

        return points_layer


    def get_points_3d(self, points_layer):
        """ get all points from PointZ vector layer """

        points = []
        # Define the acceptable WKB types for points
        point_types = [QgsWkbTypes.Type.Point, QgsWkbTypes.Type.PointZ, QgsWkbTypes.Type.MultiPoint, QgsWkbTypes.Type.MultiPointZ]

        for feature in points_layer.getFeatures():
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


    def create_3d_from_points(self, points):
        """ create 3d polygon from points """

        for point in points:
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

            return merged_geom


    def append_polygons_to_layer(self, threed_layer, polygons_geom, nom_est):
        """ append polygon geometries to target polygon 3d layer """

        # Append to Target Layer Provider
        provider = threed_layer.dataProvider()
        provider.addAttributes([QgsField("SHAPE_volume", QVariant.Double, "", 10, 9)])
        threed_layer.updateFields()

        feature = QgsFeature(threed_layer.fields())
        feature.setGeometry(polygons_geom) 
        calculated_volume = self.utils.calculate_multipolygon_z_volume(polygons_geom)
        feature.setAttributes([nom_est, calculated_volume])
        threed_layer.addFeature(feature)

        threed_layer.startEditing()
        success = provider.addFeatures([feature])

        if success:
            threed_layer.commitChanges()
            self.parent.dlg.messageBar.pushMessage(f"SUCCESS: Feature successfully appended to GeoPackage layer '{threed_layer.name()}' via data provider.", level=Qgis.Success, duration=3)
            threed_layer.triggerRepaint()
            return True
        else:
            threed_layer.rollBack()
            self.parent.dlg.messageBar.pushMessage(f"FAILURE: Provider failed to add feature. The GeoPackage rejected the geometry during the edit commit.", level=Qgis.Critical, duration=3)
            return False