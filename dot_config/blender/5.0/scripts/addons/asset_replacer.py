bl_info = {
	"name": "Interactive Asset Replacer",
	"author": "azephynight",
	"version": (1, 2),
	"blender": (3, 0, 0),
	"location": "View3D > Sidebar > Asset Replacer",
	"description": "Interactively replace materials, material node groups, and geometry node groups from a source blend file.",
	"category": "Import-Export",
}

import bpy
import os
import json
import difflib

ORIGINAL_IDENTIFIER = "[Old]" # Used to indicate a data block from the source .blend.

def fuzzy_match_replace(props):
	# Collect old assets by type, removing [Old] prefix for matching
	old_materials = {
		mat.name[len(ORIGINAL_IDENTIFIER)+1:]: mat.name
		for mat in bpy.data.materials if mat.name.startswith(ORIGINAL_IDENTIFIER)
	}
	old_shader_node_groups = {
		ng.name[len(ORIGINAL_IDENTIFIER)+1:]: ng.name
		for ng in bpy.data.node_groups if ng.name.startswith(ORIGINAL_IDENTIFIER) and ng.type != 'GEOMETRY'
	}
	old_geometry_node_groups = {
		ng.name[len(ORIGINAL_IDENTIFIER)+1:]: ng.name
		for ng in bpy.data.node_groups if ng.name.startswith(ORIGINAL_IDENTIFIER) and ng.type == 'GEOMETRY'
	}

	# Helper to find best match
	def find_best_match(name, candidates):
		if not candidates:
			return None
		matches = difflib.get_close_matches(name, candidates.keys(), n=1, cutoff=0.6)
		if matches:
			return candidates[matches[0]]
		return None

	# Assign to_be_replaced using fuzzy matching
	for m in props.mappings:
		if m.to_be_replaced:
			continue  # skip if already assigned

		if m.asset_type == "Material":
			match = find_best_match(m.source_name, old_materials)
		elif m.asset_type == "ShaderNodeTree":
			match = find_best_match(m.source_name, old_shader_node_groups)
		elif m.asset_type == "GeometryNodeTree":
			match = find_best_match(m.source_name, old_geometry_node_groups)
		else:
			match = None

		if match:
			m.to_be_replaced = match

class MappingItem(bpy.types.PropertyGroup):
	asset_type: bpy.props.StringProperty()
	source_name: bpy.props.StringProperty()
	to_be_replaced: bpy.props.StringProperty()

class ReplacerProperties(bpy.types.PropertyGroup):
	source_blend: bpy.props.StringProperty(
		name="Source .blend",
		description="Blend file whose assets you want to replace",
		subtype='FILE_PATH'
	)
	mappings: bpy.props.CollectionProperty(type=MappingItem)

class OT_FillDefaults(bpy.types.Operator):
	bl_idname = "asset_replacer.fill_defaults"
	bl_label = "AutoChoose"

	def execute(self, context):
		# Use fuzzy matching to try to find some defaults.
		fuzzy_match_replace(context.scene.asset_replacer_props)

class OT_LoadSourceAssets(bpy.types.Operator):
	bl_idname = "asset_replacer.load_source_assets"
	bl_label = "Load Source Assets"

	def execute(self, context):
		props = context.scene.asset_replacer_props

		source_path = bpy.path.abspath(props.source_blend)
		if not os.path.isfile(source_path):
			self.report({'ERROR'}, "Invalid source blend file")
			return {'CANCELLED'}

		props.mappings.clear()

		# Load datablocks directly into this file
		# Link all source data to the current file. Store the source data into mappings with source field set as the data's linked equivalent
		with bpy.data.libraries.load(source_path, link=True) as (data_from, data_to):
			data_to.materials = data_from.materials
			data_to.node_groups = data_from.node_groups

		# Store references to the new (appended) assets
		for mat in bpy.data.materials:
			if mat.library:  # new assets
				item = props.mappings.add()
				item.asset_type = "Material"
				item.source_name = mat.name
			else:
				# rename old ones
				mat.name = f"{ORIGINAL_IDENTIFIER} {mat.name}"

		for ng in bpy.data.node_groups:
			if ng.library:  # new assets
				asset_type = "GeometryNodeTree" if ng.type == 'GEOMETRY' else "ShaderNodeTree"
				item = props.mappings.add()
				item.asset_type = asset_type
				item.source_name = ng.name
			else:
				# rename old ones
				ng.name = f"{ORIGINAL_IDENTIFIER} {ng.name}"

		self.report({'INFO'}, f"Appended {len(props.mappings)} assets from source blend.")
		return {'FINISHED'}


class OT_ReplaceAssets(bpy.types.Operator):
	bl_idname = "asset_replacer.replace_assets"
	bl_label = "Replace Assets"

	def execute(self, context):
		props = context.scene.asset_replacer_props
		replaced_count = 0

		# Resolve lookup for all types
		for m in props.mappings:
			if not m.to_be_replaced:
				continue

			if m.asset_type == "Material":
				source = bpy.data.materials.get(m.source_name)
				target = bpy.data.materials.get(m.to_be_replaced)
			elif m.asset_type == "ShaderNodeTree":
				source = bpy.data.node_groups.get(m.source_name)
				target = bpy.data.node_groups.get(m.to_be_replaced)
			elif m.asset_type == "GeometryNodeTree":
				source = bpy.data.node_groups.get(m.source_name)
				target = bpy.data.node_groups.get(m.to_be_replaced)
			else:
				continue

			if source and target:
				try:
					target.user_remap(source)
					bpy.data.batch_remove([target])
					replaced_count += 1
				except Exception as e:
					self.report({'WARNING'}, f"Remap failed for {m.source_name}: {str(e)}")

		self.report({'INFO'}, f"Replaced {replaced_count} assets using remap().")
		return {'FINISHED'}

class OT_ExportMapping(bpy.types.Operator):
	bl_idname = "asset_replacer.export_mapping"
	bl_label = "Export Mapping"

	filepath: bpy.props.StringProperty(subtype="FILE_PATH")

	def execute(self, context):
		props = context.scene.asset_replacer_props
		data = [
			{
				"asset_type": m.asset_type,
				"source": m.source_name,
				"replacement": m.to_be_replaced
			}
			for m in props.mappings
		]
		with open(bpy.path.abspath(self.filepath), "w", encoding="utf-8") as f:
			json.dump(data, f, indent=2)

		self.report({'INFO'}, "Mapping exported.")
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

class OT_ImportMapping(bpy.types.Operator):
	bl_idname = "asset_replacer.import_mapping"
	bl_label = "Import Mapping"

	filepath: bpy.props.StringProperty(subtype="FILE_PATH")

	def execute(self, context):
		props = context.scene.asset_replacer_props
		if not os.path.isfile(bpy.path.abspath(self.filepath)):
			self.report({'ERROR'}, "File not found")
			return {'CANCELLED'}
		with open(bpy.path.abspath(self.filepath), "r", encoding="utf-8") as f:
			data = json.load(f)

		props.mappings.clear()
		for entry in data:
			item = props.mappings.add()
			item.asset_type = entry["asset_type"]
			item.source_name = entry["source"]
			item.to_be_replaced = entry["replacement"]

		self.report({'INFO'}, "Mapping imported.")
		return {'FINISHED'}

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

class PT_AssetReplacerPanel(bpy.types.Panel):
	bl_label = "Interactive Asset Replacer"
	bl_idname = "VIEW3D_PT_asset_replacer"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'Asset Replacer'

	def draw(self, context):
		layout = self.layout
		props = context.scene.asset_replacer_props

		layout.operator("asset_replacer.fill_defaults",icon="PLAY")
		layout.prop(props, "source_blend")
		layout.operator("asset_replacer.load_source_assets", icon='FILE_REFRESH')

		if props.mappings:
			box = layout.box()
			box.label(text="Mappings:")

			for m in props.mappings:
				row = box.row()
				row.label(text=f"{m.source_name} replaces: ")
				if m.asset_type == "Material":
					row.prop_search(m, "to_be_replaced", bpy.data, "materials", text="")
				elif m.asset_type == "GeometryNodeTree":
					row.prop_search(m, "to_be_replaced", bpy.data, "node_groups", text="")
				elif m.asset_type == "ShaderNodeTree":
					row.prop_search(m, "to_be_replaced", bpy.data, "node_groups", text="")

			layout.operator("asset_replacer.replace_assets", icon='CHECKMARK')
			row = layout.row()
			row.operator("asset_replacer.export_mapping", icon='EXPORT')
			row.operator("asset_replacer.import_mapping", icon='IMPORT')

classes = (
	OT_FillDefaults,
	MappingItem,
	ReplacerProperties,
	OT_LoadSourceAssets,
	OT_ReplaceAssets,
	OT_ExportMapping,
	OT_ImportMapping,
	PT_AssetReplacerPanel,
)

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Scene.asset_replacer_props = bpy.props.PointerProperty(type=ReplacerProperties)

def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del bpy.types.Scene.asset_replacer_props

if __name__ == "__main__":
	register()