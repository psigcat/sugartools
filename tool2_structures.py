from qgis.core import Qgis, QgsProject, QgsExpressionContextUtils, QgsLayerTreeLayer, QgsMapThemeCollection, QgsBookmark, QgsReferencedRectangle, QgsLayoutItemMap, QgsPointXY, QgsGeometry, QgsPolygon, QgsVectorLayer, QgsFeature

import os
import json

from .utils_database import utils_database
from .utils import utils


SYMBOLOGY_DIR = "qml"
FIELDS_MANDATORY_STRUCTURES = ["structures_db", "structures_workspace", "structures_name"]

FIELDS = "&field=nom_nivel:string(8)&field=des_nivel:string(50)&field=num_pieza:integer&field=coord_x:float&field=coord_y:float&field=coord_z:float"
FIELDS_MAP_EMPTY = "&field=cod_est:integer&field=nom_nivel:string(8)&field=nom_est:string(10)&field=label:string(20)&field=t_est1:string(10)&field=t_est2:string(10)&field=t_forma:string(10)&field=princip:string(10)"
FIELDS_NS_EW_EMPTY = "&field=cod_est:integer&field=nom_nivel:string(8)&field=nom_est:string(10)&field=cod_sec:integer&field=nom_sec:string(10)&field=nom_estrat:string(10)&field=t_estrat"


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
        self.fill_db()


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
        group_map = self.utils.create_group(name + "_map")
        group_ew = self.utils.create_group(name + "_ew")
        group_ns = self.utils.create_group(name + "_ns")

        # get view formas EW
        rows_ew = self.create_structure(name, "ew", group_ew)
        self.create_structure_empty(name, "ew", group_ew)

        # get view formas NS
        rows_ns = self.create_structure(name, "ns", group_ns)
        self.create_structure_empty(name, "ns", group_ns)

        if not rows_ew and not rows_ns:
            self.parent.dlg.messageBar.pushMessage(f"No structures found with name '{name}{type}'", level=Qgis.Warning, duration=3)
            self.utils.remove_group(group_map)
            self.utils.remove_group(group_ew)
            self.utils.remove_group(group_ns)
            return

        # get view formas map
        self.create_structure(name, "map", group_map)
        self.active_structure = name

        # draw ns and ew for map
        self.create_structures_points(name, group_map, rows_ew, "map_ew")
        self.create_structures_points(name, group_map, rows_ew, "label", "map_ew")
        self.create_structures_points(name, group_map, rows_ns, "map_ns")
        self.create_structures_points(name, group_map, rows_ns, "label", "map_ns")

        # add empty layers
        self.create_structure_empty(name, "map", group_map)


    def create_structure(self, name, type, group):
        """ get structure from db and create as layer """

        db_type = type
        if type == "map":
            db_type = ""

        sql = f"SELECT * FROM view_formas WHERE nom_nivel='{name}{db_type}'"
        rows = self.structures_db_obj.get_rows(sql)
        if not rows or rows == None or len(rows) == 0:
            return False
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


    def create_structures_empty(self, name, type, geom_type, group):
        """ create empty vector layer with given geom type """

        if type == "ns" or type == "ew":
            field_names = FIELDS_NS_EW_EMPTY
        elif type == "map":
            field_names = FIELDS_MAP_EMPTY

        layer = self.utils.create_vector_layer(f"{name}_{type}_{geom_type}", geom_type, group, field_names)
        layer_path = os.path.join(self.parent.dlg.structures_workspace.filePath(), "structures", name, "layers_" + name)
        self.utils.make_permanent(layer, layer_path)

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, f"structures_{geom_type}.qml")
        layer.loadNamedStyle(symbology_path)


    def create_structures_points(self, name, group, rows, type, label_type=None):
        """ make vector layer with points """

        # invert NS or EW
        invert = 1
        invert_label = ""
        if self.parent.dlg.structures_ns_invert.isChecked() or self.parent.dlg.structures_ew_invert.isChecked():
            invert = -1
            invert_label = "_inverted"

        point_layer_uri = "Point?crs=epsg:25831&field=id:integer" + FIELDS

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
                int(row[2]),    # id = num_pieza
                row[0],         # nom_nivel
                row[1],         # des_nivel
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
                    item.setExtent(bookmark.extent())
                    item.refresh()
                    break


    def onLayoutLoaded(self):
        """ load spatial bookmarks when layout designer is opened """

        print("active", self.active_structure)
        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName("structures")

        if self.active_structure:
            bookmark_manager = QgsProject.instance().bookmarkManager()
            bookmark_map = bookmark_manager.bookmarkById(f"{self.active_structure}_map")
            bookmark_ns = bookmark_manager.bookmarkById(f"{self.active_structure}_ns")
            bookmark_ew = bookmark_manager.bookmarkById(f"{self.active_structure}_ew")

            if bookmark_map and bookmark_ns and bookmark_ew:
                layout = QgsProject.instance().layoutManager().layoutByName("structures")
                self.apply_spatial_bookmarks(layout, [bookmark_map, bookmark_ns, bookmark_ew])

            # set active structure to layout variable
            QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", self.active_structure)

        else:
            # set active structure to name extracted from first selected layer
            QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", self.active_structure)

            if self.parent.iface.activeLayer():
                name = self.parent.iface.activeLayer().name()
                name = name.split("_")[0]
                QgsExpressionContextUtils.setLayoutVariable(layout, "layout_structures_name", name)


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