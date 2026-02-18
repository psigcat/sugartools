from qgis.PyQt.QtCore import Qt, QFile, QMetaType, QPointF
from qgis.PyQt.QtGui import QColor
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QProgressBar
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.core import Qgis, QgsProject, QgsSettings, QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, QgsLayerTreeNode, QgsLayerTreeGroup, QgsMapThemeCollection, QgsWkbTypes, QgsPrintLayout, QgsReadWriteContext, QgsCoordinateReferenceSystemRegistry, QgsApplication, QgsMapLayerStyle, QgsFeatureRequest, QgsVectorDataProvider, QgsEditorWidgetSetup, QgsField, QgsDefaultValue, QgsCategorizedSymbolRenderer, QgsMarkerSymbol, QgsRendererCategory, QgsFontMarkerSymbolLayer, QgsUnitTypes, QgsProviderRegistry

import os
import configparser
import processing
import random
import shutil


COMBO_SELECT = "(Select)"
SYMBOLOGY_DIR = "qml"
FIELDS_SECTIONS = ["section_ew", "section_ns", "section_ew_inverted", "section_ns_inverted"]
FIELDS_MANDATORY_IMPORT = ["workspace", "delimiter"]
FIELDS_MANDATORY_IMPORT_POINTS = ["symbology"]
FIELDS_MANDATORY_LAYOUT = ["layer", "layout"]

STRUCTURES_FIELD_MAPPINGS = [
    {
        "alias": "",
        "comment": "",
        "expression": "fid",
        "length": 0,
        "name": "fid",
        "precision": 0,
        "sub_type": 0,
        "type": 4,
        "type_name": "int8"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("nom_nivel", ""), 8)',
        "length": 8,
        "name": "nom_nivel",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("nom_est", ""), 10)',
        "length": 10,
        "name": "nom_est",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("label", ""), 20)',
        "length": 20,
        "name": "label",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("t_est1", ""), 10)',
        "length": 10,
        "name": "t_est1",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("t_forma", ""), 10)',
        "length": 10,
        "name": "planta",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": 'left(coalesce("t_est2", ""), 10)',
        "length": 10,
        "name": "morfologia_3d",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "",
        "length": 10,
        "name": "forma_2d",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "",
        "length": 2,
        "name": "white_layer",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "",
        "length": 2,
        "name": "black_layer",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "",
        "length": 2,
        "name": "rubefaccion",
        "precision": 0,
        "sub_type": 0,
        "type": 10,
        "type_name": "text"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "SHAPE_Length",
        "length": 0,
        "name": "SHAPE_Length",
        "precision": 0,
        "sub_type": 0,
        "type": 6,
        "type_name": "double precision"
    },
    {
        "alias": "",
        "comment": "",
        "expression": "SHAPE_Area",
        "length": 0,
        "name": "SHAPE_Area",
        "precision": 0,
        "sub_type": 0,
        "type": 6,
        "type_name": "double precision"
    }
]

class utils:

    def __init__(self, parent):

        self.parent = parent


    def get_metadata_parameter(self, folder, section="general", parameter="version", file="metadata.txt"):
        """ Get parameter value from Metadata """

        # Check if metadata file exists
        metadata_file = os.path.join(folder, file)
        if not os.path.exists(metadata_file):
            self.parent.dlg.messageBar.pushMessage(f"Couldn'f find metadata file: {metadata_file}", level=Qgis.Warning)
            return None

        value = None
        try:
            metadata = configparser.ConfigParser()
            metadata.read(metadata_file)
            value = metadata.get(section, parameter)
        except Exception as e:
            print(e)
        finally:
            return value


    def create_group(self, group_name, parent=False):
        """ create layer group """

        if not parent:
            parent = QgsProject.instance().layerTreeRoot()

        group = parent.addGroup(group_name)
        return group


    def remove_group(self, group):
        """ remove layer group """

        QgsProject.instance().layerTreeRoot().removeChildNode(group)


    def save_layer_gpkg(self, layer, path, only_selected=False):
        """ save layer as gpkg """

        #print("create file", layer, path)

        if not os.path.exists(path):
            os.makedirs(path)
        path = os.path.join(path, layer.name() + ".gpkg")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer.name()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        options.ct = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem.fromEpsgId(25831), QgsProject.instance())

        if only_selected:
            options.onlySelectedFeatures = True

        QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            path,
            QgsProject.instance().transformContext(),
            options
        )

        #block_layer = QgsVectorLayer(path, layer.name())
        #QgsProject.instance().addMapLayer(block_layer, False)

        # change the data source
        layer.setDataSource(path + f'|layername={layer.name()}', layer.name(), 'ogr')
        #layer.setDataProvider(myParams, name, layer type, QgsDataProvider.ProviderOptions())

        #print("created file", path, os.path.exists(path))


    def add_layer_to_gpkg(self, layer, path, source_layer_name):
        """ save layer to an existing gpkg """

        sublayers = QgsProviderRegistry.instance().decodeUri("ogr", path)
        layer_metadata = QgsProviderRegistry.instance().providerMetadata("ogr")
        sublayer_list = layer_metadata.querySublayers(path)

        # source_layer_name = None

        # for sub in sublayer_list:

        #     print(sub)

        #     # Check if the geometry type is MultiPolygon (including 3D/Z)
        #     if QgsWkbTypes.geometryType(sub.wkbType()) == QgsWkbTypes.PolygonGeometry:
        #         # Check if it is Multi (to be precise as per your requirement)
        #         #if QgsWkbTypes.isMultiType(sub.wkbType()):
        #         source_layer_name = sub.name()
        #         break

        # if not source_layer_name:
        #     print("No MultiPolygon layer found in the selected GeoPackage, use default name.")
        #     source_layer_name = "polyon_layer"

        # create gpkg
        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.layerName = f"{source_layer_name}_3d"
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteLayer

        error, msg, new_path, layer_name = QgsVectorFileWriter.writeAsVectorFormatV3(
            layer,
            path,
            QgsProject.instance().transformContext(),
            options
        )

        if error == QgsVectorFileWriter.NoError:
            uri = f"{new_path}|layername={layer_name}"
            final_layer = QgsVectorLayer(uri, layer_name, "ogr")
            if final_layer.isValid():
                QgsProject.instance().addMapLayer(final_layer)


    def create_vector_layer(self, name, geom_type, group=False, fields=""):
        """ Create empty vector layer with given geometry type """

        uri = f"{geom_type}?crs=epsg:25831" + fields
        layer = QgsVectorLayer(uri, name, 'memory')

        # Add layer to TOC or group and canvas
        if group:
            QgsProject.instance().addMapLayer(layer, False)
            group.addChildNode(QgsLayerTreeLayer(layer))
        else:
            QgsProject.instance().addMapLayer(layer)

        return layer


    def get_widget_data(self, fieldname):
        """ Get widgets and its data """

        widget = None
        data = None
        if not hasattr(self.parent.dlg, fieldname):
            return None, None
        widget = getattr(self.parent.dlg, fieldname)
        if type(widget) == QLineEdit:
            data = widget.text()
        elif type(widget) == QPlainTextEdit:
            data = widget.toPlainText()
        elif type(widget) is QgsFileWidget:
            data = widget.filePath()
        elif type(widget) is QComboBox:
            data = widget.currentText()
        elif type(widget) == QCheckBox:
            data = widget.isChecked()
        elif type(widget) == QgsMapLayerComboBox:
            data = widget.currentText()
        else:
            self.parent.dlg.messageBar.pushMessage(f"Type of component not supported for field '{fieldname}': {type(widget)}", level=Qgis.Warning)
        return widget, data


    def check_mandatory_fields(self, fields):
        """ Check if mandatory fields do have values """

        for field in fields:
            widget, widget_data = self.get_widget_data(field)
            if widget_data in (COMBO_SELECT, '--') or not widget_data or widget_data == '':
                self.parent.dlg.messageBar.pushMessage(f"Mandatory field without information: {field}", level=Qgis.Warning, duration=3)
                widget.setFocus()
                return False
        return True


    def check_mandatory(self, active_tab):
        """ Check if mandatory fields do have values """

        if not self.check_sections():
            return False

        if active_tab == "tabImport":
            if self.check_mandatory_fields(FIELDS_MANDATORY_IMPORT):
                if self.parent.dlg.radioPoints.isChecked() or self.parent.dlg.radioPointsBlocks.isChecked():
                    return self.check_mandatory_fields(FIELDS_MANDATORY_IMPORT_POINTS)
                elif self.parent.dlg.radioBlocks.isChecked():
                    return True
                else:
                    return False
            else:
                return False
            return True


        elif active_tab == "tabLayout":
            return self.check_mandatory_fields(FIELDS_MANDATORY_LAYOUT)


    def check_sections(self):
        """ Check if at least one section is selected """

        for field in FIELDS_SECTIONS:

            widget, widget_data = self.get_widget_data(field)
            if widget_data:
                return True

        self.parent.dlg.messageBar.pushMessage(f"At least one section has to be selected", level=Qgis.Warning, duration=3)

        return False


    def import_layout(self, template):
        """ create layout from template shipped with plugin """

        project = QgsProject.instance()
        qpt_file_path = os.path.join(self.parent.plugin_dir, "qpt", template)

        # Create a new layout
        layout = QgsPrintLayout(project)
        layout.initializeDefaults()
        #layout.setName("Sections")
        qpt_file = QFile(qpt_file_path)

        if qpt_file.open(QFile.ReadOnly | QFile.Text):
            document = QDomDocument()
            if document.setContent(qpt_file):
                context = QgsReadWriteContext()
                if not layout.loadFromTemplate(document, context):
                    self.parent.dlg.messageBar.pushMessage(f"Failed to load {qpt_file_path} template from plugin folder.", level=Qgis.Warning)
                else:
                    self.parent.dlg.messageBar.pushMessage(f"QPT template {layout.name()} loaded successfully.", level=Qgis.Success)
            qpt_file.close()
        # else:
        #     print("Failed to open QPT file.")

        layout_added = project.layoutManager().addLayout(layout)

        # add to combo box
        # if layout_added:
        #     self.parent.dlg.layout.addItem(layout.name())


    def refactor_attributes(self):
        """ refactor attribute tables of selected layers """

        for group in self.parent.iface.layerTreeView().selectedNodes():

            if isinstance(group, QgsLayerTreeLayer):

                layer = QgsProject.instance().mapLayersByName(group.name())[0]
                #print(layer.name(), layer.source(), layer.providerType())

                if not layer.providerType() == 'ogr':
                    self.parent.dlg.messageBar.pushMessage(f"Does only work with layers of type 'ogr'", level=Qgis.Warning, duration=3)
                    return

                # remove layer part from file name
                source = layer.source().split('|layername=')

                # get source file name, file extension and table name
                source_file = source[0]
                source_file_extension = source_file.split('.')
                source_file_extension = source_file_extension[len(source_file_extension)-1]

                if len(source) < 2:
                    source_table = layer.name()
                else:
                    source_table = source[1].split('|')[0]
                
                if source_file_extension != 'gpkg':
                    self.parent.dlg.messageBar.pushMessage(f"Does only work for Geopackage (*.gpkg) layers", level=Qgis.Warning, duration=3)
                    return

                # refactor attribute table
                layer_refactored = processing.run("native:refactorfields", {
                    'INPUT': layer,
                    'FIELDS_MAPPING': STRUCTURES_FIELD_MAPPINGS,
                    'OUTPUT': 'TEMPORARY_OUTPUT'
                })["OUTPUT"]
                table_name_refactored = f"{source_table}_refactored"
                source_refactored = f"{source_file}|layername={table_name_refactored}"

                # save new layer to gpkg
                result = processing.run("native:savefeatures", {
                    'INPUT': layer_refactored,
                    'OUTPUT': source_file,
                    'LAYER_NAME': table_name_refactored,
                    'ACTION_ON_EXISTING_FILE': 1
                })

                # delete original table inside the gpkg
                processing.run("qgis:spatialiteexecutesql", {
                    'DATABASE': layer.source(),
                    'SQL': f'DROP TABLE "{source_table}"',
                })

                # rename table to original name
                processing.run("qgis:spatialiteexecutesql", {
                    'DATABASE': layer.source(),
                    'SQL': f'ALTER TABLE {table_name_refactored} RENAME TO "{source_table}"',
                })

                final_layer = QgsVectorLayer(layer.source(), source_table, "ogr")
                QgsProject.instance().addMapLayer(final_layer, False)
                parent_group = self.get_group_by_name(layer)
                if parent_group:
                    parent_group.addLayer(final_layer)
                QgsProject.instance().removeMapLayer(layer)

                # copy style from original to refactored layer
                symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "structures_map.qml")
                final_layer.loadNamedStyle(symbology_path)
                final_layer.triggerRepaint()

                self.parent.dlg.messageBar.pushMessage(f"Refactored structures attribute tables '{source_table}'", level=Qgis.Success)


    def apply_dictionaries(self):
        """ apply dictionaries to existing structures layers """

        # TODO! duplicate of refactor_attributes
        for group in self.parent.iface.layerTreeView().selectedNodes():

            if isinstance(group, QgsLayerTreeLayer):

                layer = QgsProject.instance().mapLayersByName(group.name())[0]
                # print(layer.name(), layer.source(), layer.providerType())

                if not layer.providerType() == 'ogr':
                    self.parent.dlg.messageBar.pushMessage(f"Does only work with layers of type 'ogr'", level=Qgis.Warning, duration=3)
                    return

                self.apply_dictionaries_to_layer(layer)


    def apply_dictionaries_to_layer(self, layer):
        """ apply dictionary to layer fields """

        FIELDS_MAP_OPTIONS = self.read_config_dict()

        for field_name, options in FIELDS_MAP_OPTIONS.items():
            field_index = layer.fields().indexOf(field_name)
            
            if field_index != -1:
                config_map = {opt: opt for opt in options}
                widget_setup = QgsEditorWidgetSetup('ValueMap', {'map': config_map})
                layer.setEditorWidgetSetup(field_index, widget_setup)
            else:
                print(f"Warning: Field '{field_name}' not found in layer.")


    def read_config_dict(self):
        """ read dictionaries from file structures_dictionaries.txt """

        dictionary = {
            't_est1': [],
            'planta': [],
            'morfologia_3d': [],
            'forma_2d': [],
            'white_layer': [],
            'black_layer': [],
            'rubefaccion': []
        }

        for key in dictionary:
            values = self.get_metadata_parameter(self.parent.plugin_dir, "structures_dictionaries", key, "settings.txt")
            dictionary[key] = [item.strip() for item in values.split(',')]

        return dictionary


    def calculate_length_area(self, layer):
        """ autoupdate fields SHAPE_length and SHAPE_area """

        provider = layer.dataProvider()
        provider.addAttributes([
            QgsField("SHAPE_length", QMetaType.Double, "", 10, 2),
            QgsField("SHAPE_area", QMetaType.Double, "", 10, 2)
        ])
        layer.updateFields()
        idx_length = layer.fields().indexOf("SHAPE_length")
        idx_area = layer.fields().indexOf("SHAPE_area")

        geom_type = layer.geometryType()
        if geom_type == QgsWkbTypes.PolygonGeometry:
            length_default = QgsDefaultValue("$perimeter/1000", True)
        else:
            length_default = QgsDefaultValue("$length/1000", True)
        area_default = QgsDefaultValue("$area/1000000", True)

        layer.setDefaultValueDefinition(idx_length, length_default)
        layer.setDefaultValueDefinition(idx_area, area_default)


    def get_group_by_name(self, layer):
        """ return group by name """

        root = QgsProject.instance().layerTreeRoot()
        layer_node = root.findLayer(layer.id())
        
        if layer_node:
            parent = layer_node.parent()
            
            if isinstance(parent, QgsLayerTreeGroup):
                if parent == root:
                    return root
                else:
                    return parent

        return False


    def read_database_config(self):
        """ read params from QGIS3.ini """

        databases = {}
        s = QgsSettings()
        s.beginGroup("MySQL/connections")

        for key in s.childGroups():
            host = s.value(key + "/host")
            port = s.value(key + "/port")
            database = s.value(key + "/database")
            username = s.value(key + "/username")
            password = s.value(key + "/password")

            if not port:
                port = 3306

            databases[key] = {
                "name": key,
                "host": host,
                "port": int(port),
                "db": database,
                "user": username,
                "passwd": password
            }

        return databases


    def fill_db_combo(self, combo, databases):
        """ fill databases combobox """

        combo.clear()
        combo.addItem("Please select a database connection", {"value": None})
        for database in databases:
            combo.addItem(databases[database]["name"], {"value": database})


    def get_layer_from_tree(self, name):
        """ parse whole layer tree and return first layer matching name """

        for group in QgsProject.instance().layerTreeRoot().children():
            if name == group.name():
                layers = QgsProject.instance().mapLayersByName(name)
                if len(layers) > 0:
                    return layers[0]

        return None


    def initProgressBar(self, msg, count):
        """Show progress bar."""

        messageBar = self.parent.dlg.messageBar

        progressMessageBar = messageBar.createMessage(msg)
        progress = QProgressBar()
        progress.setMaximum(count)
        progress.setAlignment(Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        messageBar.pushWidget(progressMessageBar, Qgis.Info)

        return progress


    def select_layer(self):
        """ zoom to selected layer and hide all not selected layers """

        self.hide_all_layers_but_selected()
        if self.parent.iface.activeLayer():
            self.parent.iface.zoomToActiveLayer()


    def hide_all_layers_but_selected(self):
        """ hide all layers in layer tree but selected, nor layers belonging to selected layer group """

        for group in QgsProject.instance().layerTreeRoot().children():
            self.toggle_layer_node(group)


    def toggle_layer_node(self, node):
        if isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                self.toggle_layer_node(child)
        elif isinstance(node, QgsLayerTreeNode):
            if isinstance(self.parent.iface.activeLayer(), QgsVectorLayer):
                node.setItemVisibilityChecked(node.name() == self.parent.iface.activeLayer().name())


    def create_custom_crs(self):
        """ create a custom CRS based on EPSG:28531, but using mm units """

        PROJ_STR = "+proj=utm +zone=31 +ellps=GRS80 +towgs84=0,0,0,0,0,0,0 +units=mm +no_defs"
        PROJ_NAME = "25831mm"

        crs = QgsCoordinateReferenceSystem()
        if not crs.createFromProj(PROJ_STR):
            print("Invalid PROJ string")
            return None

        # Check for duplicates in user-defined CRS list
        registry = QgsApplication.coordinateReferenceSystemRegistry()
        for existing in registry.userCrsList():
            print(existing.name, existing.proj)
            if existing.name == PROJ_NAME or existing.proj == crs.toProj():
                print(f"CRS already exists: {existing.name} (ID: {existing.id})")
                return existing
        
        crs.saveAsUserCrs(PROJ_NAME)
        print(f"Added custom user projection {PROJ_NAME}")
        return crs


    def recalculate_shape(self):
        """ recalculate SHAPE_length and SHAPE_area of selected layers """

        for group in self.parent.iface.layerTreeView().selectedNodes():

            if isinstance(group, QgsLayerTreeLayer):

                layer = QgsProject.instance().mapLayersByName(group.name())[0]
                #print("selected layer", layer.name(), layer.source(), layer.providerType())

                if not layer.providerType() == 'ogr':
                    self.parent.dlg.messageBar.pushMessage(f"Does only work with layers of type 'ogr'", level=Qgis.Warning, duration=3)
                    return

                # check if layer has fields shape_length and shape_area
                fields = layer.fields().names()
                fields = [item.lower() for item in fields]
                if not "shape_length" in fields or not "shape_area" in fields:
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have fields SHAPE_length or SHAPE_area", level=Qgis.Warning, duration=3)
                    return

                # get index of shape_length and shape_area
                shape_length_index = fields.index("shape_length")
                shape_area_index = fields.index("shape_area")

                # check if layer is editable
                caps = layer.dataProvider().capabilities()
                if caps & QgsVectorDataProvider.Capability.ChangeAttributeValues:

                    layer.startEditing()
                    for feature in layer.getFeatures():
                        geom = feature.geometry()
                        if not geom.type() == Qgis.GeometryType.Polygon:
                            self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have a Polygon geometry", level=Qgis.Warning, duration=3)
                            return

                        # overwrite with recalculated values
                        feature.setAttribute(shape_length_index, round(geom.length()/1000, 2))
                        feature.setAttribute(shape_area_index, round(geom.area()/1000000, 2))
                        layer.updateFeature(feature)

                    layer.commitChanges()
                    self.parent.dlg.messageBar.pushMessage(f"Recalculation of SHAPE_length and SHAPE_area for layer {layer.name()} done", level=Qgis.Success, duration=3)

                else:
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} not editable", level=Qgis.Warning, duration=3)
                    return


    def recalculate_shape_volume(self):
        """ recalculate SHAPE_volume of selected layers """

        for group in self.parent.iface.layerTreeView().selectedNodes():

            if isinstance(group, QgsLayerTreeLayer):

                layer = QgsProject.instance().mapLayersByName(group.name())[0]
                #print("selected layer", layer.name(), layer.source(), layer.providerType())

                if not layer.providerType() == 'ogr':
                    self.parent.dlg.messageBar.pushMessage(f"Does only work with layers of type 'ogr'", level=Qgis.Warning, duration=3)
                    return

                # check if layer has fields shape_volume
                fields = layer.fields().names()
                fields = [item.lower() for item in fields]
                if not "shape_volume" in fields:
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have field SHAPE_volume", level=Qgis.Warning, duration=3)
                    return

                # get index of shape_volume
                shape_volume_index = fields.index("shape_volume")

                # check if layer is editable
                caps = layer.dataProvider().capabilities()
                if caps & QgsVectorDataProvider.Capability.ChangeAttributeValues:

                    layer.startEditing()
                    for feature in layer.getFeatures():
                        geom = feature.geometry()
                        if not geom.type() == Qgis.GeometryType.Polygon:
                            self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have a Polygon geometry", level=Qgis.Warning, duration=3)
                            return

                        if not QgsWkbTypes.hasZ(geom.wkbType()):
                            self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have Z-values", level=Qgis.Warning, duration=3)
                            return

                        # overwrite with recalculated values
                        calculated_volume = self.calculate_multipolygon_z_volume(geom)
                        feature.setAttribute(shape_volume_index, calculated_volume)
                        layer.updateFeature(feature)

                    layer.commitChanges()
                    self.parent.dlg.messageBar.pushMessage(f"Recalculation of SHAPE_volume for layer {layer.name()} done", level=Qgis.Success, duration=3)

                else:
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} not editable", level=Qgis.Warning, duration=3)
                    return


    def fill_symbology_list(self):
        """ show all symbologies in combobox """

        self.parent.dlg.utils_sections_list.clear()
        self.parent.dlg.utils_sections_list.addItem(COMBO_SELECT)
        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR)
        filter_str = "levels_"

        symbology_files = [f for f in os.listdir(symbology_path) if os.path.isfile(os.path.join(symbology_path, f)) and f.startswith(filter_str)]
        symbology_files.sort()
        for file in symbology_files:
            self.parent.dlg.utils_sections_list.addItem(file[len(filter_str):-4])


    def load_existing_levels(self, level=True):
        """ load all nom_nivel from selected section """

        section = self.parent.dlg.utils_sections_list.currentText()
        if not section or section == COMBO_SELECT:
            self.parent.dlg.utils_sections_existing.setPlainText("")
            return

        file_name = f"levels_{section}.qml"
        if not level:
            file_name = "overlay_" + file_name

        qml_path = os.path.join(self.parent.plugin_dir, "qml", file_name)
        existing_levels = self.get_categories(qml_path)

        if level:
            existing_levels_str = ', '.join(existing_levels)
            self.parent.dlg.utils_sections_existing.setPlainText(existing_levels_str)

        return existing_levels, qml_path


    def get_categories(self, path):
        """ get list of categories from given QML file """

        layer = self.get_qml_layer(path)
        renderer = layer.renderer()
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            self.parent.dlg.messageBar.pushMessage(f"Style loaded, but it is not a Categorized Renderer, check file {path}", level=Qgis.Warning, duration=3)
            return

        values = [cat.value() for cat in renderer.categories()]
        values = list(filter(None, values))
        return values


    def get_qml_layer(self, path):
        """ get renderer from given QML file """

        if not os.path.exists(path):
            self.parent.dlg.messageBar.pushMessage(f"File {path} does not exist", level=Qgis.Warning, duration=3)
            return

        layer = QgsVectorLayer("Point?field=nom_nivel:string", "temp_layer", "memory")
        message, success = layer.loadNamedStyle(path)

        # if not success:
        #     return f"Actual Load Error: {res[1]}"

        return layer


    def add_styles(self):
        """ Create new styles """

        section = self.parent.dlg.utils_sections_list.currentText()
        if section == COMBO_SELECT:
            self.parent.dlg.messageBar.pushMessage(f"You have to select an existing section where to add new styles to.", level=Qgis.Warning, duration=3)
            return

        new_level = self.parent.dlg.utils_sections_name.text()
        new_color = self.parent.dlg.utils_sections_color.color()
        if not new_level or not new_color:
            self.parent.dlg.messageBar.pushMessage(f"You have to write a name and choose a color for the new level.", level=Qgis.Warning, duration=3)
            return

        print(f"Add style for section {section, new_level, new_color}")

        existing_levels, qml_path = self.load_existing_levels(True)
        existing_levels_overlay, qml_path_overlay = self.load_existing_levels(False)
        if new_level in existing_levels:
            self.parent.dlg.messageBar.pushMessage(f"Given level {new_level} already does exist in {qml_path}.", level=Qgis.Warning, duration=3)
        else:
            circle_symbol = self.create_symbol_circle(new_color)
            self.save_style(qml_path, new_level, circle_symbol)

        if new_level in existing_levels_overlay:
            self.parent.dlg.messageBar.pushMessage(f"Given level {new_level} already does exist in {qml_path_overlay}.", level=Qgis.Warning, duration=3)
        else:
            fontmarker_symbol = self.create_symbol_fontmarker(new_color)
            self.save_style(qml_path_overlay, new_level, fontmarker_symbol)


    def create_symbol_circle(self, new_color):
        """ Create a circle marker symbol """

        # create the Colored Circle symbol
        return QgsMarkerSymbol.createSimple({
            'name': 'circle',
            'color': new_color,
            'outline_style': 'no',
            'size': '3'
        })


    def create_symbol_fontmarker(self, new_color):
        """ Create a font marker symbol """

        # create the multi-layer FontMarker Symbol
        # layer 1: The Red Cross ('G')
        font_layer_main = QgsFontMarkerSymbolLayer("ESRI Default Marker", "G", 7.0)
        font_layer_main.setColor(QColor(new_color))
        font_layer_main.setOffset(QPointF(0, -0.5))
        font_layer_main.setSizeUnit(QgsUnitTypes.RenderPoints)
        font_layer_main.setOffsetUnit(QgsUnitTypes.RenderPoints)

        # layer 2: The Black Shadow ('F')
        font_layer_shadow = QgsFontMarkerSymbolLayer("ESRI Default Marker", "F", 7.0)
        font_layer_shadow.setColor(QColor(0, 0, 0))
        font_layer_shadow.setOffset(QPointF(0.5, -0.5))
        font_layer_shadow.setSizeUnit(QgsUnitTypes.RenderPoints)
        font_layer_shadow.setOffsetUnit(QgsUnitTypes.RenderPoints)

        # combine layers into a single symbol
        symbol = QgsMarkerSymbol()
        symbol.changeSymbolLayer(0, font_layer_main)
        symbol.appendSymbolLayer(font_layer_shadow)

        return symbol


    def create_qml_file(self, path):
        """ Create QML file from template """

        file_name = "levels_template.qml"
        if "overlay_levels" in path:
            file_name = "overlay_levels_template.qml"   

        template_path = os.path.join(self.parent.plugin_dir, "qml", file_name)

        shutil.copyfile(template_path, path)


    def save_style(self, path, new_level, new_symbol):
        """ Save new style in selected file """

        if not os.path.exists(path):
            self.parent.dlg.messageBar.pushMessage(f"Creating new QML file from template.", level=Qgis.Success, duration=3)
            self.create_qml_file(path)

        layer = self.get_qml_layer(path)
        renderer = layer.renderer()
        if not isinstance(renderer, QgsCategorizedSymbolRenderer):
            self.parent.dlg.messageBar.pushMessage(f"Style loaded, but it is not a Categorized Renderer, check file {path}", level=Qgis.Warning, duration=3)
            return

        # create new category and append
        new_cat = QgsRendererCategory(new_level, new_symbol, new_level, True)
        renderer.addCategory(new_cat)

        # save back to files levels_[section].qml and overlay_levels_[section].qml  
        msg_save, success_save = layer.saveNamedStyle(path)

        if success_save:
            self.parent.dlg.messageBar.pushMessage(f"Successfully updated and saved: {path}", level=Qgis.Success, duration=3)
            self.load_existing_levels()
        else:
            self.parent.dlg.messageBar.pushMessage(f"Failed to save QML: {msg_save}", level=Qgis.Warning, duration=3)


    def qml_exists(self, section):
        """ Check if file exists """

        file_level = f"levels_{section}.qml"
        file_overlay = "overlay_" + file_level

        path_level = os.path.join(self.parent.plugin_dir, "qml", file_level)
        path_overlay = os.path.join(self.parent.plugin_dir, "qml", file_overlay)

        return os.path.exists(path_level) or os.path.exists(path_overlay)


    def create_styles(self):
        """ Create new styles in new file """

        section = self.parent.dlg.utils_sections_new_section.text()
        level_str = self.parent.dlg.utils_sections_new_levels.text()
        if section == "" or level_str == "":
            self.parent.dlg.messageBar.pushMessage(f"You have to write a new section and at least one level.", level=Qgis.Warning, duration=3)
            return

        if self.qml_exists(section):
            self.parent.dlg.messageBar.pushMessage(f"QML file already does exist, change section name.", level=Qgis.Warning, duration=3)
            return

        print(f"Create style for section {section} and {level_str}")

        levels = level_str.split(",")
        for level in levels:
            level = level.strip()
            color = self.get_random_color()
            self.create_style(section, level, color)
            self.create_style(section, level, color, False)

        self.fill_symbology_list()


    def get_random_color(self):
        """ Generate random integers for R, G, and B """

        r = random.randint(0, 255)
        g = random.randint(0, 255)
        b = random.randint(0, 255)

        return QColor(r, g, b)


    def create_style(self, section, level, color, islevel=True):
        """ create style for one  """

        file_name = f"levels_{section}.qml"
        if not islevel:
            file_name = "overlay_" + file_name

        path = os.path.join(self.parent.plugin_dir, "qml", file_name)

        if islevel:
            symbol = self.create_symbol_circle(color)
        else:
            symbol = self.create_symbol_fontmarker(color)

        self.save_style(path, level, symbol)


    def calculate_multipolygon_z_volume(self, geometry):
        """Calculates volume of a closed MultiPolygonZ by summing signed volumes."""

        total_volume = 0.0
        
        # 1. Get the abstract geometry
        abstract_geom = geometry.constGet() # This is the QgsMultiPolygon
        
        # 2. Iterate through each Polygon in the MultiPolygon
        for i in range(abstract_geom.numGeometries()):
            polygon = abstract_geom.geometryN(i)
            
            # 3. Iterate through rings (Exterior = 0, Interiors > 0)
            for r in range(polygon.numInteriorRings() + 1):
                ring = polygon.exteriorRing() if r == 0 else polygon.getInteriorRing(r-1)
                
                # 4. Use the Divergence Theorem (Signed volume of tetrahedra)
                # We anchor to (0,0,0) and sum signed volumes of triangles in the fan
                nodes = [ring.pointN(p) for p in range(ring.numPoints())]
                
                # Simple fan triangulation for the ring
                for j in range(1, len(nodes) - 2):
                    p1 = nodes[0]
                    p2 = nodes[j]
                    p3 = nodes[j+1]
                    
                    # Math: Signed Volume = (1/6) * |P1 · (P2 × P3)|
                    v321 = p3.x() * p2.y() * p1.z()
                    v231 = p2.x() * p3.y() * p1.z()
                    v312 = p3.x() * p1.y() * p2.z()
                    v132 = p1.x() * p3.y() * p2.z()
                    v213 = p2.x() * p1.y() * p3.z()
                    v123 = p1.x() * p2.y() * p3.z()
                    
                    total_volume += (1.0/6.0) * (-v321 + v231 + v312 - v132 - v213 + v123)
                    
        return abs(total_volume)/1000000000