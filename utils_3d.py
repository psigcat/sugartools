from qgis.core import Qgis, QgsProject, QgsGeometry, QgsVectorLayer, QgsField, QgsFeature, QgsFeatureRequest, QgsWkbTypes, QgsCoordinateReferenceSystem, QgsLayerTreeLayer
from qgis.PyQt.QtCore import QVariant

import numpy as np
from scipy.spatial import ConvexHull
import trimesh
import os


class utils_3d:

	def __init__(self, parent):

		self.parent = parent


	def create_polygon_3d(self, blocks2d_layer, points_layer, path, group=None):
		""" create polygon 3d and visualize """

		# create 3d layer 
		polygon_layer_uri = "MultiPolygonZ?crs=epsg:25831&field=dib_pieza:string(10)"
		polygon_layer = QgsVectorLayer(polygon_layer_uri, blocks2d_layer.name(), "memory")
		polygon_layer.setCrs(QgsCoordinateReferenceSystem("EPSG:25831"))
		QgsProject.instance().addMapLayer(polygon_layer, group==None)
		if group:
			group.addChildNode(QgsLayerTreeLayer(polygon_layer))

		#i = 0
		for block2d in blocks2d_layer.getFeatures():
			progress = self.parent.sectionsdb_tool.progress
			progress.setValue(progress.value() + 1)

			dib_pieza = block2d["dib_pieza"]
			points = self.get_points_3d(points_layer, dib_pieza)
			polygon_geom = self.create_3d_from_points(points)
			# if blocks2d_layer.name().startswith("Bl_EW_"):
			# 	print(i, block2d["dib_pieza"], blocks2d_layer.name())
			# 	print(len(points), polygon_geom)
			if polygon_geom:
				self.append_polygons_to_layer(polygon_layer, polygon_geom, dib_pieza)
			#i += 1

		if polygon_layer.featureCount() > 0:
			self.apply_blocks_style(polygon_layer)
			self.parent.utils.save_layer_gpkg(polygon_layer, path)


	def get_points_3d(self, points_layer, filter_field):
		""" get all points from PointZ vector layer """

		points = []
		# Define the acceptable WKB types for points
		point_types = [QgsWkbTypes.Type.Point, QgsWkbTypes.Type.PointZ, QgsWkbTypes.Type.MultiPoint, QgsWkbTypes.Type.MultiPointZ]

		expression = f'"dib_pieza"  = {filter_field}'
		request = QgsFeatureRequest().setFilterExpression(expression)

		for feature in points_layer.getFeatures(request):
			geom = feature.geometry()
			wkb_type = geom.wkbType()
			
			# 1. Skip the feature if it's not a point or multipoint type
			if wkb_type not in point_types:
				# print(f"Skipping non-point geometry type: {QgsWkbTypes.displayString(wkb_type)}")
				continue

			# 2. Handle MultiPoint/MultiPointZ features
			if geom.isMultipart():
				# Safe call to asMultiPoint() because we checked the type above
				for pt in geom.asMultiPoint():
					# Check for 3D capability using pt.is3D()
					if pt.is3D():
						points.append((pt.x(), pt.y(), pt.z()))
			# 3. Handle single Point/PointZ features
			else:
				pt = geom.constGet()
				# Ensure the point is 3D before extracting coordinates
				if pt.is3D():
					points.append((pt.x(), pt.y(), pt.z()))

		return points


	def create_3d_from_points(self, points):
		""" create 3d polygon from points """

		if not points or len(points) < 4:
			#self.parent.dlg.messageBar.pushMessage(f"A 3D convex hull requires at least 4 unique points.", level=Qgis.Critical, duration=3)
			return False

		points_array = np.array(points)
		hull = ConvexHull(points_array)

		# GeometryCollection Z WKT construction
		polygon_components = [] # List to hold the WKT for each component: '((ring))'

		# Iterate through hull simplices (triangular faces)
		for simplex in hull.simplices:
			ring_points_wkt = []
			for i in simplex:
				x, y, z = points_array[i]
				ring_points_wkt.append(f"{x} {y} {z}") 

			# Close the ring
			ring_points_wkt.append(ring_points_wkt[0])

			# Component format for MultiPolygon Z is ((ring))
			component_wkt = f"(({', '.join(ring_points_wkt)}))"
			polygon_components.append(component_wkt)

		# 3. Combine components into the final WKT
		# WKT format: MULTIPOLYGON Z (((r1)), ((r2)), ...)
		merged_wkt = f"MULTIPOLYGON Z ({', '.join(polygon_components)})"

		# Parse the final WKT string
		merged_geom = QgsGeometry.fromWkt(merged_wkt)

		if not merged_geom or merged_geom.isEmpty():
			self.parent.dlg.messageBar.pushMessage(f"CRITICAL ERROR: Failed to parse GEOMETRYCOLLECTION Z WKT.", level=Qgis.Critical, duration=3)
			return False

		return merged_geom


	def append_polygons_to_layer(self, threed_layer, polygons_geom, dib_pieza):
		""" append polygon geometries to target polygon 3d layer """

		# Append to Target Layer Provider
		provider = threed_layer.dataProvider()
		provider.addAttributes([QgsField("SHAPE_volume", QVariant.Double, "", 10, 3)])
		threed_layer.updateFields()

		feature = QgsFeature(threed_layer.fields())
		feature.setGeometry(polygons_geom) 
		calculated_volume = self.parent.utils.calculate_volume_with_trimesh(polygons_geom)
		feature.setAttributes([dib_pieza, calculated_volume])
		threed_layer.addFeature(feature)

		threed_layer.startEditing()
		success = provider.addFeatures([feature])

		if success:
			threed_layer.commitChanges()
			# self.parent.dlg.messageBar.pushMessage(f"SUCCESS: Feature successfully appended to GeoPackage layer '{threed_layer.name()}' via data provider.", level=Qgis.Success, duration=3)
			threed_layer.triggerRepaint()
			return True
		else:
			threed_layer.rollBack()
			self.parent.dlg.messageBar.pushMessage(f"FAILURE: Provider failed to add feature. The GeoPackage rejected the geometry during the edit commit.", level=Qgis.Critical, duration=3)
			return False


	def apply_blocks_style(self, layer):
		"""Apply style to blocks layer."""
		symbology_path = os.path.join(self.parent.utils.get_path_qml(), "blocks.qml")
		layer.loadNamedStyle(symbology_path)
		layer.triggerRepaint()