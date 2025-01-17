# -*- coding: utf-8 -*-
"""
/***************************************************************************
 SugarTools
                                 A QGIS plugin
 Aqueological tools for QGIS
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2024-11-25
        git sha              : $Format:%H$
        copyright            : (C) 2024 by PSIG
        email                : geraldo@servus.at
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPlainTextEdit, QComboBox, QCheckBox, QProgressBar
from qgis.gui import QgsFileWidget, QgsSpinBox, QgsExpressionBuilderDialog
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsSymbol, QgsMarkerSymbol, QgsSimpleFillSymbolLayer, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsLayerTreeLayer, QgsLayerTreeNode, QgsLayerTreeGroup, QgsExpressionContextUtils, QgsFeatureRequest, QgsExpressionContext, QgsExpressionContextUtils, QgsProviderRegistry, QgsFeature
from qgis.utils import iface

from .sugar_tools_dialog import SugarToolsDialog

import os
import datetime
from random import randrange
import processing


COMBO_SELECT = "(Select)"
SYMBOLOGY_DIR = "qml"
FIELDS_SECTIONS = ["section_ew", "section_ns", "section_ew_inverted", "section_ns_inverted"]
FIELDS_MANDATORY_IMPORT = ["workspace", "delimiter"]
FIELDS_MANDATORY_IMPORT_POINTS = ["symbology"]
FIELDS_MANDATORY_LAYOUT = ["layer", "layout"]
SECTION_EW_PATTERN = "_EW"
SECTION_NS_PATTERN = "_NS"
INVERTED_STR = " inverted"
LAYOUT_MAP_ITEM = "Mapa principal"
CSV_PARAMS = '?maxFields=20000&detectTypes=yes&crs=EPSG:25831&spatialIndex=no&subsetIndex=no&watchFile=no'
CSV_PARAMS_COORDS_EW = '&xField=X&yField=Z'
CSV_PARAMS_COORDS_NS = '&xField=Y&yField=Z'
CSV_PARAMS_COORDS_EW_NEG = '&xField=X_NEG&yField=Z'
CSV_PARAMS_COORDS_NS_NEG = '&xField=Y_NEG&yField=Z'

# copia de site_params.py
SITES = {
    "":["", 0, 0, 0, 0, "", ""],
    "CG":["Cova Gran", 170000, 270000, 480000, 540000, "files\\simb_levels\\LYR_NOCREAT.lyr", "files\\simb_levels\\OVRLYR_NOCREAT.lyr"],
    "CG_S1":["Cova Gran, S1", 180000, 205000, 490000, 505000, "files\\simb_levels\\levels_CG_S1.lyr", "files\\simb_levels\\overlay_levels_CG_S1.lyr"],
    "CG_SV":["Cova Gran, SV", 202000, 205000, 494000, 500000, "files\\simb_levels\\levels_CG_S1.lyr", "files\\simb_levels\\overlay_levels_CG_S1.lyr"],
    "CG_S2S8":["Cova Gran, S2-S8", 205750, 210250, 500750, 504250, "files\\simb_levels\\levels_CG_S2S8.lyr", "files\\simb_levels\\overlay_levels_CG_S2S8.lyr"],
    "CG_SEA":["Cova Gran, SEA", 232500, 240700, 524600, 533000, "files\\simb_levels\\levels_CG_SEA.lyr", "files\\simb_levels\\overlay_levels_CG_SEA.lyr"],
    "RB":["Roca dels Bous", 17000, 40800, 74900, 88600, "files\\simb_levels\\levels_RB.lyr", "files\\simb_levels\\overlay_levels_RB.lyr"],
    "BG":["Balma Guilanyà", 98900, 110000, 505700, 512500, "files\\simb_levels\\levels_BG.lyr", "files\\simb_levels\\overlay_levels_BG.lyr"],
    "FR":["Font del Ros", 1000, 83000, 1000, 54000, "files\\simb_levels\\levels_FR.lyr", "files\\simb_levels\\overlay_levels_FR.lyr"],
    "PZ":["Abric Pizarro", 78000, 105000, 489000, 502000, "files\\simb_levels\\levels_PZ.lyr", "files\\simb_levels\\overlay_levels_PZ.lyr"],
    "CT":["Cova del Tabac", 295000, 320000, 499900, 510000, "files\\simb_levels\\levels_CT.lyr", "files\\simb_levels\\overlay_levels_CT.lyr"],
    "empty":["site_empty", 0, 1, 0, 1, "url_lyr", "url_overlyr"],
    "empty":["site_empty", 0, 1, 0, 1, "url_lyr", "url_overlyr"]
}


class SugarTools:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'SugarTools_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Sugar Tools')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
        self.first_start = None


    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('SugarTools', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action


    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = self.plugin_dir + '/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Sugar Tools'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Sugar Tools'),
                action)
            self.iface.removeToolBarIcon(action)


    def get_widget_data(self, fieldname):
        """ Get widgets and its data """

        widget = None
        data = None
        if not hasattr(self.dlg, fieldname):
            return None, None
        widget = getattr(self.dlg, fieldname)
        if type(widget) == QLineEdit:
            data = widget.text()
        elif type(widget) == QPlainTextEdit:
            data = widget.toPlainText()
        elif type(widget) is QgsFileWidget:
            data = widget.filePath()
        elif type(widget) is QgsSpinBox:
            data = widget.text()
        elif type(widget) is QComboBox:
            data = widget.currentText()
        elif type(widget) == QCheckBox:
            data = widget.isChecked()
        else:
            self.dlg.messageBar.pushMessage(f"Type of component not supported for field '{fieldname}': {type(widget)}", level=Qgis.Warning)
        return widget, data


    def check_mandatory_fields(self, fields):
        """ Check if mandatory fields do have values """

        for field in fields:
            widget, widget_data = self.get_widget_data(field)
            if widget_data in (COMBO_SELECT, '--') or widget_data == '':
                self.dlg.messageBar.pushMessage(f"Mandatory field without information: {field}", level=Qgis.Warning, duration=3)
                widget.setFocus()
                return False
        return True


    def check_mandatory(self, active_tab):
        """ Check if mandatory fields do have values """

        if not self.check_sections():
            return False

        if active_tab == "tabImport":
            if self.check_mandatory_fields(FIELDS_MANDATORY_IMPORT):
                if self.dlg.radioPoints.isChecked() or self.dlg.radioPointsBlocks.isChecked():
                    return self.check_mandatory_fields(FIELDS_MANDATORY_IMPORT_POINTS)
            return True


        elif active_tab == "tabLayout":
            return self.check_mandatory_fields(FIELDS_MANDATORY_LAYOUT)


    def check_sections(self):
        """ Check if at least one section is selected """

        for field in FIELDS_SECTIONS:

            widget, widget_data = self.get_widget_data(field)
            if widget_data:
                return True

        self.dlg.messageBar.pushMessage(f"At least one section has to be selected", level=Qgis.Warning, duration=3)

        return False


    def get_two_section_layers(self, node):
        """ recursevly parse whole layer tree and return first two layers of section """

        layer_names = []
        for group in node:
            layer_name = self.get_section_layer(group)
            if layer_name:
                layer_names.append(layer_name)

        return layer_names


    def get_section_layer(self, node):
        """ recursevly parse whole layer tree and return first two layers of section """

        if isinstance(node, QgsLayerTreeLayer):
            if ((self.dlg.section_ew.isChecked() and node.name().find(SECTION_EW_PATTERN) > 0) or (self.dlg.section_ns.isChecked() and node.name().find(SECTION_NS_PATTERN) > 0)) and not node.layer().isTemporary():
                
                return node.name()

        elif isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                return self.get_section_layer(child)


    # def add_layer_tree_item(self, node):
    #     """ recursevly parse whole layer tree """

    #     if isinstance(node, QgsLayerTreeLayer):
    #         if (self.dlg.section_ew.isChecked() and node.name().find(SECTION_EW_PATTERN) > 0) or (self.dlg.section_ns.isChecked() and node.name().find(SECTION_NS_PATTERN) > 0):
    #             self.dlg.layer.addItem(node.name())

    #     elif isinstance(node, QgsLayerTreeGroup):
    #         for child in node.children():
    #             self.add_layer_tree_item(child)


    def point_or_block(self):
        """ select type of symbology """

        self.dlg.groupBoxPoints.setVisible(self.dlg.radioPoints.isChecked() or self.dlg.radioPointsBlocks.isChecked())
        self.dlg.groupBoxBlocks.setVisible(self.dlg.radioBlocks.isChecked() or self.dlg.radioPointsBlocks.isChecked())

        self.dlg.labelSymbology.setVisible(self.dlg.radioPoints.isChecked() or self.dlg.radioPointsBlocks.isChecked())
        self.dlg.symbology.setVisible(self.dlg.radioPoints.isChecked() or self.dlg.radioPointsBlocks.isChecked())


    def fill_symbology(self, widget, filter):
        """ show all symbologies (but starting with overlay) in combobox """

        widget.clear()
        widget.addItem(COMBO_SELECT)

        symbology_path = os.path.join(self.plugin_dir, SYMBOLOGY_DIR)
        symbology_files = [f for f in os.listdir(symbology_path) if os.path.isfile(os.path.join(symbology_path, f)) and f.startswith(filter)]
        symbology_files.sort()
        for file in symbology_files:
            #self.dlg.symbologies.addItem(file[:-4])
            widget.addItem(file)


    def fill_layer(self):
        """ show all layers in combobox """

        self.dlg.layer.clear()
        self.dlg.layer.addItem(COMBO_SELECT)
        for group in QgsProject.instance().layerTreeRoot().children():
            #self.add_layer_tree_item(self.getLayerTree(group))
            self.getLayerTree(group)


    def getLayerTree(self, node):
        if isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                self.getLayerTree(child)
        elif isinstance(node, QgsLayerTreeNode):
            self.dlg.layer.addItem(node.name())


    def fill_layout(self):
        """ show all layouts in combobox """

        self.dlg.layout.clear()
        #self.dlg.layout.addItem(COMBO_SELECT)
        layout_manager = QgsProject.instance().layoutManager()
        for layout in layout_manager.printLayouts():
            self.dlg.layout.addItem(layout.name())


    def load_file(self, file, group, csv_params_coords, prefix, inverted=False):
        """ load csv file as vector layer """

        inverted_str = ""
        if inverted:
            inverted_str = INVERTED_STR

        delimiter = ""
        if self.dlg.delimiter.currentText() == "Tabulator (TSV)":
            delimiter = "&delimiter=%5Ct"

        csv_file = os.path.join(self.secciones_path, file)
        csv_file = os.path.abspath(csv_file)
        uri = f"file:///{csv_file}{CSV_PARAMS}{delimiter}{csv_params_coords}"
        
        file_name = os.path.basename(file)[:-4]
        if prefix == "_EW":
            layer_name = file_name.split("_MMy")[1]
        elif prefix == "_NS":
            layer_name = file_name.split("_x")[1]
        else:
            self.dlg.messageBar.pushMessage(f"Unknown prefix, has to be EW or NS but is '{prefix}'", level=Qgis.Warning)
            return

        layer_name = prefix + "_" + layer_name
        csv_layer = QgsVectorLayer(uri, "Pnt" + layer_name + inverted_str, "delimitedtext")
        QgsProject.instance().addMapLayer(csv_layer, False)

        layer_group = self.create_group("Sec" + layer_name, group)
        layer_group.insertChildNode(1, QgsLayerTreeLayer(csv_layer))

        self.filter_layer_points(csv_layer)

        if self.dlg.radioPoints.isChecked() or self.dlg.radioPointsBlocks.isChecked():
            self.set_symbology(csv_layer)

        if (self.dlg.radioBlocks.isChecked() or self.dlg.radioPointsBlocks.isChecked()) and self.dlg.option_polygons.isChecked():
            self.create_blocks(csv_layer, prefix, layer_group)

        self.write_layer_vars(csv_layer)

        self.progress.setValue(self.progress.value() + 1)


    def set_symbology(self, layer):
        """ set symbology from selected qml file """

        symbology = self.dlg.symbology.currentText()
        symbology_path = os.path.join(self.plugin_dir, SYMBOLOGY_DIR, symbology)
        layer.loadNamedStyle(symbology_path)
        layer.triggerRepaint()


    def set_symbology_bck(self, layer):
        """ set categorized symbology """

        # symbol = csv_layer.renderer().symbol()
        # print(type(symbol))
        # if type(symbol) is QgsMarkerSymbol:
        #     symbol.setSize(10)
        
        field_name = 'nom_nivel'
        fni = layer.fields().indexFromName(field_name)
        unique_values = layer.uniqueValues(fni)

        # fill categories
        categories = []
        for unique_value in unique_values:
            # initialize the default symbol for this geometry type
            symbol = QgsSymbol.defaultSymbol(layer.geometryType())

            # configure a symbol layer
            layer_style = {}
            layer_style['color'] = '%d, %d, %d' % (randrange(0, 256), randrange(0, 256), randrange(0, 256))
            layer_style['outline'] = '#000000'
            symbol_layer = QgsSimpleFillSymbolLayer.create(layer_style)

            # replace default symbol layer with the configured one
            if symbol_layer is not None:
                symbol.changeSymbolLayer(0, symbol_layer)

            # create renderer object
            category = QgsRendererCategory(unique_value, symbol, str(unique_value))
            # entry for the list of category items
            categories.append(category)

        # create renderer object
        renderer = QgsCategorizedSymbolRenderer(field_name, categories)

        # assign the created renderer to the layer
        if renderer is not None:
            layer.setRenderer(renderer)

        layer.triggerRepaint()


    def get_file_list(self, pattern):
        """ get all files containing pattern from workspace """

        for root_dir, dirs, files in os.walk(self.secciones_path):
            for folder in dirs:
                if self.dlg.radioPoints.isChecked() and folder.find("UA") != -1:
                    return self.return_file_list(folder, pattern)
                elif self.dlg.radioBlocks.isChecked() and folder.find("FO") != -1:
                    return self.return_file_list(folder, pattern)
                elif self.dlg.radioPointsBlocks.isChecked() and folder.find("UA") != -1:
                    return self.return_file_list(folder, pattern)
                elif self.dlg.radioPointsBlocks.isChecked() and folder.find("FO") != -1:
                    return self.return_file_list(folder, pattern)


    def return_file_list(self, folder, pattern):
        """ Build file list for given folder and pattern. """

        points_blocks_folder = os.path.join(self.secciones_path, folder)
        return [os.path.join(self.secciones_path, folder, f) for f in os.listdir(points_blocks_folder) if os.path.isfile(os.path.join(points_blocks_folder, f)) and f.find(pattern) > 0]


    def initProgressBar(self, msg, messageBar):
        """Show progress bar."""

        fileCount = 0
        # !!! hace falta limitarlo al directoria usado !!!
        for root_dir, cur_dir, files in os.walk(self.secciones_path):
            fileCount += len(files)

        progressMessageBar = messageBar.createMessage(msg)
        progress = QProgressBar()
        progress.setMaximum(fileCount)
        progress.setAlignment(Qt.AlignLeft|Qt.AlignVCenter)
        progressMessageBar.layout().addWidget(progress)
        messageBar.pushWidget(progressMessageBar, Qgis.Info)

        return progress


    def import_files(self, active_tab):
        """ import all files from selected workspace """

        if not self.check_mandatory(active_tab):
            return False

        # 0. crear grupo
        # 1. recorrer todos los ficheros del workspace
        # 2. si contienen _EW asigno coordinadas X=X, Y=Z
        # 3. si contienen _NS asigno coordinadas X=Y, Y=Z
        # importar como CSV

        self.secciones_path = self.dlg.workspace.filePath()
        self.progress = self.initProgressBar("Import sections...", self.dlg.messageBar)
        
        if self.dlg.section_ew.isChecked():
            group = self.create_group(SECTION_EW_PATTERN[1:] + " cross-sections")
            for file in self.get_file_list(SECTION_EW_PATTERN):
                self.load_file(file, group, CSV_PARAMS_COORDS_EW, SECTION_EW_PATTERN)

        if self.dlg.section_ns.isChecked():
            group = self.create_group(SECTION_NS_PATTERN[1:] + " cross-sections")
            for file in self.get_file_list(SECTION_NS_PATTERN):
                self.load_file(file, group, CSV_PARAMS_COORDS_NS, SECTION_NS_PATTERN)

        if self.dlg.section_ew_inverted.isChecked():
            group = self.create_group(SECTION_EW_PATTERN[1:] + " cross-sections")
            for file in self.get_file_list(SECTION_EW_PATTERN):
                self.load_file(file, group, CSV_PARAMS_COORDS_EW_NEG, SECTION_EW_PATTERN, True)

        if self.dlg.section_ns_inverted.isChecked():
            group = self.create_group(SECTION_NS_PATTERN[1:] + " cross-sections")
            for file in self.get_file_list(SECTION_NS_PATTERN):
                self.load_file(file, group, CSV_PARAMS_COORDS_NS_NEG, SECTION_NS_PATTERN, True)

        # remove progress bar
        self.dlg.messageBar.clearWidgets()

        # close dialog
        self.dlg.close()


    def create_group(self, group_name, parent=False):
        """ create layer group """

        if not parent:
            parent = QgsProject.instance().layerTreeRoot()

        group = parent.addGroup(group_name)
        return group


    def has_matches(self, active_layer, expression):
        """ check if any feature in layer matches expression """

        request = QgsFeatureRequest().setFilterExpression(expression)
        matches = 0
        for f in active_layer.getFeatures(request):
           matches += 1
        if matches > 0:
            return True

        return False


    def get_section_thickness(self, layers):
        """ extract thickness in cm from two layer names 
            format similar to: Azdo_EW0_MMy491945_532832.csv """

        if len(layers) < 2:
            return ""

        layers.sort()
        parts1 = layers[0].split("_")
        if len(parts1) < 4:
            return ""
        try:
            x1 = int(parts1[2][3:])
        except ValueError:
            return ""
        y1 = int(parts1[3])

        parts2 = layers[1].split("_")
        if len(parts2) < 4:
            return ""
        try:
            x2 = int(parts2[2][3:])
        except ValueError:
            return ""
        y2 = int(parts2[3])
        
        diffx = x2-x1
        diffy = y2-y1

        if diffx==0:
            return diffy/10

        return diffx/10


    def write_layout_vars(self, layout):
        """ write variables to composition """

        if self.dlg.layer.currentText() == COMBO_SELECT or self.dlg.layer.currentText() == "":
            return False
        layer = QgsProject.instance().mapLayersByName(self.dlg.layer.currentText())[0]

        var_name = "yacimiento"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "layer"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "section"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "red_points"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "duplicated_points"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "no_coord"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "thickness"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

        var_name = "blocks"
        var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)


    def write_layer_vars(self, layer):
        """ write variables to layer, for later use in layout """

        # yacimiento name
        request = QgsFeatureRequest()
        request.setLimit(1)
        first_feature = layer.getFeatures(request)
        feature = QgsFeature() 
        first_feature.nextFeature(feature)

        abr_yacimiento = None
        if "abr_yacimiento" in feature:
            abr_yacimiento = feature["abr_yacimiento"].upper()
        yacimiento = ""
        if abr_yacimiento and abr_yacimiento in SITES and len(SITES[abr_yacimiento]) > 0:
            yacimiento = SITES[abr_yacimiento][0]
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_yacimiento", yacimiento)

        # layer name
        section = ""
        layer_name = layer.name()
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_layer", layer_name)

        # section
        if layer_name.find(SECTION_EW_PATTERN) > 0:
            if layer_name.find(INVERTED_STR):
                section = self.dlg.section_ew.text()
            else:
                section = self.dlg.section_ew_inverted.text()
        elif layer_name.find(SECTION_NS_PATTERN) > 0:
            if layer_name.find(INVERTED_STR):
                section = self.dlg.section_ns.text()
            else:
                section = self.dlg.section_ns_inverted.text()
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_section", section)

        # red points
        red_points = self.has_matches(layer, "bol_nivelok = 'false'")
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_red_points", red_points)

        # duplicated points
        duplicated_points = self.has_matches(layer, "bol_duplicado = 'true'")
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_duplicated_points", duplicated_points)

        # no coord
        no_coord = self.has_matches(layer, "nom_cmateria = 'no coordenad'")
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_no_coord", no_coord)

        # thickness: derivar de nombres de capas
        section_layers = self.get_two_section_layers(QgsProject.instance().layerTreeRoot().children())
        thickness = self.get_section_thickness(section_layers)
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_thickness", thickness)

        # blocks
        blocks = ""
        if self.dlg.option_polygons.isChecked():
            blocks = "Blocks"
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_blocks", blocks)


    def create_blocks(self, layer, prefix, layer_group):
        """ filter out blocks from active layer """

        uri_components = QgsProviderRegistry.instance().decodeUri(layer.dataProvider().name(), layer.publicSource());

        #print(layer.name(), layer.source(), uri_components["path"])

        # apply geoprocess convex hull
        params = {
            'INPUT': layer.source(),
            #'INPUT': uri_components['path'],
            'FIELD': 'dib_pieza',
            'TYPE': 3,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }

        result = processing.run("qgis:minimumboundinggeometry", params)

        QgsProject.instance().addMapLayer(result['OUTPUT'], False)
        layer_group.insertChildNode(1, QgsLayerTreeLayer(result['OUTPUT']))

        #processing.runAndLoadResults("native:buffer", params)

        # rename block
        layer_name_parts = layer.name().split(prefix)
        layer_name = layer_name_parts[0] + prefix + "_bl" + layer_name_parts[1]
        result['OUTPUT'].setName(layer_name)

        # apply style
        symbology_path = os.path.join(self.plugin_dir, SYMBOLOGY_DIR, "blocks.qml")
        result['OUTPUT'].loadNamedStyle(symbology_path)
        result['OUTPUT'].triggerRepaint()


    def filter_layer_points(self, layer):
        """ filter active layer by query and selected options """

        expr = self.dlg.filter_expr.text()

        if self.dlg.exclude_red_points.isChecked():
            if expr != "":
                expr += " AND "
            expr = "bol_nivelok = 'true'"

        if self.dlg.exclude_duplicated_points.isChecked():
            if expr != "":
                expr += " AND "
            expr += "bol_duplicado = 'false'"

        if self.dlg.exclude_no_coords.isChecked():
            if expr != "":
                expr += " AND "
            expr += "nom_cmateria != 'no coordenad'"
        
        #layer.setSubsetString("")
        layer.setSubsetString(expr)


    def load_layout(self, active_tab):
        """ only show selected layer and load into layout """

        if not self.check_mandatory(active_tab):
            return False

        # get selected layout
        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName(self.dlg.layout.currentText())
        self.write_layout_vars(layout)

        # set map extent to match main canvas extent
        map_item = layout.itemById(LAYOUT_MAP_ITEM)
        map_canvas = iface.mapCanvas()
        map_item.zoomToExtent(map_canvas.extent())

        # open layout
        iface.openLayoutDesigner(layout)

        # close dialog
        self.dlg.close()


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(iface.activeLayer())
        if expr_dialog.exec_():
            self.dlg.filter_expr.setText(expr_dialog.expressionText())


    def toggle_layer_node(self, node):
        if isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                self.toggle_layer_node(child)
        elif isinstance(node, QgsLayerTreeNode):
            if isinstance(iface.activeLayer(), QgsVectorLayer):
                node.setItemVisibilityChecked(node.name() == iface.activeLayer().name() or node.name() == self.dlg.layer.currentText())
            else:
                node.setItemVisibilityChecked(node.name() == self.dlg.layer.currentText())


    def hide_all_layers_but_selected(self):
        """ hide all layers in layer tree """

        for group in QgsProject.instance().layerTreeRoot().children():
            self.toggle_layer_node(group)


    def select_layer(self):
        """ select layer in combo box and zoom to it """

        self.hide_all_layers_but_selected()
        if iface.activeLayer():
            active_layer_name = iface.activeLayer().name()
            self.dlg.layer.setCurrentText(active_layer_name)
            iface.zoomToActiveLayer()


    def set_and_zoom_active_layer(self):
        """ set active layer and zoom to it """

        if self.dlg.layer.currentText() == COMBO_SELECT or self.dlg.layer.currentText() == "":
            return False

        self.hide_all_layers_but_selected()

        active_layer = QgsProject.instance().mapLayersByName(self.dlg.layer.currentText())[0]
        iface.setActiveLayer(active_layer)
        iface.zoomToActiveLayer()


    def process(self):
        """ execute actions when ok clicked """

        active_tab = self.dlg.tabWidget.currentWidget().objectName()

        if active_tab == "tabImport":
            self.import_files(active_tab)
        elif active_tab == "tabLayout":
            self.load_layout(active_tab)


    def run(self):
        """Run method that performs all the real work"""

        # if (QgsProject.instance()):
        #     self.iface.messageBar().pushMessage(
        #           "Warning", "Please open a project file in order to use this plugin",
        #           level=Qgis.Warning, duration=3)
        #     return False

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        if self.first_start == True:
            self.first_start = False
            self.dlg = SugarToolsDialog()
            self.dlg.buttonBox.accepted.disconnect()
            self.dlg.buttonBox.accepted.connect(self.process)
            self.dlg.section_ew.stateChanged.connect(self.fill_layer)
            self.dlg.section_ns.stateChanged.connect(self.fill_layer)
            self.dlg.layer.currentTextChanged.connect(self.set_and_zoom_active_layer)
            self.dlg.filter_expr_btn.clicked.connect(self.open_expr_builder)
            self.dlg.radioPoints.toggled.connect(self.point_or_block)
            self.dlg.radioBlocks.toggled.connect(self.point_or_block)
            self.dlg.radioPointsBlocks.toggled.connect(self.point_or_block)
            iface.layerTreeView().currentLayerChanged.connect(self.select_layer)

        # show the dialog
        self.point_or_block()
        self.fill_symbology(self.dlg.symbology, "levels")
        self.fill_symbology(self.dlg.symbology_overlay, "overlay")
        self.fill_layer()
        self.fill_layout()
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            pass