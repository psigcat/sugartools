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


FIELDS_MANDATORY = ["sections_db", "sections_table_db", "sections_x_db", "sections_y_db", "sections_z_db", "workspace_db", "symbology_db", "sections_thickness_db"]
COMBO_SELECT = "(Select)"
COORDX_IDS = ["coord_x"]
COORDY_IDS = ["coord_y"]
COORDZ_IDS = ["coord_z"]
MATERIA_SELECTED = ['muestras', 'sedimento', 'no coordenad']

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
        self.point_or_block()
        self.fill_symbology()
        self.fill_symbology_overlay()

        self.databases = self.utils.read_database_config()
        self.utils.fill_db_combo(self.parent.dlg.sections_db, self.databases)

        self.parent.dlg.sections_db.currentIndexChanged.connect(self.load_tables)
        self.parent.dlg.sections_table_db.currentIndexChanged.connect(self.load_columns)
        self.parent.dlg.filter_expr_btn_db.clicked.connect(self.open_expr_builder)


    def ortho_or_oblique(self):
        """ select type of distribution """

        isOrthogonal = self.parent.dlg.radioDistOrthogonal_db.isChecked()
        self.parent.dlg.radioPoints_db.setChecked(True)
        self.parent.dlg.radioBlocks_db.setEnabled(isOrthogonal)
        self.parent.dlg.radioPointsBlocks_db.setEnabled(isOrthogonal)
        self.parent.dlg.anchorpoint_distance_db.setVisible(not isOrthogonal)
        self.parent.dlg.anchorpoint_distance_db_label.setVisible(not isOrthogonal)
        self.parent.dlg.anchorpoint_angle_db.setVisible(not isOrthogonal)
        self.parent.dlg.anchorpoint_angle_db_label.setVisible(not isOrthogonal)


    def point_or_block(self):
        """ select type of symbology """

        self.parent.dlg.groupBoxPoints_db.setVisible(self.parent.dlg.radioPoints_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked())
        self.parent.dlg.groupBoxBlocks_db.setVisible(self.parent.dlg.radioBlocks_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked())

        self.parent.dlg.labelSymbology_db.setVisible(self.parent.dlg.radioPoints_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked())
        self.parent.dlg.symbology_db.setVisible(self.parent.dlg.radioPoints_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked())


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


    def load_tables(self):
        """ Fetch tables for the selected database and populate combobox """
        
        # Block signals temporarily to prevent recursive loops when clearing
        self.parent.dlg.sections_table_db.blockSignals(True)
        self.parent.dlg.sections_table_db.clear()
        
        # Ensure a valid DB is selected
        if not self.connect_db():
            self.parent.dlg.sections_table_db.blockSignals(False)
            return
            
        # Get the selected database name from the combobox data
        db_key = self.parent.dlg.sections_db.currentData()["value"]
        db_name = self.databases[db_key]["db"]

        # MySQL query to get tables and views
        sql_query = f"""
            SELECT TABLE_NAME 
            FROM information_schema.tables 
            WHERE table_schema = '{db_name}';
        """
        
        # Execute query using get_rows from utils_database.py
        records = self.dblayer_db_obj.get_rows(sql_query)
        
        # Populate the table combobox
        self.parent.dlg.sections_table_db.addItem("Please select a table or view", {"value": None})
        if records:
            for row in records:
                # Safely convert QByteArray to a standard Python string
                table_name = row[0].data().decode('utf-8') if hasattr(row[0], 'data') else str(row[0])
                
                self.parent.dlg.sections_table_db.addItem(table_name, {"value": table_name})
                
        self.parent.dlg.sections_table_db.blockSignals(False)


    def load_columns(self):
        """ Fetch numerical columns for the selected table and populate X, Y, Z combos """
        
        combos = [self.parent.dlg.sections_x_db, self.parent.dlg.sections_y_db, self.parent.dlg.sections_z_db]
        
        # Clear existing items
        for combo in combos:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Please select a column", {"value": None})
            
        # Get selected table
        table_data = self.parent.dlg.sections_table_db.currentData()
        if not table_data or not table_data.get("value"):
            for combo in combos:
                combo.blockSignals(False)
            return
            
        table_name = table_data["value"]
        db_key = self.parent.dlg.sections_db.currentData()["value"]
        db_name = self.databases[db_key]["db"]
        
        # MySQL query to get only numerical columns
        sql_query = f"""
            SELECT COLUMN_NAME 
            FROM information_schema.columns 
            WHERE table_schema = '{db_name}' 
              AND table_name = '{table_name}'
              AND data_type IN (
                  'tinyint', 'smallint', 'mediumint', 'int', 'bigint', 
                  'decimal', 'numeric', 'float', 'double'
              );
        """
        
        # Execute query using get_rows from utils_database.py
        records = self.dblayer_db_obj.get_rows(sql_query)
        
        # Populate the X, Y, and Z comboboxes
        if records:
            for row in records:
                # Safely convert QByteArray to a standard Python string
                col_name = row[0].data().decode('utf-8') if hasattr(row[0], 'data') else str(row[0])
                
                for combo in combos:
                    combo.addItem(col_name, {"value": col_name})
                    
        for combo in combos:
            combo.blockSignals(False)

        self.preselect_coords(self.parent.dlg.sections_x_db, COORDX_IDS)
        self.preselect_coords(self.parent.dlg.sections_y_db, COORDY_IDS)
        self.preselect_coords(self.parent.dlg.sections_z_db, COORDZ_IDS)

        self.get_cmateria_values(table_name)


    def get_cmateria_values(self, table_name):
        """ get all unique values from column nom_cmateria """

        sql_query = f"""
            SELECT distinct(nom_cmateria) 
            FROM {table_name}
            WHERE cod_tnivel = 'UA'
        """
        # AND coord_y < 78200
        
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


    def preselect_coords(self, item, labels):
        """ preselect coordinate dropdowns """

        for i in range(item.count()):
            for label in labels:
                if label == item.itemText(i):
                    item.setCurrentIndex(i)


    def process_sectionsdb(self):
        """ create points and blocks from database """

        db_layer = self.create_dblayer()

        if (self.parent.dlg.radioBlocks_db.isChecked() or self.parent.dlg.radioPointsBlocks_db.isChecked()) and self.parent.dlg.option_polygons_db.isChecked():
            blocks_layer = self.create_blocks(db_layer)


    def create_dblayer(self):
        """ add layer from database """

        # 1. Check mandatory fields
        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        # 2. Make base layer
        table_name = self.parent.dlg.sections_table_db.currentData()["value"]
        vlayer_query = self.create_baselayer(table_name)

        # 3. Points or blocks?
        # if (self.parent.dlg.radioBlocks_db.isChecked() or (self.parent.dlg.radioPointsBlocks_db.isChecked() and file.find(BLOCK_PATTERN) > -1)) and self.parent.dlg.option_polygons_db.isChecked():
        #     new_layer = self.create_blocks(gpkg_layer, prefix, layer_group, file)

        selected_mats = self.get_selected_materials()
        if selected_mats:
            formatted_mats = ", ".join([f"'{m}'" for m in selected_mats])
            vlayer_query += f" AND nom_cmateria NOT IN ({formatted_mats})"

        # 6. Add selected options to query
        if self.parent.dlg.exclude_red_points_db.isChecked():
            vlayer_query += " AND bol_nivelok = true"

        if self.parent.dlg.exclude_duplicated_points_db.isChecked():
            vlayer_query += " AND bol_duplicado = false"

        if self.parent.dlg.exclude_no_coords_db.isChecked():
            vlayer_query += " AND nom_cmateria != 'no coordenad'"

        vlayer_query += ";"

        print(vlayer_query)

        # 7. Create Virtual Layer (URL Encode the query to prevent URI parsing errors)
        query_encoded = urllib.parse.quote(vlayer_query)
        vlayer_uri = f"?crs=epsg:25831&query={query_encoded}"
        
        vlayer = QgsVectorLayer(vlayer_uri, f"{table_name}", "virtual")
        vlayer.setCrs(QgsCoordinateReferenceSystem("EPSG:25831"))

        # 8. Validate and Add to Project
        if not vlayer.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Failed to create virtual layer for {table_name}.", level=Qgis.Critical, duration=5)
            return False

        folder_name = self.get_folder_name(vlayer)
        path = os.path.join(self.parent.dlg.workspace_db.filePath(), folder_name)
        self.utils.save_layer_gpkg(vlayer, path)
        QgsProject.instance().addMapLayer(vlayer, True)
        self.parent.dlg.messageBar.pushMessage(f"Layer {table_name} created successfully.", level=Qgis.Success, duration=5)

        self.slice_layer_by_y(vlayer, folder_name)

        return vlayer


    def create_baselayer(self, table_name):
        """ """

        # 1. Get values from UI
        x_col = self.parent.dlg.sections_x_db.currentData()["value"]
        y_col = self.parent.dlg.sections_y_db.currentData()["value"]
        z_col = self.parent.dlg.sections_z_db.currentData()["value"]
        
        db_key = self.parent.dlg.sections_db.currentData()["value"]
        db_config = self.databases[db_key]
        db_name = db_config["db"]

        # 2. Fetch all columns to build the [all other columns] list
        sql_cols = f"""
            SELECT COLUMN_NAME 
            FROM information_schema.columns 
            WHERE table_schema = '{db_name}' 
              AND table_name = '{table_name}';
        """
        
        records = self.dblayer_db_obj.get_rows(sql_cols)
        
        other_cols = []
        if records:
            for row in records:
                col = row[0].data().decode('utf-8') if hasattr(row[0], 'data') else str(row[0])
                # Skip X, Y, Z to avoid duplication in the SELECT statement
                if col not in [x_col, y_col, z_col]:
                    other_cols.append(f"d.{col}")
                    
        # Join the remaining columns with commas
        other_cols_str = ", ".join(other_cols)
        if other_cols_str:
            other_cols_str = ", " + other_cols_str # Add leading comma for the SQL syntax

        # 3. Create Base Layer and add it to the project silently
        uri = QgsDataSourceUri()
        uri.setConnection(db_config['host'], str(db_config['port']), db_config['db'], db_config['user'], db_config['passwd'])
        uri.setDataSource("", table_name, None) 
        
        base_layer_name = f"{table_name}_base"
        
        # Try the native QGIS MySQL provider first
        base_layer = QgsVectorLayer(uri.uri(), base_layer_name, "mysql")
        
        # Fallback to the standard OGR provider if native fails
        if not base_layer.isValid():
            ogr_uri = f"MySQL:{db_name},host={db_config['host']},port={db_config['port']},user={db_config['user']},password={db_config['passwd']}|layername={table_name}"
            base_layer = QgsVectorLayer(ogr_uri, base_layer_name, "ogr")
            
            if not base_layer.isValid():
                self.parent.dlg.messageBar.pushMessage(f"Failed to connect to base table or view {table_name}.", level=Qgis.Critical, duration=5)
                return False

        QgsProject.instance().addMapLayer(base_layer, False)

        # 5. Construct the Virtual Layer query using the hidden base layer
        vlayer_query = f"""
            SELECT d.{x_col}, d.{y_col}, d.{z_col}{other_cols_str}, 
                   make_point(d.{x_col}, d.{y_col}, d.{z_col}) AS geometry 
            FROM "{base_layer_name}" AS d
            WHERE d.cod_tnivel = 'UA'
        """
        # AND d.coord_y < 78200

        return vlayer_query


    def get_folder_name(self, layer):
        """ build folder name """

        yacimento = "Ortho_RB" # TODO
        thickness = int(self.parent.dlg.sections_thickness_db.value())

        folder_name = f"{yacimento}_{thickness}"

        coord_y = self.parent.dlg.sections_y_db.currentText()
        idx = layer.fields().indexOf(coord_y)
        if idx == -1:
            print(f"Error: Field '{field_name}' not found.")
            return folder_name

        min_val = int(layer.minimumValue(idx))
        max_val = int(layer.maximumValue(idx))

        folder_name += f"_{min_val}_{max_val}"

        return folder_name


    def slice_layer_by_y(self, layer, folder_name):
        """
        Slices a QgsVectorLayer into multiple memory layers based on a Y-coordinate field.
        """

        field_name = self.parent.dlg.sections_y_db.currentText()
        step = self.parent.dlg.sections_thickness_db.value()
        
        # 1. Get field index and min/max values
        idx = layer.fields().indexOf(field_name)
        if idx == -1:
            print(f"Error: Field '{field_name}' not found.")
            return

        min_val = layer.minimumValue(idx)
        max_val = layer.maximumValue(idx)

        if min_val is None or max_val is None:
            print(f"Error: No valid values found in the '{field_name}' field.")
            return

        # Create or find the group in the layer tree
        root = QgsProject.instance().layerTreeRoot()
        group = root.findGroup(folder_name)
        if not group:
            group = root.insertGroup(0, folder_name)

        # Get the geometry type and CRS for the memory layer creation
        wkb_type = QgsWkbTypes.displayString(layer.wkbType()).replace(" ", "")
        crs_authid = layer.crs().authid()

        # 2. Loop by ranges divided by thickness
        # Floor the min_val to the nearest thickness to get clean boundaries
        current_y = math.floor(min_val / step) * step

        while current_y <= max_val:
            print(f"current slot: {current_y}, max: {max_val}")
            next_y = current_y + step

            # Use an expression to filter features within the current slot
            expr = f'"{field_name}" >= {current_y} AND "{field_name}" < {next_y}'
            request = QgsFeatureRequest().setFilterExpression(expr)
            
            # Extract the features that match the slot
            features = list(layer.getFeatures(request))

            # 3. Save the vector layers in memory (only if the slot has features)
            if features:
                layer_name = f"sec_{int(current_y)}_{int(next_y)}"
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

                QgsProject.instance().addMapLayer(mem_layer, False)
                group.addLayer(mem_layer)

                self.apply_symbology(mem_layer, slice_save_path, group)

            current_y = next_y
            
        print(f"Successfully sliced layer into slots of {step}.")


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
        QgsProject.instance().addMapLayer(layer_final, False)

        overlays_group_name = "overlays"
        overlays_group = self.utils.get_layer_group(overlays_group_name, group)
        if not overlays_group:
            overlays_group = self.utils.create_group(overlays_group_name, group)
        overlays_group.insertChildNode(1, QgsLayerTreeLayer(layer_final))

        # save style to gpkg
        self.set_symbology(layer_final, True)
        symbology = self.parent.dlg.symbology_overlay_db.currentText()
        symbology_name = symbology.split(".qml")[0]
        layer_final.saveStyleToDatabase(symbology_name, "", True, "")


    def remove_filtered_features(self, layer_name, overlay, filter_text, path):
        """ remove all features from vector layer which are filtered out """

        layer = QgsVectorLayer(path + f"/{layer_name}.gpkg|layername={layer_name}", layer_name)

        print("remove filtered features for layer", layer.name(), len(list(layer.getFeatures())))

        # get expression
        symbology = self.parent.dlg.symbology_db.currentText()
        if overlay:
            filter_text = self.parent.dlg.filter_expr_db.text()
            symbology = self.parent.dlg.symbology_overlay_db.currentText()

        print("active filter", filter_text)

        # check for expression to delete filtered out features
        if filter_text == "" or symbology == COMBO_SELECT:
            print("no filter to apply, so nothing to delete")
            return layer

        # Use the inverse expression to get filtered-out features
        inverse_expression = f'NOT ({filter_text})'
        print("inverse filter", inverse_expression)
        request = QgsFeatureRequest(QgsExpression(inverse_expression))
        ids_to_delete = [f.id() for f in layer.getFeatures(request)]

        # Delete the features
        if ids_to_delete:
            layer.startEditing()
            layer.deleteFeatures(ids_to_delete)
            print(f"Deleted {len(ids_to_delete)} features.")

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