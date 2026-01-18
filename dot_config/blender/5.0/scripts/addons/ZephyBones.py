bl_info = {
	"name": "Fuzzy Bone Selector",
	"author": "azephynight",
	"version": (1, 1),
	"blender": (3, 0, 0),
	"location": "View3D > Sidebar > Bone Selector",
	"description": "Fuzzy search and select bones with prettified names",
	"category": "Rigging",
}

import bpy
import difflib

GROUPINGS = {
	"fingers": ["thumb", "index", "middle", "ring", "pinky"],
	"toes": ["toe"],
	"spine": ["pelvis","hip","spine","neck","head", "back", "chest"],
	"expression": ["face", "eye", "tong", "mouth", "brow", "ear", "teeth", "tooth", "tongue", "nose", "throat", "lash", "iris", "gaze", "pupil", "sclera", "wink", "blink", "lip"],
	"arm": ["clavicle", "shoulder", "arm", "hand", "elbow"],
	"leg": ["knee", "thigh", "leg"],
	"foot": ["foot", "tarsal", "ball", "heel", "shin", "ankle"],
	"genital": ["pussy", "vagina", "penis", "testicle", "balls", "anus", "breast", "clit", "shaft", "labia"]
}

EXCLUDE = ["mech", "drv", "fin"]

ICONS = {
	# groups
	"fingers": "OUTLINER_OB_CURVES",
	"spine": "SEQ_LUMA_WAVEFORM",
	"arm": "CHECKMARK",
	"expression": "USER",
	
	
	"pectoral": "PIVOT_INDIVIDUAL",
	"boob": "PIVOT_INDIVIDUAL",
	"thumb": "STRIP_COLOR_01",
	"index": "STRIP_COLOR_02",
	"middle": "STRIP_COLOR_03",
	"ring": "STRIP_COLOR_04",
	"pinky": "STRIP_COLOR_05",
}

def prettify_bone_name(name):
	parts = name.split(".")
	base = parts[0].capitalize()
	number = ""
	side = ""
	for part in parts[1:]:
		if part.isdigit():
			number = f" {part}"
		elif part.lower() in {"l", "r"}:
			side = " (Left)" if part.lower() == "l" else " (Right)"
		else:
			number += f".{part}"
	return f"{base}{number}{side}"

def is_group_collapsed(props, key):
	keys = props.collapsed_groups.split(";") if props.collapsed_groups else []
	return key in keys

def toggle_group_collapsed(props, key):
	keys = props.collapsed_groups.split(";") if props.collapsed_groups else []
	if key in keys:
		keys.remove(key)
	else:
		keys.append(key)
	props.collapsed_groups = ";".join(keys)

class BoneSelectorProps(bpy.types.PropertyGroup):
	search_query: bpy.props.StringProperty(name="Search", description="Search bone names")
	collapsed_groups: bpy.props.StringProperty(
		name="Collapsed Groups",
		description="Semicolon-separated list of collapsed group keys",
		default=""
	)


def prepare_bone_hierarchy(bones, search_query):
	"""
	Returns a nested list of dicts:
	[
		{
			"Group": "Fingers",
			"Contents": [
				{
					"Group": "Thumb",
					"Contents": [ ["thumb.L", "thumb.R"], "thumb.02.L" ]
				},
				...
			]
		},
		...
	]
	"""
	def group_lr_pairs(bone_names):
		pairs = []
		used = set()

		def base_name(name):
			for suffix in [".L", ".R", "_L", "_R"]:
				if name.endswith(suffix):
					return name[:-len(suffix)]
			return None

		name_map = {}
		for name in bone_names:
			bname = base_name(name)
			if bname:
				name_map.setdefault(bname, []).append(name)
			else:
				name_map.setdefault(name, []).append(name)

		for bname, names in name_map.items():
			if len(names) == 2:
				# Sort so L always first, R second
				sorted_pair = sorted(names, key=lambda n: 0 if n.endswith((".L", "_L")) else 1)
				pairs.append(sorted_pair)
			else:
				# Single bone or no matching pair
				pairs.extend(names)

		return pairs

	results = []
	grouped_bones = set()

	# Filter bones by search query if given
	if not search_query:
		filtered_bones = bones
	else:
		query = search_query.lower()
		name_matches = [bone for bone in bones if query in bone.name.lower()]

		group_matches = []
		for bone in bones:
			name_lower = bone.name.lower()
			for group_name, keywords in GROUPINGS.items():
				if query in group_name.lower() or any(query in k for k in keywords):
					if bone not in group_matches:
						group_matches.append(bone)
					break

		filtered_bones = list({b for b in name_matches + group_matches})

	# --- 1. Defined groups with subgrouping by keyword ---
	for group_name, keywords in GROUPINGS.items():
		group_contents = []
		for keyword in keywords:
			keyword_bones = [
				bone for bone in filtered_bones
				if keyword in bone.name.lower()
				and not any(ex in bone.name.lower() for ex in EXCLUDE)
			]
			if keyword_bones:
				grouped_names = [b.name for b in keyword_bones]
				grouped_bones.update(grouped_names)
				group_contents.append({
					"Group": keyword.capitalize(),
					"Contents": group_lr_pairs(grouped_names)
				})
		if group_contents:
			results.append({
				"Group": group_name,
				"Contents": group_contents
			})

	# --- 2. Numbered bone groups ---
	base_groups = {}
	for bone in filtered_bones:
		if bone.name in grouped_bones or any(ex in bone.name.lower() for ex in EXCLUDE):
			continue
		if "." in bone.name:
			base = bone.name.split(".")[0]
			base_groups.setdefault(base, []).append(bone)

	for base, bones_in_group in base_groups.items():
		if len(bones_in_group) > 1:
			grouped_names = [b.name for b in bones_in_group]
			grouped_bones.update(grouped_names)
			results.append({
				"Group": prettify_bone_name(base),
				"Contents": group_lr_pairs(grouped_names)
			})

	# --- 3. Ungrouped bones ---
	ungrouped = [
		bone.name for bone in filtered_bones
		if bone.name not in grouped_bones and not any(ex in bone.name.lower() for ex in EXCLUDE)
	]
	for bone_name in sorted(ungrouped):
		results.append({
			"Group": prettify_bone_name(bone_name),
			"Contents": [bone_name]
		})
		
	# Add them all to a parent named after the rig.
	results_with_parent = [
		{
		"Group": "Rig",
		"Contents": results
		}
	]

	return results_with_parent


class POSE_OT_toggle_group(bpy.types.Operator):
	bl_idname = "pose.toggle_bone_group"
	bl_label = "Toggle Bone Group"
	bl_description = "Expand or collapse this group"

	group_key: bpy.props.StringProperty()

	def execute(self, context):
		props = context.scene.fuzzy_bone_selector
		toggle_group_collapsed(props, self.group_key)
		return {'FINISHED'}

class POSE_OT_select_bone_named(bpy.types.Operator):
	bl_idname = "pose.select_bone_named"
	bl_label = "Select Bone"
	bl_description = "Select the specified bone"

	bone_name: bpy.props.StringProperty()

	def execute(self, context):
		armature = context.object
		for b in armature.data.bones:
			b.select = False
		context.object.data.bones.active = context.object.data.bones.get(self.bone_name)
		armature.data.bones[self.bone_name].select = True
		return {'FINISHED'}

class VIEW3D_PT_fuzzy_bone_selector(bpy.types.Panel):
	bl_label = "Bone Selector"
	bl_idname = "VIEW3D_PT_fuzzy_bone_selector"
	bl_space_type = 'VIEW_3D'
	bl_region_type = 'UI'
	bl_category = "ZEPHKIT ↓"

	@classmethod
	def poll(cls, context):
		obj = context.object
		return obj and obj.type == 'ARMATURE' and context.mode == 'POSE'

	def draw(self, context):
		layout = self.layout
		props = context.scene.fuzzy_bone_selector
		armature = context.object

		layout.operator("pose.collapse_all_bone_groups", text="Collapse All", icon="DOWNARROW_HLT")
		layout.prop(props, "search_query", text="")

		if not props.search_query:
			# Show full hierarchy
			hierarchy = prepare_bone_hierarchy(armature.pose.bones, props.search_query)
			self.draw_contents(layout, hierarchy)
		else:
			query = props.search_query.lower()
			# Check if search matches any group name (top level or subgroup)
			hierarchy = prepare_bone_hierarchy(armature.pose.bones, "")  # get full hierarchy without filtering
			matched_groups = []

			def find_matching_groups(contents):
				results = []
				for entry in contents:
					if isinstance(entry, dict):
						group_lower = entry["Group"].lower()
						if query in group_lower:
							results.append(entry)
						else:
							# recurse into subgroups
							subgroups = find_matching_groups(entry.get("Contents", []))
							if subgroups:
								results.append({
									"Group": entry["Group"],
									"Contents": subgroups
								})
				return results

			matched_groups = find_matching_groups(hierarchy)

			if matched_groups:
				# Show only matched groups & their contents
				self.draw_contents(layout, matched_groups)
			else:
				# Show flat list of matching bones (no groups)
				filtered_bones = [b for b in armature.pose.bones if query in b.name.lower()]
				for bone in filtered_bones:
					icon = 'BONE_DATA'
					for k, v in ICONS.items():
						if k in bone.name.lower():
							icon = v
							break
					op = layout.operator("pose.select_bone_named", text=prettify_bone_name(bone.name), icon=icon)
					op.bone_name = bone.name

	def draw_contents(self, layout, contents, parent_key="", level=0):
		props = bpy.context.scene.fuzzy_bone_selector

		for entry in contents:
			if isinstance(entry, dict):
				key = parent_key + "." + entry["Group"] if parent_key else entry["Group"]
				
				# Check for single bone or L/R pair
				single_bone_group = False
				if len(entry["Contents"]) == 1:
					only_content = entry["Contents"][0]
					if isinstance(only_content, str):
						single_bone_group = True
					elif isinstance(only_content, list) and len(only_content) == 2 and all(isinstance(b, str) for b in only_content):
						single_bone_group = True

				if single_bone_group:
					row = layout.row(align=True)
					icon = 'GROUP_BONE'
					group_name_lower = entry["Group"].lower()
					for k, v in ICONS.items():
						if k in group_name_lower:
							icon = v
							break
					row.label(text=entry["Group"], icon=icon)

					inner_layout = layout if level == 0 else layout.box()
					self.draw_contents(inner_layout, entry["Contents"], parent_key=key, level=level + 1)

				else:
					collapsed = is_group_collapsed(props, key)
					row = layout.row(align=True)
					icon = 'GROUP_BONE'
					group_name_lower = entry["Group"].lower()
					for k, v in ICONS.items():
						if k in group_name_lower:
							icon = v
							break

					op = row.operator("pose.toggle_bone_group", text="", icon='TRIA_RIGHT' if collapsed else 'TRIA_DOWN', emboss=False)
					op.group_key = key

					row.label(text=entry["Group"], icon=icon)

					select_op = row.operator("pose.select_bone_group", text="", icon="RESTRICT_SELECT_OFF")
					select_op.group_key = key

					solo_op = row.operator("pose.solo_bone_group", text="", icon="HIDE_OFF")
					solo_op.group_key = key

					if not collapsed:
						inner_layout = layout if level == 0 else layout.box()
						self.draw_contents(inner_layout, entry["Contents"], parent_key=key, level=level + 1)

			elif isinstance(entry, list) and len(entry) == 2 and all(isinstance(b, str) for b in entry):
				row = layout.row(align=True)
				for bone_name in entry:
					icon = 'BONE_DATA'
					for k, v in ICONS.items():
						if k in bone_name.lower():
							icon = v
							break
					op = row.operator("pose.select_bone_named", text=prettify_bone_name(bone_name), icon=icon)
					op.bone_name = bone_name

			elif isinstance(entry, str):
				icon = 'BONE_DATA'
				for k, v in ICONS.items():
					if k in entry.lower():
						icon = v
						break
				op = layout.operator("pose.select_bone_named", text=prettify_bone_name(entry), icon=icon)
				op.bone_name = entry



class POSE_OT_collapse_all_groups(bpy.types.Operator):
	bl_idname = "pose.collapse_all_bone_groups"
	bl_label = "Collapse All Bone Groups"
	bl_description = "Collapse all bone groups"

	def execute(self, context):
		props = context.scene.fuzzy_bone_selector
		armature = context.object
		if not armature:
			self.report({'WARNING'}, "No armature selected")
			return {'CANCELLED'}

		hierarchy = prepare_bone_hierarchy(armature.pose.bones, props.search_query)

		def collect_keys(contents, parent_key=""):
			keys = []
			for entry in contents:
				if isinstance(entry, dict):
					key = parent_key + "." + entry["Group"] if parent_key else entry["Group"]
					keys.append(key)
					keys.extend(collect_keys(entry["Contents"], key))
			return keys

		all_keys = collect_keys(hierarchy)
		props.collapsed_groups = ";".join(all_keys)
		return {'FINISHED'}

class POSE_OT_select_group(bpy.types.Operator):
	bl_idname = "pose.select_bone_group"
	bl_label = "Select Bone Group"
	bl_description = "Select all bones in this group"

	group_key: bpy.props.StringProperty()
	mode: bpy.props.IntProperty()

	def execute(self, context):
		props = context.scene.fuzzy_bone_selector
		armature = context.object
		if not armature or armature.type != 'ARMATURE':
			self.report({'WARNING'}, "No armature selected")
			return {'CANCELLED'}

		hierarchy = prepare_bone_hierarchy(armature.pose.bones, props.search_query)

		# Collect all bone names for group_key recursively
		def collect_bones(contents, key, parent_key=""):
			bones = []
			for entry in contents:
				if isinstance(entry, dict):
					curr_key = parent_key + "." + entry["Group"] if parent_key else entry["Group"]
					if curr_key == key:
						# Collect all bones in this group recursively
						return collect_all_bones(entry["Contents"])
					else:
						bones.extend(collect_bones(entry["Contents"], key, curr_key))
			return bones

		def collect_all_bones(contents):
			collected = []
			for entry in contents:
				if isinstance(entry, dict):
					collected.extend(collect_all_bones(entry["Contents"]))
				elif isinstance(entry, list):
					collected.extend(entry)  # L/R pair list
				else:
					collected.append(entry)
			
			return collected

		bones_to_select = collect_bones(hierarchy, self.group_key)
		if not bones_to_select:
			self.report({'WARNING'}, f"No bones found for group {self.group_key}")
			return {'CANCELLED'}

		for b in armature.data.bones:
			if b.name in bones_to_select:
				b.select = True
			else:
				b.select = b.select  # Keep current state

		if bones_to_select:
			armature.data.bones.active = armature.data.bones.get(bones_to_select[0])

		return {'FINISHED'}


class POSE_OT_solo_group(bpy.types.Operator):
	bl_idname = "pose.solo_bone_group"
	bl_label = "Solo Bone Group"
	bl_description = "Select only bones in this group, deselect others"

	group_key: bpy.props.StringProperty()

	def execute(self, context):
		props = context.scene.fuzzy_bone_selector
		armature = context.object
		if not armature or armature.type != 'ARMATURE':
			self.report({'WARNING'}, "No armature selected")
			return {'CANCELLED'}

		hierarchy = prepare_bone_hierarchy(armature.pose.bones, props.search_query)

		def collect_bones(contents, key, parent_key=""):
			bones = []
			for entry in contents:
				if isinstance(entry, dict):
					curr_key = parent_key + "." + entry["Group"] if parent_key else entry["Group"]
					if curr_key == key:
						return collect_all_bones(entry["Contents"])
					else:
						bones.extend(collect_bones(entry["Contents"], key, curr_key))
			return bones

		def collect_all_bones(contents):
			collected = []
			for entry in contents:
				if isinstance(entry, dict):
					collected.extend(collect_all_bones(entry["Contents"]))
				elif isinstance(entry, list):
					collected.extend(entry)
				else:
					collected.append(entry)
			return collected

		bones_to_select = collect_bones(hierarchy, self.group_key)
		if not bones_to_select:
			self.report({'WARNING'}, f"No bones found for group {self.group_key}")
			return {'CANCELLED'}

		for b in armature.data.bones:
			b.select = (b.name in bones_to_select)

		if bones_to_select:
			armature.data.bones.active = armature.data.bones.get(bones_to_select[0])

		return {'FINISHED'}

classes = [
	BoneSelectorProps,
	POSE_OT_collapse_all_groups,
	VIEW3D_PT_fuzzy_bone_selector,
	POSE_OT_select_bone_named,
	POSE_OT_toggle_group,
	POSE_OT_select_group,
	POSE_OT_solo_group
]

def register():
	for cls in classes:
		bpy.utils.register_class(cls)
	bpy.types.Scene.fuzzy_bone_selector = bpy.props.PointerProperty(type=BoneSelectorProps)


def unregister():
	for cls in reversed(classes):
		bpy.utils.unregister_class(cls)
	del bpy.types.Scene.fuzzy_bone_selector


if __name__ == "__main__":
	register()
