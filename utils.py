from qgis.core import Qgis, QgsProject, QgsVectorLayer, QgsVectorFileWriter, QgsCoordinateTransform, QgsCoordinateReferenceSystem

import os


class utils:

	def __init__(self, plugin_dir):

		self.plugin_dir = plugin_dir


	def create_group(self, group_name, parent=False):
		""" create layer group """

		if not parent:
			parent = QgsProject.instance().layerTreeRoot()

		group = parent.addGroup(group_name)
		return group


	def make_permanent(self, layer, path):
		""" save temporary layer to gpkg """

		if not os.path.exists(path):
			os.makedirs(path)
		path = os.path.join(path, layer.name() + ".gpkg")
			
		#error = QgsVectorFileWriter.writeAsVectorFormat(layer, path, "UTF-8")

		options = QgsVectorFileWriter.SaveVectorOptions()
		options.driverName = "GPKG"
		options.fileEncoding = "UTF-8"
		options.layerName = layer.name()			
		options.ct = QgsCoordinateTransform(layer.crs(), QgsCoordinateReferenceSystem.fromEpsgId(25831), QgsProject.instance())

		QgsVectorFileWriter.writeAsVectorFormatV3(layer, path, QgsProject.instance().transformContext(), options)

		block_layer = QgsVectorLayer(path, 'Layer geopackage')
		QgsProject.instance().addMapLayer(block_layer, False)

		# change the data source
		layer.setDataSource(path + f'|layername={layer.name()}', layer.name(), 'ogr')
		#layer.setDataProvider(myParams, name, layer type, QgsDataProvider.ProviderOptions())