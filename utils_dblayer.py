from qgis.core import Qgis, QgsPoint, QgsVectorLayer, QgsProject, QgsDataSourceUri

import os
import urllib.parse

from .utils_database import utils_database
from .utils import utils


FIELDS_MANDATORY = ["db_layer_db", "db_layer_table", "db_layer_x", "db_layer_y", "db_layer_z"]
COORDX_IDS = ["coord_x"]
COORDY_IDS = ["coord_y"]
COORDZ_IDS = ["coord_z"]


class DbLayerTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}

        self.utils = utils(self.parent)


    def setup(self):
        """ load initial parameters """

        self.databases = self.utils.read_database_config()
        self.utils.fill_db_combo(self.parent.dlg.db_layer_db, self.databases)

        self.parent.dlg.db_layer_db.currentIndexChanged.connect(self.load_tables)
        self.parent.dlg.db_layer_table.currentIndexChanged.connect(self.load_columns)
        self.parent.dlg.db_layer_btn.clicked.connect(self.process_dblayer)


    def connect_db(self):
        """ get blocks from database """

        if not self.parent.dlg.db_layer_db.currentData()["value"]:
            self.parent.dlg.messageBar.pushMessage("Please select a database connection", level=Qgis.Warning, duration=3)
            return False

        # connect to database
        db = self.databases[self.parent.dlg.db_layer_db.currentData()["value"]]
        self.dblayer_db_obj = utils_database(self.parent.plugin_dir, db)
        self.dblayer_db = self.dblayer_db_obj.open_database()

        return True


    def load_tables(self):
        """ Fetch tables for the selected database and populate combobox """
        
        # Block signals temporarily to prevent recursive loops when clearing
        self.parent.dlg.db_layer_table.blockSignals(True)
        self.parent.dlg.db_layer_table.clear()
        
        # Ensure a valid DB is selected
        if not self.connect_db():
            self.parent.dlg.db_layer_table.blockSignals(False)
            return
            
        # Get the selected database name from the combobox data
        db_key = self.parent.dlg.db_layer_db.currentData()["value"]
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
        self.parent.dlg.db_layer_table.addItem("Please select a table or view", {"value": None})
        if records:
            for row in records:
                # Safely convert QByteArray to a standard Python string
                table_name = row[0].data().decode('utf-8') if hasattr(row[0], 'data') else str(row[0])
                
                self.parent.dlg.db_layer_table.addItem(table_name, {"value": table_name})
                
        self.parent.dlg.db_layer_table.blockSignals(False)


    def load_columns(self):
        """ Fetch numerical columns for the selected table and populate X, Y, Z combos """
        
        combos = [self.parent.dlg.db_layer_x, self.parent.dlg.db_layer_y, self.parent.dlg.db_layer_z]
        
        # Clear existing items
        for combo in combos:
            combo.blockSignals(True)
            combo.clear()
            combo.addItem("Please select a column", {"value": None})
            
        # Get selected table
        table_data = self.parent.dlg.db_layer_table.currentData()
        if not table_data or not table_data.get("value"):
            for combo in combos:
                combo.blockSignals(False)
            return
            
        table_name = table_data["value"]
        db_key = self.parent.dlg.db_layer_db.currentData()["value"]
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

        self.preselect_coords(self.parent.dlg.db_layer_x, COORDX_IDS)
        self.preselect_coords(self.parent.dlg.db_layer_y, COORDY_IDS)
        self.preselect_coords(self.parent.dlg.db_layer_z, COORDZ_IDS)


    def preselect_coords(self, item, labels):
        """ preselect coordinate dropdowns """

        for i in range(item.count()):
            for label in labels:
                if label == item.itemText(i):
                    item.setCurrentIndex(i)


    def process_dblayer(self):
        """ add layer from database """

        # 1. Check mandatory fields
        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        # 2. Get values from UI
        table_name = self.parent.dlg.db_layer_table.currentData()["value"]
        x_col = self.parent.dlg.db_layer_x.currentData()["value"]
        y_col = self.parent.dlg.db_layer_y.currentData()["value"]
        z_col = self.parent.dlg.db_layer_z.currentData()["value"]
        
        db_key = self.parent.dlg.db_layer_db.currentData()["value"]
        db_config = self.databases[db_key]
        db_name = db_config["db"]

        # 3. Fetch all columns to build the [all other columns] list
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

        # 4. Create Base Layer and add it to the project silently
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

        # Add to project but keep it hidden from the TOC/Layers Panel (False argument)
        QgsProject.instance().addMapLayer(base_layer, False)

        # 5. Construct the Virtual Layer query using the hidden base layer
        vlayer_query = f"""
            SELECT d.{x_col}, d.{y_col}, d.{z_col}{other_cols_str}, 
                   make_point(d.{x_col}, d.{y_col}, d.{z_col}) AS geometry 
            FROM "{base_layer_name}" AS d
        """

        # 6. Create Virtual Layer (URL Encode the query to prevent URI parsing errors)
        query_encoded = urllib.parse.quote(vlayer_query)
        vlayer_uri = f"?query={query_encoded}"
        
        vlayer = QgsVectorLayer(vlayer_uri, f"{table_name}_3d_virtual", "virtual")

        # 7. Validate and Add to Project
        if not vlayer.isValid():
            self.parent.dlg.messageBar.pushMessage(f"Failed to create virtual layer for {table_name}.", level=Qgis.Critical, duration=5)
            return False
            
        QgsProject.instance().addMapLayer(vlayer)
        self.parent.dlg.messageBar.pushMessage(f"Virtual layer {table_name}_3d_virtual created successfully.", level=Qgis.Success, duration=5)
        
        return True