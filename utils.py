from qgis.PyQt.QtCore import Qt, QFile
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QProgressBar
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.core import Qgis, QgsProject, QgsSettings, QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, QgsLayerTreeNode, QgsLayerTreeGroup, QgsMapThemeCollection, QgsWkbTypes, QgsPrintLayout, QgsReadWriteContext, QgsCoordinateReferenceSystemRegistry, QgsApplication, QgsMapLayerStyle, QgsFeatureRequest, QgsVectorDataProvider

import os
import configparser
import processing


SYMBOLOGY_DIR = "qml"
COMBO_SELECT = "(Select)"
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
        "expression": "nom_nivel",
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
        "expression": "nom_est",
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
        "expression": "label",
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
        "expression": "t_est1",
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
        "expression": "t_forma",
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
        "expression": "t_est2",
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
            show_warning(f"Couldn'f find metadata file: {metadata_file}")
            return None

        value = None
        try:
            metadata = configparser.ConfigParser()
            metadata.read(metadata_file)
            value = metadata.get(section, parameter)
        except Exception as e:
            show_warning(e)
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

        QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, QgsProject.instance().transformContext(), options)

        #block_layer = QgsVectorLayer(path, layer.name())
        #QgsProject.instance().addMapLayer(block_layer, False)

        # change the data source
        layer.setDataSource(path + f'|layername={layer.name()}', layer.name(), 'ogr')
        #layer.setDataProvider(myParams, name, layer type, QgsDataProvider.ProviderOptions())

        #print("created file", path, os.path.exists(path))


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
                if len(source) < 2:
                    self.parent.dlg.messageBar.pushMessage(f"No layername defined in layer {layer.name()}", level=Qgis.Warning, duration=3)
                    return

                # get source file name, file extension and table name
                source_file = source[0]
                source_file_extension = source_file.split('.')
                source_file_extension = source_file_extension[len(source_file_extension)-1]
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
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
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
        """ recalculate SHAPE_Length and SHAPE_Area of selected layers """

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
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} doesn't have fields SHAPE_Length or SHAPE_Area", level=Qgis.Warning, duration=3)
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
                        feature.setAttribute(shape_length_index, geom.length())
                        feature.setAttribute(shape_area_index, geom.area())
                        layer.updateFeature(feature)

                    layer.commitChanges()
                    self.parent.dlg.messageBar.pushMessage(f"Recalculation of SHAPE_Length and SHAPE_Area for layer {layer.name()} done", level=Qgis.Success, duration=3)

                else:
                    self.parent.dlg.messageBar.pushMessage(f"Layer {layer.name()} not editable", level=Qgis.Warning, duration=3)
                    return