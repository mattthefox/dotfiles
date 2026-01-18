import bpy

bl_info = {
	"name": "ZephKit Bake",
	"blender": (4, 1, 0),
	"category": "Object",
	"author": "azephynight",
	"version": (1, 1, 0),
	"location": "Properties > Modifiers",
	"description": "Makes GeoNodes baking SIMPLE! Keeps track of the frames that Geonodes are baked on, and allows you to re-bake all at once.",
}

bpy.types.Object.baker_frame = bpy.props.IntProperty(name="Bake Frame", default=-1)

class OBJECT_OT_BakeGeoNodes(bpy.types.Operator):
	"""Bake the selected Geometry Nodes modifier"""
	bl_idname = "object.bake_geometry_nodes"
	bl_label = "Bake Geometry Nodes"
	bl_options = {'REGISTER', 'UNDO'}

	modifier_name: bpy.props.StringProperty()
	change_frame: bpy.props.BoolProperty()

	def execute(self, context):
		obj = context.object
		if obj is None or self.modifier_name not in obj.modifiers:
			self.report({'WARNING'}, "Modifier not found!")
			return {'CANCELLED'}
		
		mod = obj.modifiers[self.modifier_name]
		mod.show_viewport = True
		node_tree = mod.node_group
		
		previous_frame = bpy.context.scene.frame_current
		# Retrieve or store bake frame in modifier
		if self.change_frame or obj.baker_frame == -1: # baking for first time (-1 value) changes frame automatically.
			obj.baker_frame = bpy.context.scene.frame_current # set the bake frame as current
		else:
			bpy.context.scene.frame_current = obj.baker_frame # otherwise change the frame to the specified one so it bakes at defined place
		
		for bake in mod.bakes:
			bake_id = bake.bake_id
			bpy.ops.object.geometry_node_bake_single(
				session_uid=obj.id_data.session_uid,
				modifier_name=self.modifier_name,
				bake_id=bake_id
			)

		# reset it
		bpy.context.scene.frame_current = previous_frame

		return {'FINISHED'}

class OBJECT_OT_BakeAllGeoNodes(bpy.types.Operator):
	"""Bake all Geometry Nodes modifiers on all objects"""
	bl_idname = "object.bake_all_geometry_nodes"
	bl_label = "Bake All Geometry Nodes"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		previous_frame = bpy.context.scene.frame_current
		
		for obj in bpy.data.objects:
			for mod in obj.modifiers:
				if mod.type == 'NODES' and mod.node_group:
					if "GeometryNodeBake" in [x.bl_idname for x in mod.node_group.nodes]: # if the bake node exists in this modifier
						# Retrieve or store bake frame in modifier
						if obj.baker_frame == -1:
							bpy.context.scene.frame_set(previous_frame)
						else:
							bpy.context.scene.frame_set(obj.baker_frame)
						mod.show_viewport = True
						
						for bake in mod.bakes:
							bpy.ops.object.geometry_node_bake_single(
								session_uid=obj.id_data.session_uid,
								modifier_name=mod.name,
								bake_id=bake.bake_id
							)
		
		bpy.context.scene.frame_set(previous_frame)
		self.report({'INFO'}, "Baked all Geometry Nodes modifiers.")
		return {'FINISHED'}

class OBJECT_OT_EditBake(bpy.types.Operator):
	"""Bake all Geometry Nodes modifiers on all objects"""
	bl_idname = "object.edit_bake"
	bl_label = "Edit"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		obj = context.object;
		bpy.context.scene.frame_set(obj.baker_frame)
		
		self.report({'INFO'}, "Baked all Geometry Nodes modifiers.")
		return {'FINISHED'}


class OBJECT_OT_ToggleBakeDriver(bpy.types.Operator):
	"""Toggle driver for hide_viewport based on the current frame and bake_frame"""
	bl_idname = "object.toggle_bake_driver"
	bl_label = "Automatic Bake Driver"
	bl_options = {'REGISTER', 'UNDO'}

	modifier_name: bpy.props.StringProperty()

	def execute(self, context):
		obj = context.object
		if obj is None:
			self.report({'WARNING'}, "No active object found!")
			return {'CANCELLED'}

		# Ensure modifier exists and fetch the bake_frame
		if self.modifier_name not in obj.modifiers:
			self.report({'WARNING'}, f"Modifier '{self.modifier_name}' not found!")
			return {'CANCELLED'}

		mod = obj.modifiers[self.modifier_name]
		if not hasattr(mod, "bakes") or not mod.bakes:
			self.report({'WARNING'}, f"No bakes found in the modifier '{self.modifier_name}'")
			return {'CANCELLED'}

		driver_paths = [
			"hide_viewport"
			#f'modifiers["{self.modifier_name}"].show_viewport'
		]

		for modifier in obj.modifiers:
			if modifier.node_group.name == "zephkit.cum.launcher": # add any cum launchers to it.
				driver_paths.append(f'modifiers["{modifier.name}"].show_viewport')
		
		if len(obj.animation_data.drivers) > 0:
			# Remove driver if it exists already
			for path in driver_paths:
				obj.driver_remove(path)
			self.report({'INFO'}, "Removed existing driver for hide_viewport.")
		else:
			# Add the driver for hide_viewport
			for i, path in enumerate(driver_paths):
				driver = obj.driver_add(path)
				driver.driver.type = 'SCRIPTED'
				operator = "<" if i == 0 else ">="
				driver.driver.expression = f"bpy.context.scene.frame_current {operator} {obj.baker_frame}"

				# Link the driver to the current frame to make the condition dynamic
				driver.driver.variables.new().targets[0].id_type = 'SCENE'
				driver.driver.variables[0].targets[0].data_path = "frame"

		return {'FINISHED'}

class OBJECT_PT_GeoNodesBakePanel(bpy.types.Panel):
	"""Add Bake buttons to Geometry Nodes modifiers in the Modifiers panel"""
	bl_label = "BAKE..."
	bl_idname = "OBJECT_PT_geonodes_bake"
	bl_space_type = 'PROPERTIES'
	bl_region_type = 'WINDOW'
	bl_context = "modifier"
	
	@classmethod
	def poll(cls, context):
		obj = context.object
		if not obj:
			return False

		for mod in obj.modifiers:
			if mod.type == 'NODES' and mod.node_group:
				if "GeometryNodeBake" in [x.bl_idname for x in mod.node_group.nodes]:
					return True  # Found at least one Bake node

		return False  # No Bake node found

	def draw(self, context):
		layout = self.layout
		obj = context.object

		modifier_name = None
		if obj and obj.modifiers:
			for mod in obj.modifiers:
				found = False
				if mod.type == 'NODES':  # Check if it's a Geometry Nodes modifier
					# Check if there is a Bake node in it. Otherwise, ignore
					node_tree = mod.node_group

					# Search for Bake nodes
					if "GeometryNodeBake" in [x.bl_idname for x in mod.node_group.nodes]: # if the bake node exists in this modifier
						modifier_name = mod.name
						node_tree = mod.node_group
						row = layout.row()
						row.label(text=mod.node_group.name)
						bake_row = row.row(align=True)
						bake_op = bake_row.operator("object.bake_geometry_nodes", icon="NODETREE", text="BAKE")
						bake_op.modifier_name = mod.name
						bake_op.change_frame = False
						if not obj.baker_frame == -1:
							bake_change_frame = bake_row.operator("object.bake_geometry_nodes", icon="MODIFIER", text=str(obj.baker_frame))
							bake_change_frame.modifier_name = mod.name
							bake_change_frame.change_frame = True
						else:
							bake_row.label(text="XXX")
		row = layout.row()
		row.operator("object.bake_all_geometry_nodes", text="BAKE ALL")
		row.operator("object.edit_bake", text="EDIT")

modules = [
	OBJECT_OT_BakeGeoNodes,
	OBJECT_OT_BakeAllGeoNodes,
	OBJECT_OT_ToggleBakeDriver,
	OBJECT_PT_GeoNodesBakePanel,
	OBJECT_OT_EditBake
]

def register():
	for module in modules:
		bpy.utils.register_class(module)

def unregister():
	for module in reversed(modules):
		bpy.utils.unregister_class(module)

if __name__ == "__main__":
	register()
