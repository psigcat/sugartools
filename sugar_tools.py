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
from qgis.PyQt.QtWidgets import QAction
from qgis.utils import iface

import os

from .utils import utils
from .sugar_tools_dialog import SugarToolsDialog
from .tool1_sections import SectionsTool
from .tool2_structures import StructuresTool
from .tool3_remounting import RemountingTool


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

        icon_path = self.plugin_dir + '/icon2.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Sugar Tools Layout'),
            callback=lambda:self.load_layout('tabLayout'),
            parent=self.iface.mainWindow())

        # Create the dialog with elements (after translation) and keep reference
        # Only create GUI ONCE in callback, so that it will only load when the plugin is started
        self.first_start = False
        self.sections_tool = SectionsTool(self)

        self.dlg = SugarToolsDialog()
        self.dlg.buttonBox.accepted.disconnect()
        self.dlg.buttonBox.accepted.connect(self.process)
        self.dlg.section_ew.stateChanged.connect(self.sections_tool.fill_layer)
        self.dlg.section_ns.stateChanged.connect(self.sections_tool.fill_layer)
        self.dlg.layer.currentTextChanged.connect(self.sections_tool.set_and_zoom_active_layer)
        self.dlg.filter_expr_btn.clicked.connect(self.sections_tool.open_expr_builder)
        self.dlg.radioPoints.toggled.connect(self.sections_tool.point_or_block)
        self.dlg.radioBlocks.toggled.connect(self.sections_tool.point_or_block)
        self.dlg.radioPointsBlocks.toggled.connect(self.sections_tool.point_or_block)
        self.dlg.import_layout_sections_btn.clicked.connect(lambda:self.sections_tool.import_layout("layout_sections.qpt"))
        self.dlg.import_layout_map_btn.clicked.connect(lambda:self.sections_tool.import_layout("layout_map.qpt"))
        self.dlg.import_layout_structures_btn.clicked.connect(lambda:self.sections_tool.import_layout("layout_structures.qpt"))
        self.dlg.import_shapefiles_btn.clicked.connect(self.sections_tool.import_shapefiles)
        self.dlg.symbology_folder.fileChanged.connect(self.sections_tool.fill_symbology)
        self.dlg.symbology_overlay_folder.fileChanged.connect(self.sections_tool.fill_symbology_overlay)
        iface.layerTreeView().currentLayerChanged.connect(self.sections_tool.select_layer)
        iface.layoutDesignerOpened.connect(self.sections_tool.onLayoutLoaded)

        self.sections_tool.fill_layer()
        self.sections_tool.fill_layout()


    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Sugar Tools'),
                action)
            self.iface.removeToolBarIcon(action)


    def process(self):
        """ execute actions when ok clicked """

        main_tab = self.dlg.tabWidgetMain.currentWidget().objectName()
        active_tab = self.dlg.tabWidgetSections.currentWidget().objectName()

        if main_tab == "tabSections":
            if active_tab == "tabImport":
                self.sections_tool.import_files(active_tab)

            elif active_tab == "tabLayout":
                self.sections_tool.load_layout(active_tab)

        elif main_tab == "tabStructures":
            self.structures_tool.process_structures()

        elif main_tab == "tabRemounting":
            self.remounting_tool.process_remounting()


    def run(self):
        """Run method that performs all the real work"""

        # show the dialog
        self.sections_tool.point_or_block()
        self.sections_tool.preset_fields()
        self.sections_tool.fill_symbology()
        self.sections_tool.fill_symbology_overlay()
        self.dlg.show()

        # structures
        self.structures_tool = StructuresTool(self)
        self.structures_tool.read_database_config()
        self.structures_tool.fill_db()

        # remounting
        self.remounting_tool = RemountingTool(self)
        self.remounting_tool.setup()

        # Run the dialog event loop
        result = self.dlg.exec_()

        # See if OK was pressed
        if result:
            pass