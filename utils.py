from qgis.PyQt.QtCore import Qt, QFile
from qgis.PyQt.QtXml import QDomDocument
from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QProgressBar
from qgis.gui import QgsFileWidget, QgsMapLayerComboBox
from qgis.core import Qgis, QgsProject, QgsSettings, QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateTransform, QgsCoordinateReferenceSystem, QgsLayerTreeLayer, QgsMapThemeCollection, QgsWkbTypes, QgsPrintLayout, QgsReadWriteContext

import os


COMBO_SELECT = "(Select)"
FIELDS_SECTIONS = ["section_ew", "section_ns", "section_ew_inverted", "section_ns_inverted"]
FIELDS_MANDATORY_IMPORT = ["workspace", "delimiter"]
FIELDS_MANDATORY_IMPORT_POINTS = ["symbology"]
FIELDS_MANDATORY_LAYOUT = ["layer", "layout"]
FIELDS_MANDATORY_SHAPEFILES = ["shapefiles_folder"]


class utils:

    def __init__(self, parent):

        self.parent = parent


    def create_group(self, group_name, parent=False):
        """ create layer group """

        if not parent:
            parent = QgsProject.instance().layerTreeRoot()

        group = parent.addGroup(group_name)
        return group


    def remove_group(self, group):
        """ remove layer group """

        QgsProject.instance().layerTreeRoot().removeChildNode(group)


    def make_permanent(self, layer, path):
        """ save temporary layer to gpkg """

        if not os.path.exists(path):
            os.makedirs(path)
        path = os.path.join(path, layer.name() + ".gpkg")

        options = QgsVectorFileWriter.SaveVectorOptions()
        options.driverName = "GPKG"
        options.fileEncoding = "UTF-8"
        options.layerName = layer.name()
        options.actionOnExistingFile = QgsVectorFileWriter.CreateOrOverwriteFile
        options.ct = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem.fromEpsgId(25831), QgsProject.instance())

        QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, QgsProject.instance().transformContext(), options)

        #block_layer = QgsVectorLayer(path, layer.name())
        #QgsProject.instance().addMapLayer(block_layer, False)

        # change the data source
        layer.setDataSource(path + f'|layername={layer.name()}', layer.name(), 'ogr')
        #layer.setDataProvider(myParams, name, layer type, QgsDataProvider.ProviderOptions())


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
        

    def import_shapefiles(self):
        """ import all shapefiles from a folder """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY_SHAPEFILES):
            return False

        shp_group = self.utils.create_group("Map")
        shp_path = self.parent.dlg.shapefiles_folder.filePath()
        for file in os.listdir(shp_path):
            if file.endswith(".shp"):
                file_path = os.path.join(shp_path, file)
                print(file_path, file)
                shp_layer = QgsVectorLayer(file_path, file, "ogr")
                QgsProject.instance().addMapLayer(shp_layer, False)
                #shp_group.insertChildNode(1, QgsLayerTreeLayer(shp_layer))
                shp_group.addChildNode(QgsLayerTreeLayer(shp_layer))

        # create spatial bookmark


        # create map theme
        mapThemesCollection = QgsProject.instance().mapThemeCollection()
        mapThemes = mapThemesCollection.mapThemes()
        mapThemeRecord = QgsMapThemeCollection.createThemeFromCurrentState(
            QgsProject.instance().layerTreeRoot(),
            self.parent.iface.layerTreeView().layerTreeModel()
        )
        mapThemesCollection.insert("Map", mapThemeRecord)
        
        # apply spatial bookmark once layout "map" is opened


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
        if layout_added:
            self.parent.dlg.layout.addItem(layout.name())


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