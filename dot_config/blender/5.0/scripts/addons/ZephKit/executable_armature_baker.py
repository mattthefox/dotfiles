import bpy

class AttributeNamePG(bpy.types.PropertyGroup):
	name: bpy.props.StringProperty(name="Attribute Name")
	frame: bpy.props.IntProperty(name="Bake Frame")

class OBJECT_OT_zephkit_bake_single(bpy.types.Operator):
	bl_idname = "object.zephkit_bake_single"
	bl_label = "Bake Attribute"
	bl_description = "Bake this attribute for the active object"

	index: bpy.props.IntProperty()
	setFrame: bpy.props.BoolProperty()

	def execute(self, context):
		obj = context.active_object

		# A list of modifiers that change the vert count or otherwise interfere. They must be disabled to bake properly.
		disabled_modifiers = [
			"SOLIDIFY",
			"SUBSURF",
			"NODES",
			"MULTIRES",
			"BOOLEAN",
			"ARRAY",
			"LATTICE",
			"MIRROR",
			"BEVEL",
			"BUILD",
			"DECIMATE",
			"EDGE_SPLIT",
			"MASK",
			"REMESH",
			"SCREW",
			"TRIANGULATE",
			"WELD",
			"WIREFRAME",
			"CLOTH"
		]
		if obj is None or obj.type != 'MESH':
			self.report({'WARNING'}, "Active object is not a mesh")
			return {'CANCELLED'}

		if self.setFrame:
			obj.bake_attributes[self.index].frame = context.scene.frame_current;
		attribute_name = obj.bake_attributes[self.index].name

		# Store original state of geometry nodes modifiers
		original_states = {m.name: m.show_viewport for m in obj.modifiers if m.type in disabled_modifiers}
		for modifier in obj.modifiers:
			if modifier.type in disabled_modifiers:
				modifier.show_viewport = False

		mesh = obj.data

		# Create the attribute if it doesn't exist
		if attribute_name not in mesh.attributes:
			mesh.attributes.new(attribute_name, 'FLOAT_VECTOR', 'POINT')
		
		# Store vertex positions in the attribute
		bake_attr = mesh.attributes[attribute_name]

		dg = bpy.context.evaluated_depsgraph_get()
		evaled = obj.evaluated_get(dg)
		eval_mesh = evaled.to_mesh()

		for i, vertex in enumerate(eval_mesh.vertices):
			bake_attr.data[i].vector = vertex.co

		# Restore original states of geometry nodes modifiers
		for modifier_name, state in original_states.items():
			obj.modifiers[modifier_name].show_viewport = state

		self.report({'INFO'}, f"Baking completed for attribute '{attribute_name}'.")
		return {'FINISHED'}

class OBJECT_OT_zephkit_bake_all(bpy.types.Operator):
	bl_idname = "object.zephkit_bake_all"
	bl_label = "Bake All"
	bl_description = "Re-bake all attributes in the scene."

	def execute(self, context):
		for obj in context.scene.objects:
			if obj is None or obj.type != 'MESH':
				continue;

			for i, attr in enumerate(obj.bake_attributes):
				bpy.ops.object.zephkit_bake_single(context)
			attribute_name = obj.bake_attributes[self.index].name

		return {'FINISHED'}

class OBJECT_OT_zephkit_add_attribute(bpy.types.Operator):
	bl_idname = "object.zephkit_add_attribute"
	bl_label = "Add Attribute"
	bl_description = "Add a new attribute to bake"

	def execute(self, context):
		context.object.bake_attributes.add()
		return {'FINISHED'}

class OBJECT_OT_zephkit_remove_attribute(bpy.types.Operator):
	bl_idname = "object.zephkit_remove_attribute"
	bl_label = "Remove Attribute"
	bl_description = "Remove selected attribute from the list"

	index: bpy.props.IntProperty()

	def execute(self, context):
		obj = context.object
		obj.bake_attributes.remove(self.index)
		return {'FINISHED'}

class OBJECT_PT_zephkit_baker_panel(bpy.types.Panel):
	bl_idname = "OBJECT_PT_zephkit_baker_panel"
	bl_label = "Zephkit Baker"
	bl_space_type = "VIEW_3D"
	bl_region_type = "TOOLS"

	def draw(self, context):
		layout = self.layout
		obj = context.object

		row = layout.row()
		row.operator("object.zephkit_add_attribute", icon='ADD')
		
		for i, attr in enumerate(obj.bake_attributes):
			row = layout.row(align=True)
			remove_op = row.operator("object.zephkit_remove_attribute", text="", icon='X')
			remove_op.index = i
			row.prop(attr, "name", text="")
			bake_op = row.operator("object.zephkit_bake_single", text="", icon='RENDER_STILL')
			bake_op.index = i
			bake_op.setFrame = True;

modules = [
	OBJECT_OT_zephkit_bake_single,
	OBJECT_OT_zephkit_add_attribute,
	OBJECT_OT_zephkit_remove_attribute,
	OBJECT_PT_zephkit_baker_panel
]

def register():
	bpy.utils.register_class(AttributeNamePG)
	bpy.types.Object.bake_attributes = bpy.props.CollectionProperty(type=AttributeNamePG)
	for module in modules:
		bpy.utils.register_class(module)

def unregister():
	for module in reversed(modules):
		bpy.utils.unregister_class(module)
	del bpy.types.Object.bake_attributes
	bpy.utils.unregister_class(AttributeNamePG)