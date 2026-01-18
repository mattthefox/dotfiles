import bpy

class ANIM_OT_MakeSpace(bpy.types.Operator):
	"""Rename the nearest marker"""
	bl_idname = "anim.make_space"
	bl_label = "Make Space"
	bl_options = {'REGISTER', 'UNDO'}

	offset: bpy.props.FloatProperty(
		name="Offset",
		description="How much space to free up?",
	)

	def execute(self, context):
		"""
			Properties we must adjust:
			Keyframe times: Adjust offset to times that are greater than the cursor position.
			Frame End: Add offset
			Cloth simulation end: Add offset
			Particle simulation end: Add offset
			Loop end and loop starts: Add offset for relevant ACTION START TIMES greater than the cursor position
		"""

		scene = context.scene
		cursor_frame = scene.frame_current
		offset_int = int(self.offset)

		# Adjust frame range
		scene.frame_end += offset_int

		# Adjust keyframe times
		for obj in bpy.data.objects:
			for modifier in obj.modifiers:
				if modifier.type == 'CLOTH' and modifier.point_cache:
					if modifier.point_cache.frame_end >= cursor_frame:
						modifier.point_cache.frame_end += offset_int
					if modifier.point_cache.frame_start >= cursor_frame:
						modifier.point_cache.frame_start += offset_int
			for ps in obj.particle_systems:
				if ps.settings.frame_end >= cursor_frame:
					ps.settings.frame_end += offset_int
				if ps.settings.frame_start >= cursor_frame:
					ps.settings.frame_start += offset_int

							
		# Adjust action loop start and end times
		for action in bpy.data.actions:
			for fcurve in action.fcurves:
				for keyframe in fcurve.keyframe_points:
					if keyframe.co[0] >= cursor_frame:
						keyframe.co[0] += self.offset
			if action.frame_start > cursor_frame:
				action.loop_end += self.offset
				action.loop_start += self.offset

		prevArea = context.area.type
		context.area.type = "NLA_EDITOR"

		# iterate over actions starting from the furthest and sync length.
		for obj in bpy.data.objects:
			if obj.name in bpy.context.view_layer.objects:
				if obj.animation_data and obj.animation_data.nla_tracks:
					context.view_layer.objects.active = obj
					for track in obj.animation_data.nla_tracks:
						for strip in reversed(sorted(track.strips, key=lambda x: x.frame_end)):
							if strip.frame_start >= cursor_frame:
								bpy.ops.nla.select_all(action='DESELECT')
								strip.select = True
								bpy.ops.nla.action_sync_length()
								#strip.frame_end_ui += offset_int
		context.area.type = prevArea

		bpy.ops.wm.update_time_for_speed()

		self.report({'INFO'}, f"Space of {self.offset} frames created.")
		return {'FINISHED'}

modules = [
	ANIM_OT_MakeSpace
]

# Register the menu and update the header
def register():
	for cls in modules:
		bpy.utils.register_class(cls)
	
def unregister():
	for cls in reversed(modules):
		bpy.utils.unregister_class(cls)