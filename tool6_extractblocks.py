from qgis.core import Qgis, QgsProject, QgsLayerTreeLayer, QgsVectorLayer, QgsFeatureRequest, QgsExpression, QgsFeature

import os

from .utils import utils


FIELDS_MANDATORY = ["extractblocks_folder", "extract_table", "extract_polygon_layer", "extract_lines_layer", "extract_3d_layer"]
RELTABLE_ID = "rel_"
POLYGON_LAYER_ID = "_2D"
LINE_LAYER_ID = "_lin2D"
THREED_LAYER_ID = "_3D"
STR_BLOQUES = "BL"
STR_BASES_NAGATIVAS = "BN"
STR_ESTRUCTURAS = "ES"


class ExtractblocksTool():
    def __init__(self, parent):
        """Constructor."""

        self.parent = parent

        self.utils = utils(self.parent)

        self.preselect_layer()


    def preselect_layer(self):
        """ preselect reltable """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer):
                layer_name = layer.layer().name()
                layer = QgsProject.instance().mapLayersByName(layer_name)[0]
                layer.setSubsetString("")

                if RELTABLE_ID in layer_name:
                    self.parent.dlg.extract_table.setLayer(layer)
                elif POLYGON_LAYER_ID in layer_name:
                    self.parent.dlg.extract_polygon_layer.setLayer(layer)
                elif LINE_LAYER_ID in layer_name:
                    self.parent.dlg.extract_lines_layer.setLayer(layer)
                elif THREED_LAYER_ID in layer_name:
                    self.parent.dlg.extract_3d_layer.setLayer(layer)


    def process_extractforms(self):
        """ process relations """

        if not self.utils.check_mandatory_fields(FIELDS_MANDATORY):
            return False

        extract_table = self.parent.dlg.extract_table.currentText()
        extract_layer = QgsProject.instance().mapLayersByName(extract_table)[0]
        restricted_uas = self.parent.dlg.extract_restrict.text().split(",")

        #print(restricted_uas)

        feature_count = len(list(extract_layer.getFeatures()))
        self.progress = self.utils.initProgressBar("Process extractioin...", feature_count)

        for feature in extract_layer.getFeatures():
            attributes = feature.attributes()
            
            id_bloque = feature[1]
            ua = feature[2]
            position = feature[3]

            if len(restricted_uas) == 0 or restricted_uas[0].strip() == "" or ua in restricted_uas:
                self.add_features(id_bloque, ua, position)
                self.progress.setValue(self.progress.value() + 1)

        self.parent.dlg.messageBar.clearWidgets()
        self.parent.dlg.messageBar.pushMessage(f"Forms extracted and written to working directory", level=Qgis.Success)


    def add_features(self, id_bloque, ua, position):
        """ write combination to layer files """

        combination = f"_{ua}_{position}"
        combination_all = f"_{ua}_ALL"
        layer_name_2d = "BL2D" + combination
        layer_name_2d_all = "BL2D" + combination_all
        layer_name_lines = "Lines" + combination
        layer_name_lines_all = "Lines" + combination_all
        layer_name_3d = "BL3D" + combination
        layer_name_3d_all = "BL3D" + combination_all

        self.add_feature(id_bloque, layer_name_2d, "Polygon", ua)
        self.add_feature(id_bloque, layer_name_2d_all, "Polygon", ua)
        self.add_feature(id_bloque, layer_name_lines, "LineString", ua)
        self.add_feature(id_bloque, layer_name_lines_all, "LineString", ua)
        self.add_feature(id_bloque, layer_name_3d, "PolygonZ", ua)
        self.add_feature(id_bloque, layer_name_3d_all, "PolygonZ", ua)


    def add_feature(self, id_bloque, layer_name, geom_type, ua):
        """ write combination to layer files """

        layer = self.get_layer(layer_name, geom_type, ua)
        feature = self.get_feature(id_bloque, geom_type)

        if layer and feature:
            self.write_feature(feature, layer, id_bloque)


    def get_layer(self, layer_name, geom_type, ua):
        """ get layer from project """

        dir_name = f"{self.get_form_type()}_{ua}"

        layer_path = os.path.join(self.parent.dlg.extractblocks_folder.filePath(), dir_name, layer_name + ".gpkg")

        if os.path.exists(layer_path):
            layer = QgsVectorLayer(layer_path, layer_name, 'ogr')
            if not layer.isValid():
                print(f"Layer failed to load: {layer_path}")
                return

            if not self.has_layer(layer_name) and self.parent.dlg.extract_check_layers.isChecked():
                QgsProject.instance().addMapLayer(layer)
        else:
            layer = self.create_layer(layer_name, geom_type, dir_name)

        return layer


    def create_layer(self, layer_name, geom_type, dir_name):
        """ create empty polygon 2d layer file """

        layer_uri = f"{geom_type}?crs=epsg:25831&field=id_bloque:integer"
        layer = QgsVectorLayer(layer_uri, layer_name, "memory")

        if self.parent.dlg.extract_check_layers.isChecked():
            QgsProject.instance().addMapLayer(layer)

        path = self.parent.dlg.extractblocks_folder.filePath()
        path = os.path.join(path, dir_name)
        self.utils.make_permanent(layer, path)

        return layer


    def get_feature(self, id_bloque, geom_type):
        """ get feature by id_bloque """

        layer_name = None
        if geom_type == "Polygon":
            layer_name = self.parent.dlg.extract_polygon_layer.currentText()
        elif geom_type == "LineString":
            layer_name = self.parent.dlg.extract_lines_layer.currentText()
        elif geom_type == "PolygonZ":
            layer_name = self.parent.dlg.extract_3d_layer.currentText()
 
        if not layer_name:
            return None

        layer = QgsProject.instance().mapLayersByName(layer_name)[0]
        request = QgsFeatureRequest(QgsExpression(f"\"id_bloque\" = {id_bloque}"))
        features = list(layer.getFeatures(request))

        if len(features) == 0:
            return None

        return features[0]


    def write_feature(self, origin_feature, layer, id_bloque):
        """ write feature to layer """

        feature = QgsFeature()
        feature.setGeometry(origin_feature.geometry())
        feature.setAttributes([None, id_bloque])

        layer.startEditing()
        layer.addFeature(feature)
        layer.commitChanges()


    def has_layer(self, name):
        """ check if layer already is in layer tree """

        for layer in QgsProject.instance().layerTreeRoot().children():
            if isinstance(layer, QgsLayerTreeLayer) and name == layer.layer().name():
                return True 

        return False


    def get_form_type(self):
        """ check if bloque, base negativa or estructura """

        # for now only check with 2d types
        polygon_layer_name = self.parent.dlg.extract_polygon_layer.currentLayer().name()

        if STR_BLOQUES in polygon_layer_name:
            return STR_BLOQUES
        elif STR_BASES_NAGATIVAS in polygon_layer_name:
            return STR_BASES_NAGATIVAS
        elif STR_ESTRUCTURAS in polygon_layer_name:
            return STR_ESTRUCTURAS
        else:
            return STR_BLOQUES