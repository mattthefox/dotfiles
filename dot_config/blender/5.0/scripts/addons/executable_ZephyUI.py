bl_info = {
	"name": "ZephyUI",
	"author": "azephynight",
	"version": (1, 0),
	"blender": (4, 0, 0),
	"location": "3D View > Sidebar > ZephKit",
	"description": "Manage custom properties tagged with zephkit_tag metadata",
	"category": "3D View",
}

import bpy
from bpy.props import BoolProperty, StringProperty, FloatProperty, EnumProperty
import json

PREDEFINED_ICONS = [
	("DOT", "Default", "Default"),
	("NONE", "--TECHNICAL--", "--TECHNICAL--", 1),
	("MOD_CLOTH", "Cloth", "Cloth", "MOD_CLOTH", 2),
	("MATERIAL", "Material", "Material", "MATERIAL", 3),
	("ARMATURE_DATA", "Armature", "Armature", "ARMATURE_DATA", 4),
	("EXPERIMENTAL", "Experimental", "Experimental", "EXPERIMENTAL", 5),
	("PHYSICS", "Physics", "Physics", "PHYSICS", 6),
	("WORLD", "World", "World", "WORLD", 7),
	("PARTICLEMODE", "Comb", "Comb", "PARTICLEMODE", 8),
	("OUTLINER_OB_POINTCLOUD", "Points", "Points", "OUTLINER_OB_POINTCLOUD", 9),
	("SHAPEKEY_DATA", "Shape Key", "Shape Key", "SHAPEKEY_DATA", 10),
	("LIGHT", "Light", "Light", "LIGHT", 11),

	("NONE", "--BODY--", "--BODY--", 12),
	("USER", "Face", "Face", "USER", 13),
	("HIDE_OFF", "Eye", "Eye", "HIDE_OFF", 14),
	("STRANDS", "Hair", "Hair", "STRANDS", 15),
	("MOD_DYNAMICPAINT", "Foot", "Foot", "MOD_DYNAMICPAINT", 16),
	("CAMERA_STEREO", "Glasses", "Glasses", "CAMERA_STEREO", 17),

	("DOT", "--ICON--", "--ICON--", 18),
	("OUTLINER_DATA_VOLUME", "Cloud", "Cloud", "OUTLINER_DATA_VOLUME", 19),
	("FUND", "Hearth", "Hearth", "FUND", 20),
	("MATSHADERBALL", "Ball", "Ball", "MATSHADERBALL", 21),
	("GHOST_ENABLED", "Ghost", "Ghost", "GHOST_ENABLED", 22),
	("ERROR", "Error", "Error", "ERROR", 23),
	("SOLO_ON", "Star", "Star", "SOLO_ON", 24),
	("COMMUNITY", "Crowd", "Crowd", "COMMUNITY", 25),

	("NONE", "--NSFW--", "--NSFW--", 26),
	("PIVOT_INDIVIDUAL", "Boobs", "Boobs", "PIVOT_INDIVIDUAL", 27),
	("MOD_OUTLINE", "Penis", "Penis", "MOD_OUTLINE", 28),
	("PIVOT_CURSOR", "Anus", "Anus", "PIVOT_CURSOR", 29),
	("MOUSE_MMB", "Vagina", "Vagina", "MOUSE_MMB", 30),
	("META_BALL", "Butt", "Butt", "META_BALL", 31),
	("MOD_FLUIDSIM", "Liquid", "Liquid", "MOD_FLUIDSIM", 32),
	("IPO_BACK", "Cum", "Cum", "IPO_BACK", 33),
	("PROP_OFF", "Nipple", "Nipple", "PROP_OFF", 34)
]

# ------------------------------------------------------------------------
# GLOBAL STATE
# ------------------------------------------------------------------------
def register_custom_properties():
	bpy.types.Scene.zephyui_editmode = BoolProperty(
		name="Edit Mode",
		description="Enable or disable editing of properties.",
		default=True
	)

# ------------------------------------------------------------------------
# HELPERS
# ------------------------------------------------------------------------
def get_property_owner(context):
	"""
	Returns the Armature object associated with the active object.
	- If the active object is an Armature, returns it.
	- If it's a Mesh with an Armature modifier, returns the target Armature.
	- Otherwise returns None.
	"""
	obj = context.object
	if not obj:
		return None

	if obj.type == "ARMATURE":
		return obj

	if obj.type == "MESH":
		for mod in obj.modifiers:
			if mod.type == "ARMATURE" and mod.object and mod.object.type == "ARMATURE":
				return mod.object

	return obj

def get_armature_object_from_data(armature_data):
	for obj in bpy.data.objects:
		if obj.type == 'ARMATURE' and obj.data == armature_data:
			return obj
	return None

def get_rig_components(scene):
	"""Ensure we have a mapping in the scene's custom properties."""
	if "_ZK_RIG_MAP" not in scene:
		scene["_ZK_RIG_MAP"] = {}
	return scene["_ZK_RIG_MAP"]

USE_NAME = "Select all with name"

def get_enum_items(self, context):
	next_index = 0
	obj = context.object

	if not obj or obj.type != 'ARMATURE':
		return [('NONE', 'No Armature Selected', '', 'ERROR', 0)]

	arm = obj.data
	items = [(USE_NAME, USE_NAME, "By Name", 'FILE_TEXT', next_index)]
	next_index += 1

	# List bones
	for bone in arm.bones:
		items.append((bone.name, bone.name, "Bone", 'BONE_DATA', next_index))
		next_index += 1

	# List bone collections (Blender 4+)
	for coll in arm.collections_all:
		items.append((coll.name, coll.name, "Bone Collection", 'GROUP_BONE', next_index))
		next_index += 1

	return items

def get_ui_groups(self, context):
	next_index = 0
	obj = context.object

	if not obj or obj.type != 'ARMATURE':
		return [('NONE', 'No Armature Selected', '', 'ERROR', 0)]

	arm = obj.data
	items = [(USE_NAME, USE_NAME, "By Name", 'FILE_TEXT', next_index)]
	next_index += 1

	# List bones
	for bone in arm.bones:
		items.append((bone.name, bone.name, "Bone", 'BONE_DATA', next_index))
		next_index += 1

	# List bone collections (Blender 4+)
	for coll in arm.collections_all:
		items.append((coll.name, coll.name, "Bone Collection", 'GROUP_BONE', next_index))
		next_index += 1

	return items

# ------------------------------------------------------------------------
# PROPERTY PANEL DRAW
# ------------------------------------------------------------------------
def draw_props(context, layout, datablock, is_scene):
	rna_ui = datablock.get("_RNA_UI", {})
	tagged_keys = [k for k, meta in rna_ui.items() if meta.get("zephkit_tag")]
	edit_mode = context.scene.zephyui_editmode

	if not tagged_keys:
		layout.label(icon="INFO", text="No properties added.")
		if edit_mode:
			layout.operator("zk.add_tagged_prop", icon="ADD").is_scene = is_scene
		return

	for key in tagged_keys:
		row = layout.row(align=True)

		if edit_mode:
			icon_name = "KEY_MENU_FILLED"
		else:
			meta = rna_ui.get(key, {})
			icon_name = meta.get("icon", "NONE")

		icon_select = row.operator("zk.property_ui_settings", text="", icon=icon_name)
		icon_select.is_scene = is_scene
		icon_select.property_name = key

		row.prop(datablock, f'["{key}"]', text=key)

		if edit_mode:
			edit = row.operator("wm.properties_edit", text="", icon="PREFERENCES")
			edit.data_path = "scene" if is_scene else "object"
			edit.property_name = key

			remove = row.operator("zk.remove_tagged_prop", text="", icon="X")
			remove.data_path = "scene" if is_scene else "object"
			remove.property_name = key

	if edit_mode:
		layout.separator()
		layout.operator("zk.add_tagged_prop", icon="ADD").is_scene = is_scene

# ------------------------------------------------------------------------
# PANELS
# ------------------------------------------------------------------------
class ZK_PT_tagged_props(bpy.types.Panel):
	bl_label = "Global Properties"
	bl_idname = "ZK_PT_global_props"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'ZEPHKIT ↓'

	def draw(self, context):
		layout = self.layout
		scene = context.scene

		draw_props(context, layout, scene, is_scene=True)

class ZK_PT_local_props(bpy.types.Panel):
	bl_label = "Local Properties"
	bl_idname = "ZK_PT_local_props"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'ZEPHKIT ↓'

	def draw(self, context):
		layout = self.layout
		layout.use_property_split = False
		row = layout.row()
		row.prop(context.scene, "zephyui_editmode", toggle=True, icon="TOOL_SETTINGS")
		layout.separator()

		obj = get_property_owner(context)
		if obj:
			draw_props(context, layout, obj, is_scene=False)
		else:
			layout.label(text="No active object.")

class ZK_PT_rigui(bpy.types.Panel):
	bl_label = "Rig"
	bl_idname = "ZK_PT_rigui"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = 'ZEPHKIT ↓'

	def draw(self, context):
		def rigging_menu_item(name, layout=self.layout):
			icons = {
				"head": ["USER"],
				"breast": ["PROP_OFF"],
				"hand": ["VIEW_PAN"],
				"origin": ["PIVOT_CURSOR"],
				"thumb": ["STRIP_COLOR_01", False],
				"index": ["STRIP_COLOR_02", False],
				"middle": ["STRIP_COLOR_03", False],
				"ring": ["STRIP_COLOR_04", False],
				"pinky": ["STRIP_COLOR_05", False]
			}
			if name:
				trim_name = name.lower().replace(".l","").replace(".r","")
				button = icons[trim_name] if trim_name in icons else ["RADIOBUT_OFF"]
				icon = button[0] if name in rig_map else "PREFERENCES"
				scaled = button[1] if len(button) > 1 else True

				big_button = layout.column(align=True)
				if scaled:
					big_button.scale_y=1.25
				# red for right
				if ".r" in name.lower():
					big_button.alert = True
				# blue for left
				depress = False
				if ".l" in name.lower():
					depress = True
				rig_component = big_button.operator("ZK_OT_rig_component", text = name, icon=icon, depress=depress)
				rig_component.component_name = name
			else: # empty entry, for spacing.
				layout.label(text="")
		def rig_row(*elements):
			layout = self.layout
			row = layout.row(align=True)
			for element in elements:
				rigging_menu_item(element, row)
		layout = self.layout
		scene = context.scene
		rig_map = scene.get("_ZK_RIG_MAP", {})

		# Standard humanoid layout.
		rig_row("head")
		rig_row("neck")
		rig_row("shoulder.L", "spine", "shoulder.R")
		rig_row("arm.L","breast.L", "breast.R", "arm.R")
		rig_row("forearm.L","chest","forearm.R")
		rig_row("hand.L","hips","hand.R")
		rig_row("pelvis")
		rig_row("thigh.L", "thigh.R")
		rig_row("calf.L", "calf.R")
		rig_row("foot.L", "foot.R")
		rig_row("origin")
		layout.row()
		rig_row("fingers.L", "fingers.R")
		rig_row("thumb.L","thumb.R")
		rig_row("index.L","index.R")
		rig_row("middle.L","middle.R")
		rig_row("ring.L","ring.R")
		rig_row("pinky.L","pinky.R")
		layout.row()
		row = layout.row(align=True)
		row.operator("zk.import_rig_map", icon="IMPORT")
		row.operator("zk.export_rig_map", icon="EXPORT")

class ZK_OT_rig_component(bpy.types.Operator):
	"""Add or select a ZephKit rig component"""
	bl_idname = "zk.rig_component"
	bl_label = "Rig Component"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "target"

	component_name: bpy.props.StringProperty(name="Component Name")
	target: bpy.props.EnumProperty(name="Target", items=get_enum_items)

	def invoke(self, context, event):
		scene = context.scene
		rig_map = scene.get("_ZK_RIG_MAP", {})

		# Prompt to change mapping if it doesn't exist, OR if we're in edit mode.
		if self.component_name in rig_map and not context.scene.zephyui_editmode:
			mapped = rig_map[self.component_name]
			self.report({'INFO'}, f"Already mapped to {mapped}")
			self.select_target(context, mapped, self.component_name, union=event.shift)
			return {'CANCELLED'}

		context.window_manager.invoke_search_popup(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		scene = context.scene
		rig_map = scene.get("_ZK_RIG_MAP", {})
		rig_map[self.component_name] = self.target
		scene["_ZK_RIG_MAP"] = rig_map
		self.report({'INFO'}, f"Mapped {self.component_name} → {self.target}")
		return {'FINISHED'}

	def select_target(self, context, name, component_name = "", union=False):
		"""Select the mapped bone/collection in the armature."""
		obj = context.object
		if not obj or obj.type != 'ARMATURE':
			return

		arm = obj.data


		bpy.ops.object.mode_set(mode='POSE')
		if not union:
			bpy.ops.pose.select_all(action='DESELECT')

		if name == USE_NAME: # Select all by name mode.
			lower_name = component_name.lower()

			if lower_name.endswith(".l"):
				trim_name = lower_name[:-2]
				side = ".l"
			elif lower_name.endswith(".r"):
				trim_name = lower_name[:-2]
				side = ".r"
			else:
				return
			
			for pose_bone in obj.pose.bones:
				if trim_name in pose_bone.name.lower() and side in pose_bone.name.lower():
					pose_bone.select = True
			return

		if name in arm.bones:
			obj.pose.bones[name].select = True
			return

		if name in arm.collections_all:
			for bone in arm.collections_all[name].bones:
				obj.pose.bones[bone.name].select = True
			return

class ZK_OT_ImportRigMap(bpy.types.Operator):
	"""Add or select a ZephKit rig component"""
	bl_idname = "zk.import_rig_map"
	bl_label = "Import map"
	bl_options = {'REGISTER', 'UNDO'}

	filepath: bpy.props.StringProperty(subtype='FILE_PATH')

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		scene = context.scene

		with open(filepath) as f:
			scene["_ZK_RIG_MAP"] = json.load(f)

		return {'FINISHED'}

class ZK_OT_ExportRigMap(bpy.types.Operator):
	bl_idname = "zk.export_rig_map"
	bl_label = "Export map"

	filepath: bpy.props.StringProperty(subtype='FILE_PATH')

	def invoke(self, context, event):
		context.window_manager.fileselect_add(self)
		return {'RUNNING_MODAL'}

	def execute(self, context):
		import json
		scene = context.scene

		rig_map = scene.get("_ZK_RIG_MAP", {})

		with open(self.filepath, "w") as f:
			json.dump(rig_map, f, indent=4)

		self.report({'INFO'}, "Rig map exported")
		return {'FINISHED'}

class ZK_OT_add_tagged_prop(bpy.types.Operator):
	"""Add a new ZephKit tagged custom property"""
	bl_idname = "zk.add_tagged_prop"
	bl_label = "Add ZephKit Property"

	is_scene: bpy.props.BoolProperty()
	prop_name: bpy.props.StringProperty(name="Property Name", default="my_prop")
	default_value: bpy.props.FloatProperty(name="Default Value", default=0.0)
	min_value: bpy.props.FloatProperty(name="Min", default=0.0)
	max_value: bpy.props.FloatProperty(name="Max", default=1.0)
	description: bpy.props.StringProperty(name="Description", default="ZephKit property")

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "prop_name")
		layout.prop(self, "default_value")
		layout.prop(self, "min_value")
		layout.prop(self, "max_value")
		layout.prop(self, "description")

	def execute(self, context):
		target = context.scene if self.is_scene else get_property_owner(context)
		if not target:
			self.report({'ERROR'}, "No valid target")
			return {'CANCELLED'}

		if not target.get("_RNA_UI"):
			target["_RNA_UI"] = {}

		target[self.prop_name] = self.default_value
		target["_RNA_UI"][self.prop_name] = {
			"min": self.min_value,
			"max": self.max_value,
			"description": self.description,
			"zephkit_tag": True,
			"icon": "DOT",
		}

		return {'FINISHED'}

class ZK_OT_remove_tagged_prop(bpy.types.Operator):
	"""Remove a ZephKit tagged property"""
	bl_idname = "zk.remove_tagged_prop"
	bl_label = "Remove ZephKit Property"
	bl_options = {'UNDO'}

	data_path: bpy.props.StringProperty()
	property_name: bpy.props.StringProperty()

	def execute(self, context):
		if self.data_path == "scene":
			target = context.scene
		else:
			target = get_property_owner(context)

		if not target:
			self.report({'ERROR'}, "No valid target found")
			return {'CANCELLED'}

		# Actually remove from data and metadata
		if self.property_name in target:
			del target[self.property_name]

		rna_ui = target.get("_RNA_UI", {})
		if self.property_name in rna_ui:
			del rna_ui[self.property_name]

		# Clean up empty _RNA_UI dictionary if needed
		if not rna_ui:
			if "_RNA_UI" in target:
				del target["_RNA_UI"]

		self.report({'INFO'}, f"Removed property '{self.property_name}'")
		return {'FINISHED'}

class ZK_OT_Property_UI_Settings(bpy.types.Operator):
	bl_idname = "zk.property_ui_settings"
	bl_label = "UI Settings"
	bl_description = "Choose an icon and group for the property."
	bl_options = {'UNDO'}

	is_scene: BoolProperty()
	property_name: StringProperty()
	icon: EnumProperty(name="Icon", items=PREDEFINED_ICONS)
	group: EnumProperty(name="Group", items=get_ui_groups)

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self, width=300)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "icon")
		layout.prop(self, "group")

	def execute(self, context):
		target = context.scene if self.is_scene else get_property_owner(context)
		if not target or "_RNA_UI" not in target:
			self.report({'ERROR'}, "No valid target or metadata")
			return {'CANCELLED'}

		if self.property_name not in target["_RNA_UI"]:
			self.report({'ERROR'}, f"Property '{self.property_name}' not found")
			return {'CANCELLED'}

		target["_RNA_UI"][self.property_name]["icon"] = self.icon
		return {'FINISHED'}

def get_clipboard():
	# Try system clipboard
	try:
		return subprocess.check_output(['wl-paste'], text=True).strip()
	except:
		return ""

class ZK_PT_add_property(bpy.types.Operator):
	"""Add the property to the ZephKit UI"""
	bl_idname = "zk.property_menuadd"
	bl_label = "Add to ZephKit UI"
	bl_options = {'UNDO'}

	name: bpy.props.StringProperty(name="Display Name", default="New Property")
	icon: bpy.props.EnumProperty(name="Icon", items=PREDEFINED_ICONS)
	description: bpy.props.StringProperty(name="Description", default="")

	def execute(self, context):
		path = bpy.context.window_manager.clipboard.strip()

		if not path:
			self.report({'ERROR'}, 'Clipboard is empty or invalid.')
			return {'CANCELLED'}

		# Try to resolve the property from the clipboard path
		try:
			value = eval(f"context.{path}")
		except Exception as e:
			self.report({'ERROR'}, f"Failed to access property: {e}")
			return {'CANCELLED'}

		# Get object to store _RNA_UI metadata
		obj = context.object
		if not obj:
			self.report({'ERROR'}, 'No active object found.')
			return {'CANCELLED'}

		# Extract the property name (everything after the last ".")
		if "[" in path:
			prop_name = path.split("[")[-1].strip("]'\"")
		else:
			prop_name = path.split(".")[-1]

		if "_RNA_UI" not in obj:
			obj["_RNA_UI"] = {}

		obj["_RNA_UI"][prop_name] = {
			"description": self.description,
			"zephkit_tag": True,
			"icon": self.icon,
		}

		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		layout.prop(self, "name")
		layout.prop(self, "description")
		layout.prop(self, "icon")

classes = [
	ZK_PT_local_props,
	ZK_OT_rig_component,
	ZK_PT_rigui,
	ZK_PT_add_property,
	ZK_PT_tagged_props,
	ZK_OT_add_tagged_prop,
	ZK_OT_remove_tagged_prop,
	ZK_OT_Property_UI_Settings,
	ZK_OT_ImportRigMap,
	ZK_OT_ExportRigMap
]

# Function to link a property in the MustardUI.
def property_menu(self, context):
	# Check if the context has 'button_prop' attribute and if an object was found.
	if hasattr(context, 'button_prop') and context.object:
		layout = self.layout  # Get the layout for the UI.
		# Add a menu for linking properties in the UI.
		layout.separator()
		layout.operator("zk.property_menuadd", icon="LINKED")


def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	register_custom_properties()
	bpy.types.UI_MT_button_context_menu.append(property_menu)

def unregister():
	bpy.types.UI_MT_button_context_menu.remove(property_menu)
	for cls in classes:
		bpy.utils.unregister_class(cls)
		

if __name__ == "__main__":
	register()
