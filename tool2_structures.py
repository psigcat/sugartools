from qgis.core import Qgis, QgsProject, QgsExpressionContextUtils, QgsLayerTreeLayer, QgsMapThemeCollection, QgsBookmark, QgsReferencedRectangle, QgsLayoutItemMap, QgsPointXY, QgsGeometry, QgsPolygon, QgsVectorLayer, QgsFeature

import os
import json

from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_STRUCTURES = ["structures_db", "structures_workspace", "structures_name"]


class StructuresTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}

        self.utils = utils(self.parent)


    def read_database_config(self):
        """ read params from databases.json """

        try:
            with open(os.path.join(self.parent.plugin_dir, "databases.json")) as f:
                self.databases = json.load(f)
        except Exception as e:
            print(e)


    def fill_db(self):
        """ fill databases combobox """

        for database in self.databases:
            self.parent.dlg.structures_db.addItem(self.databases[database]["name"], {"value": database})


    def process_structures(self):
        """ get structures from database """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_STRUCTURES):
            return False

        # connect to database
        db = self.databases[self.parent.dlg.structures_db.currentData()["value"]]
        self.structures_db_obj = utils_database(self.parent.plugin_dir, db)
        self.structures_db = self.structures_db_obj.open_database()

        # save layout vars
        name = self.parent.dlg.structures_name.text()
        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName("structures")
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_db", db["name"])
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", name)

        self.create_structures(name)


    def create_structures(self, name):
        """ create structures and visualize """

        # create group
        group = self.utils.create_group(name)
        group_labels = self.utils.create_group(name + "_labels")

        # get view formas EW
        rows_ew = self.create_structure(name, "ew", group, group_labels)

        # get view formas NS
        rows_ns = self.create_structure(name, "ns", group, group_labels)

        # draw ns and ew for map
        self.create_structures_points(name, group_labels, rows_ew, "label", "map_ew")
        self.create_structures_points(name, group, rows_ew, "map_ew")
        self.create_structures_points(name, group_labels, rows_ns, "label", "map_ns")
        self.create_structures_points(name, group, rows_ns, "map_ns")

        # get view formas map
        self.create_structure(name, "map", group, group_labels)


    def create_structure(self, name, type, group, group_labels):
        """ get structure from db and create as layer """

        db_type = type
        if type == "map":
            db_type = ""

        sql = f"SELECT * FROM view_formas WHERE nom_nivel='{name}{db_type}'"
        rows = self.structures_db_obj.get_rows(sql)
        if not rows or rows == None or len(rows) == 0:
            #self.parent.dlg.messageBar.pushMessage(f"No structures found with name '{name}{db_type}' in db '{self.databases[database]["name"]}'", level=Qgis.Warning)
            self.parent.dlg.messageBar.pushMessage(f"No structures found with name '{name}{db_type}'", level=Qgis.Warning)
            return
        self.create_structures_points(name, group_labels, rows, "label", type)
        layer = self.create_structures_points(name, group, rows, type)

        self.create_structures_empty(name, type, "polygon", group, group_labels)
        self.create_structures_empty(name, type, "linestring", group, group_labels)
        self.create_structures_empty(name, type, "multilinestring", group, group_labels)

        self.create_map_theme(name, type)
        bookmark = self.create_spatial_bookmark(type, layer)

        if type == "map":
            self.parent.iface.mapCanvas().setExtent(bookmark.extent())

        return rows


    def create_structures_empty(self, name, type, geom_type, group, group_labels):
        """ create empty vector layer with given geom type """

        layer = self.utils.create_vector_layer(f"{name}_{type}_{geom_type}", geom_type, group, "&field=id:integer")
        layer_path = os.path.join(self.parent.dlg.structures_workspace.filePath(), "structures", name)
        self.utils.make_permanent(layer, layer_path)

        # clone layer for labels
        clone = layer.clone()
        clone.setName(f"{layer.name()}_label")
        QgsProject.instance().addMapLayer(clone, False)
        group_labels.addChildNode(QgsLayerTreeLayer(clone))


    def create_structures_points(self, name, group, rows, type, label_type=None):
        """ make vector layer with points """

        # invert NS or EW
        invert = 1
        invert_label = ""
        if self.parent.dlg.structures_ns_invert.isChecked() or self.parent.dlg.structures_ew_invert.isChecked():
            invert = -1
            invert_label = "_inverted"

        point_layer_uri = "Point?crs=epsg:25831&field=id:integer"
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
            feature.setAttributes([int(row[2])])
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

        path = os.path.join(self.parent.dlg.structures_workspace.filePath(), "structures", name)
        self.utils.make_permanent(point_layer, path)

        return point_layer


    def create_map_theme(self, name, type):
        """ create map theme from given layers """

        mapThemesCollection = QgsProject.instance().mapThemeCollection()
        mapThemes = mapThemesCollection.mapThemes()
        layersToChanges = [
            f"{name}_{type}", f"{name}_{type}_label", 
            f"{name}_{type}_polygon", f"{name}_{type}_polygon_label",
            f"{name}_{type}_linestring", f"{name}_{type}_linestring_label",
            f"{name}_{type}_multilinestring", f"{name}_{type}_multilinestring_label",
        ]
        if type == "map":
            layersToChanges.append(f"{name}_map_ns")
            layersToChanges.append(f"{name}_map_ns_label")
            layersToChanges.append(f"{name}_map_ew")
            layersToChanges.append(f"{name}_map_ew_label")
            layersToChanges.append(f"{name}_map_polygon")
            layersToChanges.append(f"{name}_map_polygon_label")
            layersToChanges.append(f"{name}_map_line")
            layersToChanges.append(f"{name}_map_line_label")
            layersToChanges.append(f"{name}_map_multiline")
            layersToChanges.append(f"{name}_map_multiline_label")

        for group in QgsProject.instance().layerTreeRoot().children():
            for subgroup in group.children():
                if isinstance(subgroup, QgsLayerTreeLayer):
                    subgroup.setItemVisibilityChecked(subgroup.name() in layersToChanges)
                else:
                    subgroup.setItemVisibilityChecked(False)
        
        mapThemeRecord = QgsMapThemeCollection.createThemeFromCurrentState(
            QgsProject.instance().layerTreeRoot(),
            self.parent.iface.layerTreeView().layerTreeModel()
        )
        mapThemesCollection.insert(type, mapThemeRecord)


    def create_spatial_bookmark(self, name, layer):
        """ create map theme from given layers """

        bookmark = QgsBookmark()
        bookmark.setId(name)
        bookmark.setName(name)
        referenced_extent = QgsReferencedRectangle(layer.extent(), layer.crs())
        bookmark.setExtent(referenced_extent)
        bookmark_manager = QgsProject.instance().bookmarkManager()
        bookmark_manager.addBookmark(bookmark)

        return bookmark


    def apply_spatial_bookmarks(self, layout, bookmarks):
        """ create map theme from given layers """

        for bookmark in bookmarks:
            for item in layout.items():
                if isinstance(item, QgsLayoutItemMap) and item.id() == bookmark.name():
                    item.setExtent(bookmark.extent())
                    item.refresh()
                    break


    # def create_structures_polygon(self, name, rows):
    #     """ make vector layer with points """

    #     polygon_layer_uri = "Polygon?crs=epsg:25831&field=id:integer"
    #     polygon_layer = QgsVectorLayer(polygon_layer_uri, name, "memory")

    #     QgsProject.instance().addMapLayer(polygon_layer)
    #     polygon_layer.startEditing()

    #     #for i in range(rows):
    #     point_list = []
    #     pos_x = 3
    #     pos_y = 4
    #     first_point = QgsPointXY(rows[0][pos_x], rows[0][pos_y])
    #     for row in rows:
    #         point_list.append(QgsPointXY(row[pos_x], row[pos_y]))
    #     point_list.append(first_point)
           
    #     geometry = QgsGeometry.fromPolygonXY([point_list])
    #     feature = QgsFeature()
    #     feature.setGeometry(geometry)
    #     feature.setAttributes([row[2]])
    #     polygon_layer.addFeature(feature)
    #     polygon_layer.commitChanges()
    #     self.parent.iface.setActiveLayer(polygon_layer)
    #     self.parent.iface.zoomToActiveLayer()