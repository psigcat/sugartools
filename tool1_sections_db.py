from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QProgressBar, QWidget, QVBoxLayout, QHBoxLayout, QCheckBox, QLabel, QScrollArea
from qgis.gui import QgsExpressionBuilderDialog
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsDataSourceUri, QgsSymbol, QgsMarkerSymbol, QgsSimpleFillSymbolLayer, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsLayerTreeLayer, QgsLayerTreeNode, QgsLayerTreeGroup, QgsExpressionContextUtils, QgsFeatureRequest, QgsExpressionContext, QgsProviderRegistry, QgsFeature, QgsLayout, QgsExpression, QgsWkbTypes, QgsCoordinateReferenceSystem

import math
import os
import processing
import urllib.parse

from .utils import utils
from .utils_database import utils_database


FIELDS_MANDATORY = ["sections_db", "workspace_db", "sections_thickness_db"]
COMBO_SELECT = "(Select)"
COORDX = "coord_x"
COORDY = "coord_y"
COORDZ = "coord_z"
COORDX_NEG = "coord_x_neg"
COORDY_NEG = "coord_y_neg"
MATERIA_SELECTED = ['muestras', 'sedimento', 'no coordenad']
TABLE_NAME = 'view_secciones'
ORTO = "sec_orthogonal"
OBLI = "sec_oblique"

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


class SectionsDbTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.ortho_or_oblique()
        self.points_or_blocks()
        self.fill_symbology()
        self.fill_symbology_overlay()

        self.databases = self.utils.read_database_config()
        self.utils.fill_db_combo(self.parent.dlg.sections_db, self.databases)

        self.parent.dlg.sections_db.currentIndexChanged.connect(self.get_cmateria_values)
        self.parent.dlg.filter_expr_btn_db.clicked.connect(self.open_expr_builder)


    def ortho_or_oblique(self):
        """ select type of distribution """

        isOrthogonal = self.parent.dlg.radioDistOrthogonal_db.isChecked()
        self.parent.dlg.radioPoints_db.setChecked(True)
        self.parent.dlg.radioBlocks_db.setEnabled(isOrthogonal)
        self.parent.dlg.radioPointsBlocks_db.setEnabled(isOrthogonal)
        self.parent.dlg.groupAnchorpoints_db.setVisible(not isOrthogonal)


    def points_or_blocks(self):
        """ select type of symbology """

        paint_points = self.parent.dlg.radioPoints_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked()

        self.parent.dlg.groupBoxPoints_db.setVisible(paint_points)
        self.parent.dlg.groupBoxBlocks_db.setVisible(self.parent.dlg.radioBlocks_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked())

        self.parent.dlg.labelSymbology_db.setVisible(paint_points)
        self.parent.dlg.symbology_db.setVisible(paint_points)


    def fill_symbology(self):
        """ show all symbologies (but starting with levels) in combobox """

        symbology_path = self.parent.utils.get_path_qml()
        self.fill_symbology_files(self.parent.dlg.symbology_db, "levels", symbology_path)


    def fill_symbology_overlay(self):
        """ show all symbologies (but starting with overlay) in combobox """

        symbology_path = self.parent.utils.get_path_qml()
        self.fill_symbology_files(self.parent.dlg.symbology_overlay_db, "overlay", symbology_path)


    def fill_symbology_files(self, widget, filter, symbology_path):
        """ show all symbologies in combobox """

        widget.clear()
        widget.addItem(COMBO_SELECT)

        symbology_files = [f for f in os.listdir(symbology_path) if os.path.isfile(os.path.join(symbology_path, f)) and f.startswith(filter)]
        symbology_files.sort()
        for file in symbology_files:
            #self.parent.dlg.symbologies.addItem(file[:-4])
            widget.addItem(file)


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(self.parent.iface.activeLayer())
        if expr_dialog.exec():
            self.parent.dlg.filter_expr_db.setText(expr_dialog.expressionText())


    def connect_db(self):
        """ get blocks from database """

        if not self.parent.dlg.sections_db.currentData()["value"]:
            self.parent.dlg.messageBar.pushMessage("Please select a database connection", level=Qgis.Warning, duration=3)
            return False

        # connect to database
        db = self.databases[self.parent.dlg.sections_db.currentData()["value"]]
        self.dblayer_db_obj = utils_database(self.parent.plugin_dir, db)
        self.dblayer_db = self.dblayer_db_obj.open_database()

        return True


    def get_cmateria_values(self):
        """ get all unique values from column nom_cmateria """

        # Ensure a valid DB is selected
        if not self.connect_db():
            return

        sql_query = f"""
            SELECT distinct(nom_cmateria) 
            FROM {TABLE_NAME}
        """
        #    WHERE coord_y < 78200
        
        # Execute query using get_rows from utils_database.py
        records = self.dblayer_db_obj.get_rows(sql_query)
        
        unique_materials = []
        
        if records:
            for row in records:
                unique_materials.append(str(row[0]))

        self.populate_cmateria(unique_materials)


    def populate_cmateria(self, items_list: list):
        """ populate list of nom_cmateria """

        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        
        for item_text in items_list:
            row_layout = QHBoxLayout()
            
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(5)
            
            checkbox = QCheckBox()
            label = QLabel(item_text)
            
            if item_text in MATERIA_SELECTED:
                checkbox.setChecked(True)
                
            row_layout.addWidget(checkbox)
            row_layout.addWidget(label)
            row_layout.addStretch()

            container_layout.addLayout(row_layout)
            
        container_layout.addStretch()
        
        self.parent.dlg.nom_cmateria_list.setWidget(container_widget)
        self.parent.dlg.nom_cmateria_list.setWidgetResizable(True)


    def get_selected_materials(self):
        """ Extract text of selected items from the QScrollArea """

        selected_materials = []
        container_widget = self.parent.dlg.nom_cmateria_list.widget()
        if not container_widget:
            return selected_materials
            
        container_layout = container_widget.layout()
        if not container_layout:
            return selected_materials
            
        # Iterate through the QVBoxLayout items
        for i in range(container_layout.count()):
            row_item = container_layout.itemAt(i)
            row_layout = row_item.layout()
            
            # If it's a layout (your QHBoxLayout), extract the widgets
            if row_layout:
                checkbox = row_layout.itemAt(0).widget()
                label = row_layout.itemAt(1).widget()
                
                # Check if they exist and if the checkbox is checked
                if checkbox and label and checkbox.isChecked():
                    selected_materials.append(label.text())
                    
        return selected_materials


    def process_dblayer(self):
        """ process layer options """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        self.progress, self.progress_msg = self.utils.initProgressBar("Import sections from database...", 100)

        if self.parent.dlg.radioPoints_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked():

            # points
            if not self.utils.check_mandatory_fields(["symbology_db"]):
                return False

            layer_type = 'UA'
            where_query = f" cod_tnivel = '{layer_type}'"

            selected_mats = self.get_selected_materials()
            if selected_mats:
                formatted_mats = ", ".join([f"'{m}'" for m in selected_mats])
                where_query += f" AND nom_cmateria NOT IN ({formatted_mats})"

            # Add selected options to query
            if self.parent.dlg.exclude_red_points_db.isChecked():
                where_query += " AND bol_nivelok = true"

            if self.parent.dlg.exclude_duplicated_points_db.isChecked():
                where_query += " AND bol_duplicado = false"

            self.import_dblayer(layer_type, where_query)

        if self.parent.dlg.radioBlocks_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked():

            # blocks
            layer_type = 'FO'
            where_query = f" cod_tnivel = '{layer_type}'"
            where_query += f" AND nom_nivel LIKE '%bl' AND dib_pieza is not NULL "

            self.import_dblayer(layer_type, where_query)

        self.progress.setValue(100)
        self.parent.dlg.messageBar.popWidget(self.progress_msg)


    def import_dblayer(self, layer_type, where_query):
        """ import layers from database """

        where_query = self.limit_projection(where_query)

        # Make base layer and section layers
        if not self.create_baselayer(where_query, layer_type):
            return False

        if not self.create_planta(where_query, layer_type):
            return False

        if self.parent.dlg.section_ew_db.isChecked():
            vlayer_ew = self.create_dblayer("EW", where_query, layer_type)

            if vlayer_ew:
                self.slice_layer("EW", vlayer_ew, layer_type)

        if self.parent.dlg.section_ns_db.isChecked():
            vlayer_ns = self.create_dblayer("NS", where_query, layer_type)

            if vlayer_ns:
                self.slice_layer("NS", vlayer_ns, layer_type)

        if self.parent.dlg.section_ew_inverted_db.isChecked():
            vlayer_ew_neg = self.create_dblayer("EW", where_query, layer_type)

            if vlayer_ew_neg:
                self.slice_layer("EW_NEG", vlayer_ew_neg, layer_type)

        if self.parent.dlg.section_ns_inverted_db.isChecked():
            vlayer_ns_neg = self.create_dblayer("NS", where_query, layer_type)

            if vlayer_ns_neg:
                self.slice_layer("NS_NEG", vlayer_ns_neg, layer_type)


    def limit_projection(self, where_query):
        """ add limits to where query """

        xmin = self.parent.dlg.limit_xmin_db.value()
        xmax = self.parent.dlg.limit_xmax_db.value()
        ymin = self.parent.dlg.limit_ymin_db.value()
        ymax = self.parent.dlg.limit_ymax_db.value()
        
        if xmin != 0 and xmax != 0 and ymin != 0 and ymax != 0:
            where_query += f" AND {COORDX} >= {xmin} AND {COORDX} <= {xmax} AND {COORDY} >= {ymin} AND {COORDY} <= {ymax}"

        return where_query


    def create_baselayer(self, where_query, layer_type):
        """ load database layer as memory layer and return whole query """

        # 1. Get values from UI
        db_key = self.parent.dlg.sections_db.currentData()["value"]
        db_config = self.databases[db_key]
        db_name = db_config["db"]
        base_layer_name = f"{TABLE_NAME}_{layer_type}"

        self.progress.setValue(self.progress.value() + 1)
        
        # 2. Build a robust OGR connection string for MySQL
        ogr_uri = (
            f"MySQL:{db_name},host={db_config['host']},port={db_config['port']},"
            f"user={db_config['user']},password={db_config['passwd']},tables={TABLE_NAME}"
            f"|layername={TABLE_NAME}"
        )
        
        # 3. Use the OGR provider directly (highly stable on Windows)
        base_layer = QgsVectorLayer(ogr_uri, base_layer_name, "ogr")
        
        # Fallback to native MySQL provider if OGR fails (rare)
        if not base_layer.isValid():
            uri = QgsDataSourceUri()
            uri.setConnection(db_config['host'], str(db_config['port']), db_config['db'], db_config['user'], db_config['passwd'])
            uri.setDataSource("", TABLE_NAME, "")
            
            base_layer = QgsVectorLayer(uri.uri(), base_layer_name, "mysql")
            
            if not base_layer.isValid():
                self.parent.dlg.messageBar.pushMessage(f"Failed to connect to base table or view '{TABLE_NAME}' on {ogr_uri}.", level=Qgis.Critical, duration=5)
                return False

        # Apply the subset string
        success = base_layer.setSubsetString(where_query)
        
        if not success:
            self.parent.dlg.messageBar.pushMessage(f"Could not apply provider filter to {TABLE_NAME}.", level=Qgis.Warning, duration=5)

        if len(list(base_layer.getFeatures())) == 0:
            self.parent.dlg.messageBar.pushMessage(f"No features in base layer loaded from {TABLE_NAME}. Maybe problems with your MySQL database?", level=Qgis.Warning, duration=5)
            return False

        QgsProject.instance().addMapLayer(base_layer, False)

        self.progress.setValue(self.progress.value() + 1)

        return True


    def create_planta(self, where_query, layer_type):
        """ create planta with all points and x/y projection """

        vlayer_query = f"""
            SELECT *, make_point({COORDX}, {COORDY}) AS geometry 
            FROM "{TABLE_NAME}_{layer_type}" 
            WHERE {where_query};
        """

        # Create Virtual Layer
        query_encoded = urllib.parse.quote(vlayer_query)
        vlayer_uri = f"?crs=epsg:25831&query={query_encoded}"

        vlayer = QgsVectorLayer(vlayer_uri, f"Planta {layer_type}", "virtual")
        vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:25831"))

        # Validate and Add to Project
        if not vlayer.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Failed to create virtual layer for Planta.", level=Qgis.Critical, duration=5)
            return False

        QgsProject.instance().addMapLayer(vlayer, True)
        self.utils.save_layer_gpkg(vlayer, self.parent.dlg.workspace_db.filePath())
        self.parent.dlg.messageBar.pushMessage(f"Planta created successfully.", level=Qgis.Success, duration=5)

        self.progress.setValue(self.progress.value() + 1)

        return True


    def get_folder_name(self, layer, section_type):
        """ build folder name """

        yacimento = "Ortho_RB" # TODO dynamic yacimiento name
        thickness = int(self.parent.dlg.sections_thickness_db.value())
        folder_name = f"{yacimento}_{thickness}_{section_type}"

        min_val, max_val, field_name = self.get_min_max_val(layer, section_type)
        folder_name += f"_{min_val}_{max_val}"

        return folder_name


    def get_min_max_val(self, layer, section_type):
        """ return field min and max values """

        if section_type == 'EW':
            field_name = COORDY
        elif section_type == 'NS':
            field_name = COORDX
        elif section_type == 'EW_NEG':
            field_name = COORDY_NEG
        elif section_type == 'NS_NEG':
            field_name = COORDX_NEG
        else:
            return 0, 0, ""

        idx = layer.fields().indexOf(field_name)
        if idx == -1:
            print(f"Error: Field '{field_name}' not found.")
            return False

        min_val = int(layer.minimumValue(idx))
        max_val = int(layer.maximumValue(idx))

        return min_val, max_val, field_name


    def create_dblayer(self, section_type, where_query, layer_type):
        """ create virtual layer using the hidden base layer and add to project """

        if section_type == 'EW':
            coord1 = COORDX
        elif section_type == 'NS':
            coord1 = COORDY
        elif section_type == 'EW_NEG':
            coord1 = COORDX_NEG
        elif section_type == 'NS_NEG':
            coord1 = COORDY_NEG

        vlayer_query = f"""
            SELECT *, make_point({coord1}, {COORDZ}) AS geometry 
            FROM "{TABLE_NAME}_{layer_type}" 
            WHERE {where_query};
        """

        if layer_type == 'UA':
            layer_type_name = "Pnt"
        elif layer_type == 'FO':
            layer_type_name = "Bl"
        else:
            layer_type_name = ""

        # Create Virtual Layer
        query_encoded = urllib.parse.quote(vlayer_query)
        vlayer_uri = f"?crs=epsg:25831&query={query_encoded}"

        vlayer = QgsVectorLayer(vlayer_uri, f"{TABLE_NAME}_{section_type}_{layer_type_name}", "virtual")
        vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:25831"))

        # Validate and Add to Project
        if not vlayer.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Failed to create virtual layer for {TABLE_NAME}.", level=Qgis.Critical, duration=5)
            return False

        # TESTING: add and show view_secciones
        # QgsProject.instance().addMapLayer(vlayer, True)
        # folder_name = self.get_folder_name(vlayer, section_type)
        # path = os.path.join(self.parent.dlg.workspace_db.filePath(), folder_name)
        # self.utils.save_layer_gpkg(vlayer, path)
        # self.parent.dlg.messageBar.pushMessage(f"Layer {TABLE_NAME} created successfully.", level=Qgis.Success, duration=5)

        self.progress.setValue(self.progress.value() + 1)

        return vlayer


    def slice_layer(self, section_type, layer, layer_type):
        """
        Slices a QgsVectorLayer into multiple memory layers based on a X- or Y-coordinate field.
        """

        step = self.parent.dlg.sections_thickness_db.value()
        min_val, max_val, coord_field = self.get_min_max_val(layer, section_type)

        if layer_type == 'UA':
            layer_type_name = "Pnt"
        elif layer_type == 'FO':
            layer_type_name = "Bl"
        else:
            layer_type_name = ""

        # Create or find the group in the layer tree
        root = QgsProject.instance().layerTreeRoot()
        folder_name = self.get_folder_name(layer, section_type)
        group_name = section_type + " cross-sections"
        group = root.findGroup(group_name)
        if not group:
            group = root.insertGroup(0, group_name)
            group.setExpanded(False)

        # Get the geometry type and CRS for the memory layer creation
        wkb_type = QgsWkbTypes.displayString(layer.wkbType()).replace(" ", "")
        crs_authid = layer.crs().authid()

        # 2. Loop by ranges divided by thickness
        # Floor the min_val to the nearest thickness to get clean boundaries
        current_val = math.floor(min_val / step) * step

        while current_val <= max_val:
            self.progress.setValue(self.progress.value() + 1)

            #print(f"current slot: {current_val}, max: {max_val}")
            next_val = current_val + step

            # Use an expression to filter features within the current slot
            expr = f'"{coord_field}" >= {current_val} AND "{coord_field}" < {next_val}'
            request = QgsFeatureRequest().setFilterExpression(expr)
            
            # Extract the features that match the slot
            features = list(layer.getFeatures(request))

            # 3. Save the vector layers in memory (only if the slot has features)
            if features:
                layer_name = f"{layer_type_name}_{section_type}_{int(current_val)}_{int(next_val)}"
                uri = f"{wkb_type}?crs={crs_authid}"
                
                mem_layer = QgsVectorLayer(uri, layer_name, "memory")
                mem_layer_data = mem_layer.dataProvider()

                mem_layer_data.addAttributes(layer.fields())
                mem_layer.updateFields()

                mem_layer_data.addFeatures(features)
                mem_layer.updateExtents()

                workspace_path = self.parent.dlg.workspace_db.filePath()
                slice_save_path = os.path.join(workspace_path, folder_name)
                self.utils.save_layer_gpkg(mem_layer, slice_save_path)

                # 3. Save points and/or blocks layers to file
                if layer_type == 'UA':
                    print("create points", mem_layer.name())
                    QgsProject.instance().addMapLayer(mem_layer, False)
                    group.addLayer(mem_layer)
                    self.apply_symbology(mem_layer, slice_save_path, group)

                elif layer_type == 'FO':
                    self.create_blocks(mem_layer, group, slice_save_path)

            current_val = next_val
            
        self.parent.dlg.messageBar.pushMessage(f"Successfully sliced {section_type} into slots of {step}.", level=Qgis.Success, duration=5)


    def apply_symbology(self, layer, path, group):
        """ filter active layer by query """

        self.set_symbology(layer)

        # save style to gpkg
        symbology = self.parent.dlg.symbology_db.currentText()
        symbology_name = symbology.split(".qml")[0]
        layer.saveStyleToDatabase(symbology_name, "", True, "")

        if self.parent.dlg.filter_expr_db.text() != "" and self.parent.dlg.symbology_overlay_db.currentText() != COMBO_SELECT:
            self.make_overlay(layer, path, group)


    def make_overlay(self, layer, path, group):
        """ duplicate existing layer in layer group """

        print("make overlay for layer", layer.name())

        layer_clone = QgsVectorLayer(layer.source(), layer.name() + "_overlay")
        layer_clone.setName(layer.name() + "_overlay")
        self.utils.save_layer_gpkg(layer_clone, path, False)

        layer_final = self.remove_filtered_features(layer_clone.name(), True, self.parent.dlg.filter_expr_db.text(), path)

        if len(list(layer_final.getFeatures())) > 0:
            QgsProject.instance().addMapLayer(layer_final, False)
            group.addLayer(layer_final)

            # save style to gpkg
            self.set_symbology(layer_final, True)
            symbology = self.parent.dlg.symbology_overlay_db.currentText()
            symbology_name = symbology.split(".qml")[0]
            layer_final.saveStyleToDatabase(symbology_name, "", True, "")

            # TODO remove layer_clone.gpkg


    def remove_filtered_features(self, layer_name, overlay, filter_text, path):
        """ remove all features from vector layer which are filtered out """

        layer = QgsVectorLayer(path + f"/{layer_name}.gpkg|layername={layer_name}", layer_name)

        #print("remove filtered features for layer", layer.name(), len(list(layer.getFeatures())))

        # get expression
        symbology = self.parent.dlg.symbology_db.currentText()
        if overlay:
            filter_text = self.parent.dlg.filter_expr_db.text()
            symbology = self.parent.dlg.symbology_overlay_db.currentText()

        #print("active filter", filter_text)

        # check for expression to delete filtered out features
        if filter_text == "" or symbology == COMBO_SELECT:
            print("no filter to apply, so nothing to delete")
            return layer

        # Use the inverse expression to get filtered-out features
        inverse_expression = f'NOT ({filter_text})'
        #print("inverse filter", inverse_expression)
        request = QgsFeatureRequest(QgsExpression(inverse_expression))
        ids_to_delete = [f.id() for f in layer.getFeatures(request)]

        # Delete the features
        if ids_to_delete:
            layer.startEditing()
            layer.deleteFeatures(ids_to_delete)
            #print(f"Deleted {len(ids_to_delete)} features.")

        # Commit the changes
        if not layer.commitChanges():
            print("Failed to commit changes:", layer.name(), layer.commitErrors())

        layer.setSubsetString("")

        return layer


    def set_symbology(self, layer, overlay=False):
        """ set symbology from selected qml file """

        symbology = self.parent.dlg.symbology_db.currentText()
        if overlay:
            symbology = self.parent.dlg.symbology_overlay_db.currentText()

        symbology_path = os.path.join(self.parent.utils.get_path_qml(), symbology)
        layer.loadNamedStyle(symbology_path)
        layer.triggerRepaint()


    def create_blocks(self, layer, group, path):
        """ create blocks from point layer """

        self.progress.setValue(self.progress.value() + 1)

        print("create blocks", layer.name())

        # paint polygons as points
        if self.parent.dlg.option_points_db.isChecked():
            QgsProject.instance().addMapLayer(layer, False)
            group.addLayer(layer)
            return

        field = 'dib_pieza'
        #if self.parent.dlg.radioPointsBlocks_db.isChecked():
        #    field = 'nom_nivel'

        # apply geoprocess convex hull
        params = {
            'INPUT': layer.source(),
            'FIELD': field,
            'TYPE': 3,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }

        result = processing.run("qgis:minimumboundinggeometry", params)

        if len(list(result['OUTPUT'].getFeatures())) == 0:
            return

        QgsProject.instance().addMapLayer(result['OUTPUT'], False)
        group.addChildNode(QgsLayerTreeLayer(result['OUTPUT']))
        result['OUTPUT'].setName(f"{layer.name()}_bl")

        # apply style
        symbology_path = os.path.join(self.parent.utils.get_path_qml(), "blocks.qml")
        result['OUTPUT'].loadNamedStyle(symbology_path)
        result['OUTPUT'].triggerRepaint()

        self.utils.save_layer_gpkg(result['OUTPUT'], path)

        self.progress.setValue(self.progress.value() + 1)