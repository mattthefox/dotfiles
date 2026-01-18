bl_info = {
	"name": "Lapser",
	"author": "azephynight",
	"version": (1, 1, 0),
	"blender": (4, 0, 0),
	"location": "Dope Sheet > Sidebar (N) > Lapser",
	"description": "Insert empty animation space after the current frame, shifting all animation data",
	"category": "Animation",
}

import bpy

def fcurves_all(action):
	BLENDER_VERSION = 5
	fcurves = None
	if BLENDER_VERSION == 5:
		for layer in action.layers:
			strips = layer.strips
			for strip in strips:
				for bag in strip.channelbags:
					fcurves = bag.fcurves
					break;break;break;
	else:
		fcurves = action.fcurves
	return fcurves

def get_shift_preview(frame, offset):
    preview = {"nla_strips": [], "actions": [], "markers": [],
               "scene_range": (), "preview_range": (), 
               "baker_frames": [], "physics": []}

    # NLA strips
    for obj in bpy.data.objects:
        ad = obj.animation_data
        if not ad or not ad.nla_tracks:
            continue
        for track in ad.nla_tracks:
            for strip in track.strips:
                if strip.frame_start > frame:
                    preview["nla_strips"].append(
                        f"{obj.name}: {strip.name} → {strip.frame_start + offset}"
                    )

    # Loose actions (not in NLA)
    nla_actions = {strip.action for obj in bpy.data.objects if obj.animation_data
                   for track in obj.animation_data.nla_tracks
                   for strip in track.strips if strip.action}

    for action in bpy.data.actions:
        if action not in nla_actions:
            preview["actions"].append(
                f"{action.name} → keys after {frame} shifted by {offset}"
            )

    # Markers
    for m in bpy.context.scene.timeline_markers:
        if m.frame > frame:
            preview["markers"].append(f"{m.name} → {m.frame + offset}")

    # Scene frame range
    scene = bpy.context.scene
    start = scene.frame_start + offset if scene.frame_start > frame else scene.frame_start
    end = scene.frame_end + offset if scene.frame_end > frame else scene.frame_end
    preview["scene_range"] = (start, end)

    # Preview range
    if scene.use_preview_range:
        start = scene.frame_preview_start + offset if scene.frame_preview_start > frame else scene.frame_preview_start
        end = scene.frame_preview_end + offset if scene.frame_preview_end > frame else scene.frame_preview_end
        preview["preview_range"] = (start, end)

    # Baker frames
    for obj in bpy.data.objects:
        if hasattr(obj, "baker_frame") and obj.baker_frame > frame:
            preview["baker_frames"].append(f"{obj.name}: {obj.baker_frame + offset}")

    # Physics
    rbw = scene.rigidbody_world
    if rbw and rbw.point_cache.frame_start > frame:
        preview["physics"].append(f"RigidBodyWorld → {rbw.point_cache.frame_start + offset}")

    for obj in scene.objects:
        if obj.rigid_body and obj.rigid_body.start_frame > frame:
            preview["physics"].append(f"{obj.name} RigidBody → {obj.rigid_body.start_frame + offset}")
        for mod in obj.modifiers:
            pc = getattr(mod, "point_cache", None)
            if pc and pc.frame_start > frame:
                preview["physics"].append(f"{obj.name} {mod.name} Cache → {pc.frame_start + offset}")
        for ps in obj.particle_systems:
            if ps.settings.frame_start > frame:
                preview["physics"].append(f"{obj.name} Particle → {ps.settings.frame_start + offset}")

    return preview


# ------------------------------------------------------------
# Action / F-Curve shifting
# ------------------------------------------------------------

def shift_fcurves(action, frame, offset):
	for fcu in fcurves_all(action):
		for kp in fcu.keyframe_points:
			if kp.co.x > frame:
				kp.co.x += offset
				kp.handle_left.x += offset
				kp.handle_right.x += offset
		fcu.update()


def shift_all_actions(frame, offset):
    nla_actions = {strip.action for obj in bpy.data.objects if obj.animation_data
                   for track in obj.animation_data.nla_tracks
                   for strip in track.strips if strip.action}

    for action in bpy.data.actions:
        if action not in nla_actions:
            shift_fcurves(action, frame, offset)


# ------------------------------------------------------------
# NLA
# ------------------------------------------------------------

def shift_nla_strips(frame, offset):
	for obj in bpy.data.objects:
		ad = obj.animation_data
		if not ad or not ad.nla_tracks:
			continue

		for track in ad.nla_tracks:
			for strip in track.strips:
				if strip.frame_start > frame:
					strip.frame_start += offset
					strip.frame_end += offset


# ------------------------------------------------------------
# Markers
# ------------------------------------------------------------

def shift_markers(scene, frame, offset):
	for m in scene.timeline_markers:
		if m.frame > frame:
			m.frame += offset


# ------------------------------------------------------------
# Scene frame ranges
# ------------------------------------------------------------

def shift_scene_range(scene, frame, offset):
	if scene.frame_start > frame:
		scene.frame_start += offset
	if scene.frame_end > frame:
		scene.frame_end += offset


def shift_preview_range(scene, frame, offset):
	if not scene.use_preview_range:
		return

	if scene.frame_preview_start > frame:
		scene.frame_preview_start += offset

	if scene.frame_preview_end > frame:
		scene.frame_preview_end += offset


# ------------------------------------------------------------
# Custom properties
# ------------------------------------------------------------

def shift_baker_frame(frame, offset):
	for obj in bpy.data.objects:
		if hasattr(obj, "baker_frame"):
			if obj.baker_frame > frame:
				obj.baker_frame += offset


# ------------------------------------------------------------
# Physics / simulation start frames
# ------------------------------------------------------------

def shift_physics(scene, frame, offset):
	# Rigid body world
	rbw = scene.rigidbody_world
	if rbw and rbw.point_cache.frame_start > frame:
		rbw.point_cache.frame_start += offset

	for obj in scene.objects:
		# Rigid body
		if obj.rigid_body:
			if obj.rigid_body.start_frame > frame:
				obj.rigid_body.start_frame += offset

		# Modifiers with caches
		for mod in obj.modifiers:
			pc = getattr(mod, "point_cache", None)
			if pc and pc.frame_start > frame:
				pc.frame_start += offset

		# Particle systems
		for ps in obj.particle_systems:
			if ps.settings.frame_start > frame:
				ps.settings.frame_start += offset


# ------------------------------------------------------------
# Operator
# ------------------------------------------------------------

class LAPSER_OT_insert_gap(bpy.types.Operator):
	bl_idname = "lapser.insert_gap"
	bl_label = "Insert Animation Gap"
	bl_description = "Insert empty animation space after the current frame"
	bl_options = {'UNDO'}

	frames: bpy.props.IntProperty(
		name="Frames to insert:",
		default=10,
		min=1
	)

	show_all: bpy.props.BoolProperty(
		name="Expand list",
		default=False
	)

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

	def draw(self, context):
		layout = self.layout
		col = layout.column(align=True)

		col.prop(self, "frames")
		col.prop(self, "show_all")

		preview = get_shift_preview(context.scene.frame_current, self.frames)

		show_amount = -1 if self.show_all else 5

		if preview["nla_strips"]:
			col.label(text="NLA Strips:")
			for line in preview["nla_strips"][:show_amount]:
				col.label(text="  " + line)

		if preview["actions"]:
			col.label(text="Actions:")
			for line in preview["actions"][:show_amount]:
				col.label(text="  " + line)

		if preview["markers"]:
			col.label(text="Markers:")
			for line in preview["markers"][:show_amount]:
				col.label(text="  " + line)

		col.label(text=f"Scene Frame Range → {preview['scene_range']}")
		if preview["preview_range"]:
			col.label(text=f"Preview Range → {preview['preview_range']}")
		if preview["baker_frames"]:
			col.label(text="Baker Frames:")
			for line in preview["baker_frames"][:show_amount]:
				col.label(text="  " + line)
		if preview["physics"]:
			col.label(text="Physics / Simulation Start Frames:")
			for line in preview["physics"][:show_amount]:
				col.label(text="  " + line)


	def execute(self, context):
		scene = context.scene
		frame = scene.frame_current
		offset = self.frames

		# 1️⃣ Shift NLA strips first (so strips move as containers)
		shift_nla_strips(frame, offset)

		# 2️⃣ Shift actions next (F-Curves inside actions)
		# Optional: skip actions already referenced by NLA strips to avoid double-shift
		shift_all_actions(frame, offset)

		# 3️⃣ Shift everything else
		shift_markers(scene, frame, offset)
		shift_scene_range(scene, frame, offset)
		shift_preview_range(scene, frame, offset)
		shift_baker_frame(frame, offset)
		shift_physics(scene, frame, offset)

		self.report({'INFO'}, f"Inserted {offset} frames after frame {frame}")
		return {'FINISHED'}


# ------------------------------------------------------------
# UI Panel
# ------------------------------------------------------------

class LAPSER_PT_panel(bpy.types.Panel):
	bl_label = "Lapser"
	bl_space_type = 'DOPESHEET_EDITOR'
	bl_region_type = 'UI'
	bl_category = "Lapser"

	def draw(self, context):
		layout = self.layout
		col = layout.column(align=True)

		col.label(text="Insert Animation Space")
		col.operator("lapser.insert_gap")


# ------------------------------------------------------------
# Registration
# ------------------------------------------------------------

classes = (
	LAPSER_OT_insert_gap,
	LAPSER_PT_panel,
)


def register():
	for c in classes:
		bpy.utils.register_class(c)


def unregister():
	for c in reversed(classes):
		bpy.utils.unregister_class(c)


if __name__ == "__main__":
	register()
