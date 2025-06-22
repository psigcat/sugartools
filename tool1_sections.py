from qgis.PyQt.QtCore import Qt
from qgis.PyQt.QtWidgets import QProgressBar
from qgis.gui import QgsExpressionBuilderDialog
from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsSymbol, QgsMarkerSymbol, QgsSimpleFillSymbolLayer, QgsRendererCategory, QgsCategorizedSymbolRenderer, QgsLayerTreeLayer, QgsLayerTreeNode, QgsLayerTreeGroup, QgsExpressionContextUtils, QgsFeatureRequest, QgsExpressionContext, QgsExpressionContextUtils, QgsProviderRegistry, QgsFeature, QgsLayout, QgsExpression

import os
import processing

from .utils import utils


COMBO_SELECT = "(Select)"
SYMBOLOGY_DIR = "qml"
SECTION_EW_PATTERN = "_EW"
SECTION_NS_PATTERN = "_NS"
INVERTED_STR = " inverted"
POINT_PATTERN = "_UA"
BLOCK_PATTERN = "_FO"
LAYOUT_MAP_ITEM = "Mapa principal"
CSV_PARAMS = '?maxFields=20000&detectTypes=yes&crs=EPSG:25831&spatialIndex=no&subsetIndex=no&watchFile=no'
CSV_PARAMS_COORDS_EW = '&xField=X&yField=Z'
CSV_PARAMS_COORDS_NS = '&xField=Y&yField=Z'
CSV_PARAMS_COORDS_EW_NEG = '&xField=X_NEG&yField=Z'
CSV_PARAMS_COORDS_NS_NEG = '&xField=Y_NEG&yField=Z'
SECTIONS_LAYOUT_NAME = 'sections'

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


class SectionsTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent
        self.databases = {}

        self.utils = utils(self.parent)


    def get_two_section_layers(self):
        """ recursevly parse whole layer tree and return first two layers of section """

        layer_names = []
        for group in QgsProject.instance().layerTreeRoot().children():
            for subgroup in group.children():
                layer_name = self.get_section_layer(subgroup)
                #print(layer_name)
                if layer_name:
                    layer_names.append(layer_name)
            break

        #print(layer_names)
        return layer_names


    def get_section_layer(self, node):
        """ recursevly parse whole layer tree and return first two layers of section """

        # if isinstance(node, QgsLayerTreeLayer):
        #     if ((self.parent.dlg.section_ew.isChecked() and node.name().find(SECTION_EW_PATTERN) > 0) or (self.parent.dlg.section_ns.isChecked() and node.name().find(SECTION_NS_PATTERN) > 0)) and not node.layer().isTemporary():
                
        #         return node.name()

        if isinstance(node, QgsLayerTreeGroup):
            for child in node.children():
                #return self.get_section_layer(child)
                return node.name()


    def point_or_block(self):
        """ select type of symbology """

        self.parent.dlg.groupBoxPoints.setVisible(self.parent.dlg.radioPoints.isChecked() or self.parent.dlg.radioPointsBlocks.isChecked())
        self.parent.dlg.groupBoxBlocks.setVisible(self.parent.dlg.radioBlocks.isChecked() or self.parent.dlg.radioPointsBlocks.isChecked())

        self.parent.dlg.labelSymbology.setVisible(self.parent.dlg.radioPoints.isChecked() or self.parent.dlg.radioPointsBlocks.isChecked())
        self.parent.dlg.symbology.setVisible(self.parent.dlg.radioPoints.isChecked() or self.parent.dlg.radioPointsBlocks.isChecked())


    def preset_fields(self):
        """ show all symbologies (but starting with overlay) in combobox """

        self.parent.dlg.symbology_folder.setFilePath(os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR))
        self.parent.dlg.symbology_overlay_folder.setFilePath(os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR))


    def fill_symbology(self):
        """ show all symbologies (but starting with levels) in combobox """

        symbology_path = self.parent.dlg.symbology_folder.filePath()
        self.fill_symbology_files(self.parent.dlg.symbology, "levels", symbology_path)


    def fill_symbology_overlay(self):
        """ show all symbologies (but starting with overlay) in combobox """

        symbology_path = self.parent.dlg.symbology_overlay_folder.filePath()
        self.fill_symbology_files(self.parent.dlg.symbology_overlay, "overlay", symbology_path)


    def fill_symbology_files(self, widget, filter, symbology_path):
        """ show all symbologies in combobox """

        widget.clear()
        widget.addItem(COMBO_SELECT)

        symbology_files = [f for f in os.listdir(symbology_path) if os.path.isfile(os.path.join(symbology_path, f)) and f.startswith(filter)]
        symbology_files.sort()
        for file in symbology_files:
            #self.parent.dlg.symbologies.addItem(file[:-4])
            widget.addItem(file)


    # def fill_layer(self):
    #     """ show all layers in combobox """

    #     self.parent.dlg.layer.clear()
    #     self.parent.dlg.layer.addItem(COMBO_SELECT)
    #     for group in QgsProject.instance().layerTreeRoot().children():
    #         #self.add_layer_tree_item(self.getLayerTree(group))
    #         self.getLayerTree(group)

    #     # select active layer
    #     if self.parent.iface.activeLayer():
    #         self.parent.dlg.layer.setCurrentText(self.parent.iface.activeLayer().name())
    #     else:
    #         self.parent.dlg.layer.setCurrentIndex(1)


    # def getLayerTree(self, node):
    #     if isinstance(node, QgsLayerTreeGroup):
    #         for child in node.children():
    #             self.getLayerTree(child)
    #     elif isinstance(node, QgsLayerTreeNode):
    #         self.parent.dlg.layer.addItem(node.name())


    # def fill_layout(self):
    #     """ show all layouts in combobox """

    #     self.parent.dlg.layout.clear()
    #     #self.parent.dlg.layout.addItem(COMBO_SELECT)
    #     layout_manager = QgsProject.instance().layoutManager()
    #     for layout in layout_manager.printLayouts():
    #         self.parent.dlg.layout.addItem(layout.name())


    def load_file(self, file, group, csv_params_coords, prefix, inverted=False):
        """ load csv file as vector layer """

        # print("import file", file)

        inverted_str = ""
        if inverted:
            inverted_str = INVERTED_STR

        delimiter = ""
        if self.parent.dlg.delimiter.currentText() == "Tabulator (TSV)":
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
            self.parent.dlg.messageBar.pushMessage(f"Unknown prefix, has to be EW or NS but is '{prefix}'", level=Qgis.Warning)
            return

        layer_name = prefix + "_" + layer_name
        csv_layer = QgsVectorLayer(uri, "Pnt" + layer_name + inverted_str, "delimitedtext")

        # save to geopackage
        path = os.path.join(self.secciones_path, "sections")
        self.utils.save_layer_gpkg(csv_layer, path)

        gpkg_layer = QgsVectorLayer(os.path.join(path, csv_layer.name() + ".gpkg"), csv_layer.name())
        QgsProject.instance().addMapLayer(gpkg_layer, False)

        # check if group already does exist
        layer_group = self.get_layer_group("Sec" + layer_name, group)
        if not layer_group:
            layer_group = self.utils.create_group("Sec" + layer_name, group)
        # insert as first element in group to assure that it does appear before blocks
        layer_group.insertChildNode(0, QgsLayerTreeLayer(gpkg_layer))

        if file.find(POINT_PATTERN) > -1:
            self.filter_layer_points(gpkg_layer, layer_group)
            self.set_symbology(gpkg_layer)

            # save style to gpkg
            symbology = self.parent.dlg.symbology.currentText()
            symbology_name = symbology.split(".qml")[0]
            gpkg_layer.saveStyleToDatabase(symbology_name, "", True, "")

        if (self.parent.dlg.radioBlocks.isChecked() or (self.parent.dlg.radioPointsBlocks.isChecked() and file.find(BLOCK_PATTERN) > -1)) and self.parent.dlg.option_polygons.isChecked():
            new_layer = self.create_blocks(gpkg_layer, prefix, layer_group, file)
            self.write_layer_vars(new_layer)
        else:
            self.write_layer_vars(gpkg_layer)
            # !!! only for first layer !!!
            # self.write_layout_yacimiento(gpkg_layer)

        self.progress.setValue(self.progress.value() + 1)


    def get_layer_group(self, layer_group_name, section_group):
        """ get layer group inside another group, false if it doesn't exist """

        for group in section_group.findGroups():
            if group.name() == layer_group_name:
                return group
        return False


    def set_symbology(self, layer, overlay=False):
        """ set symbology from selected qml file """

        symbology = self.parent.dlg.symbology.currentText()
        if overlay:
            symbology = self.parent.dlg.symbology_overlay.currentText()

        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, symbology)
        layer.loadNamedStyle(symbology_path)
        layer.triggerRepaint()


    def get_file_list(self, pattern):
        """ get all files containing pattern from workspace """

        file_list = []
        for root_dir, dirs, files in os.walk(self.secciones_path):
            for folder in dirs:
                if self.parent.dlg.radioPoints.isChecked() and folder.find(POINT_PATTERN) != -1 or self.parent.dlg.radioBlocks.isChecked() and folder.find(BLOCK_PATTERN) != -1 or self.parent.dlg.radioPointsBlocks.isChecked() and folder.find(POINT_PATTERN) != -1 or self.parent.dlg.radioPointsBlocks.isChecked() and folder.find(BLOCK_PATTERN) != -1:
                    file_list += self.return_file_list(folder, pattern)
        return file_list


    def return_file_list(self, folder, pattern):
        """ Build file list for given folder and pattern. """

        points_blocks_folder = os.path.join(self.secciones_path, folder)
        return [os.path.join(self.secciones_path, folder, f) for f in os.listdir(points_blocks_folder) if os.path.isfile(os.path.join(points_blocks_folder, f)) and f.find(pattern) > 0]


    def import_files(self):
        """ import all files from selected workspace """

        # 0. crear grupo
        # 1. recorrer todos los ficheros del workspace
        # 2. si contienen _EW asigno coordinadas X=X, Y=Z
        # 3. si contienen _NS asigno coordinadas X=Y, Y=Z
        # importar como CSV

        label = "Points "
        if self.parent.dlg.radioBlocks.isChecked():
            label = "Blocks "
        elif self.parent.dlg.radioPointsBlocks.isChecked():
            label = "Points and Blocks "

        success = False
        self.secciones_path = self.parent.dlg.workspace.filePath()

        file_count = 0
        # !!! hace falta limitarlo al directoria usado !!!
        for root_dir, cur_dir, files in os.walk(self.secciones_path):
            file_count += len(files)
        self.progress = self.utils.initProgressBar("Import sections...", file_count)
        
        if self.parent.dlg.section_ew.isChecked():
            file_list = self.get_file_list(SECTION_EW_PATTERN)
            if file_list:
                success = True
                group = self.utils.create_group(label + SECTION_EW_PATTERN[1:] + " cross-sections")
                for file in file_list:
                    self.load_file(file, group, CSV_PARAMS_COORDS_EW, SECTION_EW_PATTERN)

        if self.parent.dlg.section_ns.isChecked():
            file_list = self.get_file_list(SECTION_NS_PATTERN)
            if file_list:
                success = True
                group = self.utils.create_group(label + SECTION_NS_PATTERN[1:] + " cross-sections")
                for file in file_list:
                    self.load_file(file, group, CSV_PARAMS_COORDS_NS, SECTION_NS_PATTERN)

        if self.parent.dlg.section_ew_inverted.isChecked():
            file_list = self.get_file_list(SECTION_EW_PATTERN)
            if file_list:
                success = True
                group = self.utils.create_group(label + SECTION_EW_PATTERN[1:] + " cross-sections")
                for file in file_list:
                    self.load_file(file, group, CSV_PARAMS_COORDS_EW_NEG, SECTION_EW_PATTERN, True)

        if self.parent.dlg.section_ns_inverted.isChecked():
            file_list = self.get_file_list(SECTION_NS_PATTERN)
            if file_list:
                success = True
                group = self.utils.create_group(label + SECTION_NS_PATTERN[1:] + " cross-sections")
                for file in file_list:
                    self.load_file(file, group, CSV_PARAMS_COORDS_NS_NEG, SECTION_NS_PATTERN, True)

        # remove progress bar
        self.parent.dlg.messageBar.clearWidgets()

        if not success:
            self.parent.dlg.messageBar.pushMessage(f"No files imported, workspace has to have UA folder with points data or FO folder with blocks data.", level=Qgis.Warning)
            return

        # select first layers
        first_layer = self.get_first_layer(QgsProject.instance().layerTreeRoot())
        if first_layer:
            self.parent.iface.setActiveLayer(first_layer)
        self.utils.select_layer()

        #self.fill_layer()
        #self.fill_layout()

        # close dialog
        self.parent.dlg.close()


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

        #print("layers", layers)

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

        #print("thickness", diffx)

        return diffx/10


    def write_layout_vars(self, layout):
        """ write variables to composition """

        # if self.parent.dlg.layer.currentText() == COMBO_SELECT or self.parent.dlg.layer.currentText() == "":
        #     return False
        # layer = QgsProject.instance().mapLayersByName(self.parent.dlg.layer.currentText())[0]
        layer = self.parent.iface.activeLayer()

        # var_name = "yacimiento"
        # var = QgsExpressionContextUtils.layerScope(layer).variable("layer_" + var_name)
        # QgsExpressionContextUtils.setLayoutVariable(layout, "layout_" + var_name, var)

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


    def write_layout_yacimiento(self, layout):
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
        print("abr_yacimiento", abr_yacimiento)
        # yacimiento = ""
        # if abr_yacimiento and abr_yacimiento in SITES and len(SITES[abr_yacimiento]) > 0:
        #     yacimiento = SITES[abr_yacimiento][0]
        # #print("yacimiento", yacimiento)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_yacimiento", abr_yacimiento)


    def write_layout_thickness(self, layout):
        """ write variables to layer, for later use in layout """

        section_layers = self.get_two_section_layers()
        thickness = self.get_section_thickness(section_layers)
        QgsExpressionContextUtils.setLayoutVariable(layout, "layout_thickness", thickness)


    def write_layer_vars(self, layer):
        """ write variables to layer, for later use in layout """

        # layer name
        section = ""
        layer_name = layer.name()
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_layer", layer_name)

        # section
        if layer_name.find(SECTION_EW_PATTERN) > 0:
            if layer_name.find(INVERTED_STR):
                section = self.parent.dlg.section_ew.text()
            else:
                section = self.parent.dlg.section_ew_inverted.text()
        elif layer_name.find(SECTION_NS_PATTERN) > 0:
            if layer_name.find(INVERTED_STR):
                section = self.parent.dlg.section_ns.text()
            else:
                section = self.parent.dlg.section_ns_inverted.text()
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
        # section_layers = self.get_two_section_layers()
        # thickness = self.get_section_thickness(section_layers)
        # QgsExpressionContextUtils.setLayerVariable(layer, "layer_thickness", thickness)

        # blocks
        blocks = ""
        if self.parent.dlg.option_polygons.isChecked():
            blocks = "Blocks"
        QgsExpressionContextUtils.setLayerVariable(layer, "layer_blocks", blocks)


    def create_blocks(self, layer, prefix, layer_group, file):
        """ create blocks from point layer """

        print("create block", layer.name(), file)

        uri_components = QgsProviderRegistry.instance().decodeUri(layer.dataProvider().name(), layer.publicSource());

        field = 'dib_pieza'
        if self.parent.dlg.radioPointsBlocks.isChecked() and layer.name().find(BLOCK_PATTERN) > -1:
            field = 'nom_nivel'

        # apply geoprocess convex hull
        params = {
            'INPUT': layer.source(),
            #'INPUT': uri_components['path'],
            'FIELD': field,
            'TYPE': 3,
            'OUTPUT': 'TEMPORARY_OUTPUT'
        }

        result = processing.run("qgis:minimumboundinggeometry", params)

        QgsProject.instance().addMapLayer(result['OUTPUT'], False)
        # insert as last element in group
        layer_group.addChildNode(QgsLayerTreeLayer(result['OUTPUT']))

        #processing.runAndLoadResults("native:buffer", params)

        # rename block
        layer_name_parts = layer.name().split(prefix)
        layer_name = layer_name_parts[0] + prefix + "_bl" + layer_name_parts[1]
        result['OUTPUT'].setName(layer_name)

        # apply style
        symbology_path = os.path.join(self.parent.plugin_dir, SYMBOLOGY_DIR, "blocks.qml")
        result['OUTPUT'].loadNamedStyle(symbology_path)
        result['OUTPUT'].triggerRepaint()

        path = os.path.join(self.secciones_path, "sections")
        self.utils.save_layer_gpkg(result['OUTPUT'], path)

        # delete point layer
        if self.parent.dlg.option_polygons.isChecked(): #and self.parent.dlg.radioPointsBlocks.isChecked() and layer.name().find(BLOCK_PATTERN) > -1:
            QgsProject.instance().removeMapLayer(layer)

        return result['OUTPUT']


    def filter_layer_points(self, layer, group):
        """ filter active layer by query and selected options """

        #print("filter", layer.name())

        expr = ""
        # filter_expr = self.parent.dlg.filter_expr.text()
        # if filter_expr != "":
        #     expr = f'NOT ({filter_expr})'
        
        if self.parent.dlg.exclude_red_points.isChecked():
            if expr != "":
                expr += " AND "
            expr = "bol_nivelok = 'true'"

        if self.parent.dlg.exclude_duplicated_points.isChecked():
            if expr != "":
                expr += " AND "
            expr += "bol_duplicado = 'false'"

        if self.parent.dlg.exclude_no_coords.isChecked():
            if expr != "":
                expr += " AND "
            expr += "nom_cmateria != 'no coordenad'"
        
        layer.setSubsetString(expr)

        if self.parent.dlg.filter_expr.text() != "" and self.parent.dlg.symbology_overlay.currentText() != COMBO_SELECT:
            self.duplicate_layer(layer, group)


    def duplicate_layer(self, layer, group):
        """ duplicate existing layer in layer group """

        layer_clone = QgsVectorLayer(layer.source(), layer.name() + "_overlay")
        layer_clone.setName(layer.name() + "_overlay")
        path = os.path.join(self.secciones_path, "sections")
        self.utils.save_layer_gpkg(layer_clone, path, False)

        layer_final = self.remove_filtered_features(layer_clone.name())
        QgsProject.instance().addMapLayer(layer_final, False)
        # insert after points, but before blocks
        group.insertChildNode(1, QgsLayerTreeLayer(layer_final))

        # save style to gpkg
        self.set_symbology(layer_final, True)
        symbology = self.parent.dlg.symbology_overlay.currentText()
        symbology_name = symbology.split(".qml")[0]
        layer_final.saveStyleToDatabase(symbology_name, "", True, "")


    def remove_filtered_features(self, layer_name):
        """ remove all features from vector layer which are filtered out """

        path = os.path.join(self.secciones_path, "sections")
        layer = QgsVectorLayer(path + f"/{layer_name}.gpkg|layername={layer_name}", layer_name)

        # get expression
        filter_text = self.parent.dlg.filter_expr.text()
        symbology_overlay = self.parent.dlg.symbology_overlay.currentText()

        # check for expression to delete filtered out features
        if filter_text == "" or symbology_overlay == COMBO_SELECT:
            print("no filter to apply, so nothing to delete")
            return layer

        # Use the inverse expression to get filtered-out features
        inverse_expression = f'NOT ({filter_text})'
        request = QgsFeatureRequest(QgsExpression(inverse_expression))
        ids_to_delete = [f.id() for f in layer.getFeatures(request)]

        # Delete the features
        if ids_to_delete:
            layer.startEditing()
            layer.deleteFeatures(ids_to_delete)
            #print(f"Deleted {len(ids_to_delete)} features.")

        # Commit the changes
        if not layer.commitChanges():
            print("Failed to commit changes:", layer.commitErrors())

        layer.setSubsetString("")

        return layer


    # def load_layout(self, active_tab):
    #     """ only show selected layer and load into layout """

    #     if not self.utils.check_mandatory(active_tab):
    #         self.self.parent.iface.messageBar().pushMessage(f"You have to import data and a layout first.", level=Qgis.Warning, duration=3)
    #         return False

    #     # open layout
    #     layout_manager = QgsProject.instance().layoutManager()
    #     layout = layout_manager.layoutByName(self.parent.dlg.layout.currentText())
    #     self.parent.iface.openLayoutDesigner(layout)

    #     # close dialog
    #     self.parent.dlg.close()


    def onLayoutLoaded(self):
        """ set layout vars when layout designer is opened """

        print("onLayoutLoaded")

        layout_manager = QgsProject.instance().layoutManager()
        layout = layout_manager.layoutByName(SECTIONS_LAYOUT_NAME)
        #layout.refreshed.connect(lambda:self.write_layer_vars(self.parent.iface.activeLayer()))
        self.write_layout_vars(layout)
        self.write_layout_thickness(layout)
        #self.write_layout_yacimiento(layout)

        # set map extent to match main canvas extent
        if layout != None:
            map_item = layout.itemById(LAYOUT_MAP_ITEM)
            map_canvas = self.parent.iface.mapCanvas()
            map_item.zoomToExtent(map_canvas.extent())


    def open_expr_builder(self):
        """ open QGIS Query Builder"""

        expr_dialog = QgsExpressionBuilderDialog(self.parent.iface.activeLayer())
        if expr_dialog.exec_():
            self.parent.dlg.filter_expr.setText(expr_dialog.expressionText())


    def set_and_zoom_active_layer(self):
        """ set active layer and zoom to it """

        # if self.parent.dlg.layer.currentText() == COMBO_SELECT or self.parent.dlg.layer.currentText() == "":
        #     return False

        self.utils.hide_all_layers_but_selected()

        #active_layer = QgsProject.instance().mapLayersByName(self.parent.dlg.layer.currentText())[0]
        active_layer = self.parent.iface.activeLayer()
        self.parent.iface.setActiveLayer(active_layer)
        self.parent.iface.zoomToActiveLayer()


    def get_first_layer(self, node):
        """ set first layer from layer tree active """

        if isinstance(node, QgsLayerTreeLayer):
            return node.layer()
        elif hasattr(node, 'children'):
            for child in node.children():
                result = self.get_first_layer(child)
                if result:
                    return result
        return None