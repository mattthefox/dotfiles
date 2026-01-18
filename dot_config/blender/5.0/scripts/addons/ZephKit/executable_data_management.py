import bpy
import re
from bpy.props import StringProperty

"""
--DATA MANAGEMENT--
Data management operators that are meant to help out with performance.
"""

class ZEPHKIT_DATA_WidgetRedundancy(bpy.types.Operator):
	bl_idname = "zephkit.widget_redundancy"
	bl_label = "Delete redundant bone shapes/widgets in a collection."
	bl_description = "Replace duplicated custom shapes with originals and remove redundant ones"

	collection_enum: bpy.props.EnumProperty(
		name="Target Collection",
		description="Select the collection containing the correct bone widgets",
		items=lambda self, context: [(col.name, col.name, "") for col in bpy.data.collections]
	)

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "collection_enum")

	def get_base_name(self, name):
		return re.sub(r"\.\d{3}$", "", name)

	def execute(self, context):
		if not self.collection_enum:
			self.report({'ERROR'}, "No collection selected.")
			return {'CANCELLED'}

		target_collection = bpy.data.collections.get(self.collection_enum)
		if not target_collection:
			self.report({'ERROR'}, f"Collection '{self.collection_enum}' not found.")
			return {'CANCELLED'}

		located_widgets = {}
		redundant_widgets = []

		# Step 1: Collect unique base widgets and mark redundant ones
		for obj in target_collection.objects:
			base_name = self.get_base_name(obj.name)
			if base_name not in located_widgets:
				located_widgets[base_name] = obj
			else:
				redundant_widgets.append(obj.name)

		# Step 2: Replace redundant widgets in all armatures
		for obj in bpy.data.objects:
			if obj.type == 'ARMATURE':
				for bone in obj.pose.bones:
					shape = bone.custom_shape
					if shape and shape.name in redundant_widgets:
						base_name = self.get_base_name(shape.name)
						if base_name in located_widgets:
							bone.custom_shape = located_widgets[base_name]
							print(f"Replaced custom shape for bone '{bone.name}' with '{located_widgets[base_name].name}'")

		# Step 3: Protect mesh data used by located widgets
		protected_mesh_data = {obj.data for obj in located_widgets.values() if obj.type == 'MESH'}

		# Step 4: Delete redundant widgets and their data
		for obj in bpy.data.objects:
			if obj.type == 'MESH' and obj.name in redundant_widgets:
				mesh_data = obj.data

				# Unlink from collections
				for coll in obj.users_collection:
					coll.objects.unlink(obj)

				# Clear users before removal
				obj.user_clear()
				bpy.data.objects.remove(obj)

				# Only delete mesh data if not protected
				if mesh_data not in protected_mesh_data:
					mesh_data.user_clear()
					bpy.data.meshes.remove(mesh_data)
				else:
					print(f"Skipped deleting mesh data (shared): {mesh_data.name}")

		# Step 5: Delete *redundant mesh data blocks* with duplicate base names
		for mesh in list(bpy.data.meshes):
			base_name = self.get_base_name(mesh.name)
			if base_name in [self.get_base_name(obj.name) for obj in located_widgets.values()] and mesh not in protected_mesh_data:
				if mesh.users == 0:
					mesh.user_clear()
					bpy.data.meshes.remove(mesh)
					print(f"Removed redundant mesh data block: {mesh.name}")

		# Step 6: Rename widgets to their base names
		for obj in located_widgets.values():
			base_name = self.get_base_name(obj.name)
			if obj.name != base_name:
				obj.name = base_name

		self.report({'INFO'}, "Widget redundancy resolved.")
		return {'FINISHED'}


# Purge unused data, but works a bit better than Blender's default operator.
class ZEPHKIT_DATA_PurgeUnused(bpy.types.Operator):
	bl_idname = "zephkit.purge_unused"
	bl_label = "Delete unused data"
	bl_description = "Delete unused data"

	def execute(self, context):
		data_blocks_removed = 0
		# Remove unused meshes
		for mesh in bpy.data.meshes:
			if mesh.users == 0 and not mesh.use_fake_user:
				bpy.data.meshes.remove(mesh)
				data_blocks_removed += 1

		# Remove unused materials
		for material in bpy.data.materials:
			if material.users == 0 and not material.use_fake_user:
				bpy.data.materials.remove(material)
				data_blocks_removed += 1

		# Remove unused images
		for image in bpy.data.images:
			if image.users == 0 and image.packed_file is None and not image.use_fake_user:
				bpy.data.images.remove(image)
				data_blocks_removed += 1

		# Remove unused cameras
		for camera in bpy.data.cameras:
			if camera.users == 0 and not camera.use_fake_user:
				bpy.data.cameras.remove(camera)
				data_blocks_removed += 1

		# Remove unused lights
		for light in bpy.data.lights:
			if light.users == 0 and not light.use_fake_user:
				bpy.data.lights.remove(light)
				data_blocks_removed += 1

		# Remove unused actions
		for action in bpy.data.actions:
			if action.users == 0 and not action.use_fake_user:
				bpy.data.actions.remove(action)
				data_blocks_removed += 1

		# Remove unused armatures
		for armature in bpy.data.armatures:
			if armature.users == 0 and not armature.use_fake_user:
				bpy.data.armatures.remove(armature)
				data_blocks_removed += 1

		# Remove unused curves
		for curve in bpy.data.curves:
			if curve.users == 0 and not curve.use_fake_user:
				bpy.data.curves.remove(curve)
				data_blocks_removed += 1
				
		# Remove unused collections
		for collection in bpy.data.collections:
			if collection.users == 0 and not collection.use_fake_user:
				bpy.data.collections.remove(collection)
				data_blocks_removed += 1
		self.report({'INFO'}, f"{data_blocks_removed} unused data blocks purged.")
		return {'FINISHED'}

def is_driver_invalid(driver):
	# Check if the data path is valid
	try:
		driver.id_data.path_resolve(driver.data_path)
	except Exception:
		return True

	# Check all targets in driver variables
	for var in driver.driver.variables:
		for target in var.targets:
			if target.id is None:
				return True
			if target.data_path:
				try:
					target.id.path_resolve(target.data_path)
				except Exception:
					return True
	return False

class ZEPHKIT_DATA_RemoveInvalidDrivers(bpy.types.Operator):
	bl_idname = "zephkit.remove_invalid_drivers"
	bl_label = "Remove invalid drivers"
	bl_description = "Remove invalid drivers"

	def execute(self, context):
		total_removed = 0

		datablocks = (
			list(bpy.data.objects) +
			list(bpy.data.materials) +
			list(bpy.data.meshes) +
			list(bpy.data.lights) +
			list(bpy.data.cameras) +
			list(bpy.data.worlds) +
			list(bpy.data.textures) +
			list(bpy.data.images) +
			list(bpy.data.curves) +
			list(bpy.data.grease_pencils) +
			list(bpy.data.armatures) +
			list(bpy.data.node_groups) +
			list(bpy.data.shape_keys)
		)

		for datablock in datablocks:
			if not hasattr(datablock, "animation_data"):
				continue

			ad = datablock.animation_data
			if ad is None or ad.drivers is None:
				continue

			drivers_to_remove = [fcurve for fcurve in ad.drivers if is_driver_invalid(fcurve)]

			for fcurve in drivers_to_remove:
				ad.drivers.remove(fcurve)
				total_removed += 1

		self.report({'INFO'}, f"Removed {total_removed} invalid drivers.")
		return {'FINISHED'}

class ZEPHKIT_DATA_CustomRemove(bpy.types.Operator):
	bl_idname = "zephkit.custom_remove_data"
	bl_label = "Remove Data by Custom Python Expression"
	bl_description = "Remove any Blender datablock that matches a custom Python condition"
	
	expression: StringProperty(
		name="Python Condition",
		description="Condition as Python code (e.g., 'not d.users')",
		default=""
	)

	def invoke(self, context, event):
		wm = context.window_manager
		return wm.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "expression")

	def execute(self, context):
		total_removed = 0
		errors = 0

		data_blocks = [
			('meshes', bpy.data.meshes),
			('materials', bpy.data.materials),
			('images', bpy.data.images),
			('textures', bpy.data.textures),
			('actions', bpy.data.actions),
			('node_groups', bpy.data.node_groups),
			('armatures', bpy.data.armatures),
			('objects', bpy.data.objects),
			# Add more as needed
		]

		try:
			for type_name, collection in data_blocks:
				for datablock in list(collection):
					d = datablock
					try:
						if eval(self.expression, {"d": d, "type_name": type_name}):
							# Clear users (if allowed)
							if hasattr(d, "user_clear"):
								d.user_clear()

							# Remove fake user flag
							if hasattr(d, "use_fake_user"):
								d.use_fake_user = False

							# Remove from collection
							collection.remove(d)
							total_removed += 1
					except Exception:
						errors += 1
		except Exception as e:
			self.report({'ERROR'}, f"Fatal error: {e}")
			return {'CANCELLED'}

		self.report({'INFO'}, f"Removed {total_removed} items. {errors} errors.")
		return {'FINISHED'}

class ZEPHKIT_DATA_ReplaceKeyword(bpy.types.Operator):
	bl_idname = "zephkit.replace_keyword"
	bl_label = "Replace Keyword in All Datablock Names"
	bl_description = "Find and replace a keyword in the names of all datablocks"

	find_str: StringProperty(
		name="Find",
		description="Text to search for in datablock names",
		default=""
	)
	replace_str: StringProperty(
		name="Replace",
		description="Text to replace the found text with",
		default=""
	)
	case_sensitive: bpy.props.BoolProperty(
		name="Case Sensitive",
		default=False
	)

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "find_str")
		layout.prop(self, "replace_str")
		layout.prop(self, "case_sensitive")

	def execute(self, context):
		if not self.find_str:
			self.report({'ERROR'}, "Find text cannot be empty.")
			return {'CANCELLED'}

		# All datablock collections to search
		data_blocks = [
			bpy.data.objects,
			bpy.data.meshes,
			bpy.data.materials,
			bpy.data.images,
			bpy.data.textures,
			bpy.data.actions,
			bpy.data.node_groups,
			bpy.data.armatures,
			bpy.data.cameras,
			bpy.data.lights,
			bpy.data.worlds,
			bpy.data.curves,
			bpy.data.grease_pencils,
			bpy.data.collections,
			bpy.data.shape_keys,
		]

		total_renamed = 0

		for collection in data_blocks:
			for datablock in collection:
				name_to_search = datablock.name if self.case_sensitive else datablock.name.lower()
				find_text = self.find_str if self.case_sensitive else self.find_str.lower()
				if find_text in name_to_search:
					new_name = datablock.name.replace(self.find_str, self.replace_str) if self.case_sensitive \
						else re.sub(re.escape(find_text), self.replace_str, datablock.name, flags=re.IGNORECASE)
					try:
						datablock.name = new_name
						total_renamed += 1
					except AttributeError as e:
						print(f"Failed to rename {datablock.name} with {e}, skipping ...")

		self.report({'INFO'}, f"Renamed {total_renamed} datablocks.")
		return {'FINISHED'}

class OBJECT_OT_delete_unlocked_shape_keys(bpy.types.Operator):
    """Delete all unlocked shape keys"""
    bl_idname = "object.delete_unlocked_shape_keys"
    bl_label = "Delete Unlocked Shape Keys"
    bl_options = {'UNDO'}

    @classmethod
    def poll(cls, context):
        ob = context.active_object
        return ob and ob.type == 'MESH' and ob.data.shape_keys

    def execute(self, context):
        ob = context.active_object
        keys = ob.data.shape_keys.key_blocks
        
        # Collect indices of unlocked shape keys (except Basis)
        unlocked_indices = [
            i for i, key in enumerate(keys) if not key.lock_shape and key.name != "Basis"
        ]

        # Delete from last to first (to avoid index shifting)
        for i in reversed(unlocked_indices):
            ob.active_shape_key_index = i
            bpy.ops.object.shape_key_remove(all=False)

        return {'FINISHED'}


def menu_func(self, context):
    self.layout.operator(
        OBJECT_OT_delete_unlocked_shape_keys.bl_idname,
        icon="X"
    )

# Registration
modules = [
	OBJECT_OT_delete_unlocked_shape_keys,
	ZEPHKIT_DATA_WidgetRedundancy,
	ZEPHKIT_DATA_RemoveInvalidDrivers,
	ZEPHKIT_DATA_PurgeUnused,
	ZEPHKIT_DATA_CustomRemove,
	ZEPHKIT_DATA_ReplaceKeyword
]

def register():
	for module in modules:
		bpy.utils.register_class(module)
	bpy.types.MESH_MT_shape_key_context_menu.append(menu_func)

def unregister():
	bpy.utils.unregister_class(OBJECT_OT_delete_unlocked_shape_keys)
	for module in reversed(modules):
		bpy.utils.unregister_class(module)
