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
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QLineEdit, QPlainTextEdit, QComboBox, QCheckBox
from qgis.gui import QgsFileWidget, QgsSpinBox, QgsExpressionBuilderDialog
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsSymbol, QgsMarkerSymbol, QgsSimpleFillSymbolLayer, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsLayerTreeLayer, QgsLayerTreeGroup, QgsExpressionContextUtils, QgsFeatureRequest, QgsExpressionContext, QgsExpressionContextUtils
from qgis.utils import iface

from .sugar_tools_dialog import SugarToolsDialog

import os
import datetime
from random import randrange


COMBO_SELECT = "(Select)"
FIELDS_SECTIONS = ["section_ew", "section_ns", "section_ew_inverted", "section_ns_inverted"]
FIELDS_MANDATORY_IMPORT = ["workspace"]
FIELDS_MANDATORY_LAYOUT = ["layer", "layout"]
SECTION_EW_PATTERN = "_EW"
SECTION_NS_PATTERN = "_NS"
INVERTED_STR = " inverted"
LAYOUT_MAP_ITEM = "Mapa principal"
#CSV_PARAMS = '?delimiter=%5Ct&maxFields=20000&detectTypes=yes&crs=EPSG:25831&spatialIndex=no&subsetIndex=no&watchFile=no'
CSV_PARAMS = '?maxFields=20000&detectTypes=yes&crs=EPSG:25831&spatialIndex=no&subsetIndex=no&watchFile=no'
CSV_PARAMS_COORDS_EW = '&xField=X&yField=Z'
CSV_PARAMS_COORDS_NS = '&xField=Y&yField=Z'
CSV_PARAMS_COORDS_EW_NEG = '&xField=X_NEG&yField=Z'
CSV_PARAMS_COORDS_NS_NEG = '&xField=Y_NEG&yField=Z'



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


    def check_mandatory(self, active_tab):
        """ Check if mandatory fields do have values """

        if not self.check_sections():
            return False

        if active_tab == "tabImport":
            FIELDS_MANDATORY = FIELDS_MANDATORY_IMPORT
        elif active_tab == "tabLayout":
            FIELDS_MANDATORY = FIELDS_MANDATORY_LAYOUT

        for field in FIELDS_MANDATORY:

            widget, widget_data = self.get_widget_data(field)
            if widget_data in (COMBO_SELECT, '--') or widget_data == '':
                self.dlg.messageBar.pushMessage(f"Mandatory field without information: {field}", level=Qgis.Warning)
                widget.setFocus()
                return False

        return True


    def check_sections(self):
        """ Check if at least one section is selected """

        for field in FIELDS_SECTIONS:

            widget, widget_data = self.get_widget_data(field)
            if widget_data:
                return True

        self.dlg.messageBar.pushMessage(f"At least one section has to be selected", level=Qgis.Warning)

        return False


    def get_layer_tree(self, node):
        """ recursevly parse whole layer tree """

        if isinstance(node, QgsLayerTreeLayer):
            if (self.dlg.section_ew.isChecked() and node.name().find(SECTION_EW_PATTERN) > 0) or (self.dlg.section_ns.isChecked() and node.name().find(SECTION_NS_PATTERN) > 0):
                self.dlg.layer.addItem(node.name())

        elif isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                self.get_layer_tree(child)


    def fill_layer(self):
        """ show all layers in combobox """

        self.dlg.layer.clear()
        self.dlg.layer.addItem(COMBO_SELECT)
        for group in QgsProject.instance().layerTreeRoot().children():
            self.get_layer_tree(group)


    def fill_layout(self):
        """ show all layouts in combobox """

        self.dlg.layout.clear()
        self.dlg.layout.addItem(COMBO_SELECT)
        layout_manager = QgsProject.instance().layoutManager()
        for layout in layout_manager.printLayouts():
            self.dlg.layout.addItem(layout.name())


    def load_file(self, file, csv_params_coords, inverted=False):
        """ load csv file as vector layer """

        inverted_str = ""
        if inverted:
            inverted_str = INVERTED_STR

        # file = 'Azdo_EW0_MMy77681_87860.txt'
        uri = os.path.join('file://' + self.secciones_path, file + CSV_PARAMS + csv_params_coords)
        csv_layer = QgsVectorLayer(uri, file[:-4] + inverted_str, 'delimitedtext')
        QgsProject.instance().addMapLayer(csv_layer)

        self.set_symbology(csv_layer)


    def set_symbology(self, layer):
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

        return [f for f in os.listdir(self.secciones_path) if os.path.isfile(os.path.join(self.secciones_path, f)) and f.find(pattern) > 0]


    def import_files(self, active_tab):
        """ import all files from selected workspace """

        if not self.check_mandatory(active_tab):
            return False

        # 1. recorrer todos los ficheros de la carpeta roca_bous_secciones
        # 2. si contienen _EW asigno coordinadas X=X, Y=Z
        # 3. si contienen _NS asigno coordinadas X=Y, Y=Z
        # importar como CSV

        self.secciones_path = self.dlg.workspace.filePath()
        
        if self.dlg.section_ew.isChecked():
            for file in self.get_file_list(SECTION_EW_PATTERN):
                self.load_file(file, CSV_PARAMS_COORDS_EW)

        if self.dlg.section_ns.isChecked():
            for file in self.get_file_list(SECTION_NS_PATTERN):
                self.load_file(file, CSV_PARAMS_COORDS_NS)

        if self.dlg.section_ew_inverted.isChecked():
            for file in self.get_file_list(SECTION_EW_PATTERN):
                self.load_file(file, CSV_PARAMS_COORDS_EW_NEG, True)

        if self.dlg.section_ns_inverted.isChecked():
            for file in self.get_file_list(SECTION_NS_PATTERN):
                self.load_file(file, CSV_PARAMS_COORDS_NS_NEG, True)

        # close dialog
        self.dlg.close()


    def has_matches(self, active_layer, expression):
        """ check if any feature in layer matches expression """

        request = QgsFeatureRequest().setFilterExpression(expression)
        matches = 0
        for f in active_layer.getFeatures(request):
           matches += 1
        if matches > 0:
            return True

        return False


    def write_layout_vars(self, layout):
        """ write variables to composition """

        section = ""
        layer_name = iface.activeLayer().name()
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
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_section", section)

        red_points = self.has_matches(iface.activeLayer(), "bol_nivelok = 'false'")
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_red_points", red_points)

        duplicated_points = self.has_matches(iface.activeLayer(), "bol_duplicado = 'true'")
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_duplicated_points", duplicated_points)

        no_coord = self.has_matches(iface.activeLayer(), "nom_cmateria = 'no coordenad'")
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_no_coord", no_coord)

        # falta thickness: derivar de nombres de capas
        # falta blocks


    def filter_layer_points(self):
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
            expr = "nom_cmateria != 'no coordenad'"
        
        #active_layer.setSubsetString("")
        iface.activeLayer().setSubsetString(expr)


    def load_layout(self, active_tab):
        """ only show selected layer and load into layout """

        if not self.check_mandatory(active_tab):
            return False

        # filter points
        self.filter_layer_points()

        # get selected layout
        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName(self.dlg.layout.currentText())
        self.write_layout_vars(layout)

        # set map extent to match main canvas extent
        mapItem = layout.itemById(LAYOUT_MAP_ITEM)
        mapCanvas = iface.mapCanvas()
        mapItem.zoomToExtent(mapCanvas.extent())

        # open layout
        iface.openLayoutDesigner(layout)

        # close dialog
        self.dlg.close()


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(iface.activeLayer())
        if expr_dialog.exec_():
            self.dlg.filter_expr.setText(expr_dialog.expressionText())


    def set_active_layer(self):
        """ set active layer """

        if self.dlg.layer.currentText() == COMBO_SELECT or self.dlg.layer.currentText() == "":
            return False

        # hide all layers but selected
        for group in QgsProject.instance().layerTreeRoot().children():
            group.setItemVisibilityChecked(group.name() == self.dlg.layer.currentText())

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
            self.dlg.layer.currentTextChanged.connect(self.set_active_layer)
            self.dlg.filter_expr_btn.clicked.connect(self.open_expr_builder)

        # show the dialog
        self.fill_layer()
        self.fill_layout()
        self.dlg.show()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            pass