import bpy

class ZJumpToKeyframe(bpy.types.Operator):
	bl_idname = "screen.zjump_to_keyframe"
	bl_label = "Jump to Keyframe (Z)"

	direction: bpy.props.BoolProperty(name="Right?")

	def execute(self, context):
		action = bpy.context.object.animation_data.action
		if action is None:
			self.report({'WARNING'}, "No active action")
			return {'CANCELLED'}
		keyframes = []
		prevSelect = {}
		# store selection state and then deselect manually.
		for fcurve in action.fcurves:
			for keyframe_point in fcurve.keyframe_points:
				prevSelect[keyframe_point] = [keyframe_point.select_control_point, keyframe_point.select_left_handle, keyframe_point.select_right_handle]
				keyframe_point.select_control_point = False
				keyframe_point.select_left_handle = False
				keyframe_point.select_right_handle = False

		area = next(a for a in bpy.context.screen.areas if a.type == 'DOPESHEET_EDITOR')

		if area:
			with context.temp_override(area=area):
				bpy.ops.action.select_all(action='SELECT')
			for fcurve in action.fcurves:
				for keyframe_point in reversed(fcurve.keyframe_points) if self.direction else fcurve.keyframe_points:
					if keyframe_point.select_control_point:
						if self.direction:
							if keyframe_point.co.x > bpy.context.scene.frame_current:
								keyframes.append(keyframe_point.co.x)
							else:
								break
						else:
							if keyframe_point.co.x < bpy.context.scene.frame_current:
								keyframes.append(keyframe_point.co.x)
							else:
								break
			for fcurve in action.fcurves:
				for keyframe_point in fcurve.keyframe_points:
					if keyframe_point in prevSelect:
						keyframe_point.select_control_point = prevSelect[keyframe_point][0]
						keyframe_point.select_left_handle = prevSelect[keyframe_point][1]
						keyframe_point.select_right_handle = prevSelect[keyframe_point][2]
			prevFrame = context.scene.frame_current;
			if keyframes:
				bpy.context.scene.frame_current = int(min(keyframes) if self.direction else max(keyframes))
				if context.scene.frame_current == prevFrame:
					bpy.ops.screen.keyframe_jump(next=self.direction)
				return {'FINISHED'}
			else:
				if context.scene.frame_current == prevFrame:
					bpy.ops.screen.keyframe_jump(next=self.direction)
				return {'CANCELLED'}
		else:
			return {'CANCELLED'}

modules = [
	ZJumpToKeyframe,
]

addon_keymaps = []

def register():
	for module in modules:
		bpy.utils.register_class(module)

def unregister():
	for module in reversed(modules):
		bpy.utils.unregister_class(module)

if __name__ == "__main__":
	register()