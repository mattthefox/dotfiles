import bpy
import random
from . import utils

class ANIM_OT_collapse_all_collections(bpy.types.Operator):
	"""Collapse All Collections"""
	bl_idname = "wm.collapse_all_collections"
	bl_label = "Collapse All Collections"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		self.toggle_collection_collapse(2, context)
		return {'FINISHED'}
	
	# Credit to iceythe on BlenderArtists
	# https://blenderartists.org/t/question-regarding-expanding-collapsing-collection-in-outliner-in-2-8/1175242/2
	# Additional credit to hadit on BlenderArtists for the fix of iceythe's code.

	def toggle_collection_collapse(self, state, context):
		# Find the Outliner area
		area = next((a for a in context.screen.areas if a.type == 'OUTLINER'), None)
		if not area:
			self.report({'WARNING'}, "Outliner area not found")
			return {'CANCELLED'}

		region = next((r for r in area.regions if r.type == 'WINDOW'), None)
		if not region:
			self.report({'WARNING'}, "Outliner region not found")
			return {'CANCELLED'}

		with context.temp_override(area=area, region=region):
			bpy.ops.outliner.show_hierarchy('INVOKE_DEFAULT')
			for _ in range(state):
				bpy.ops.outliner.expanded_toggle()
			area.tag_redraw()


	"""
	def toggle_collection_collapse(self, state, context):
		area = next(a for a in bpy.context.screen.areas if a.type == 'OUTLINER')

		with context.temp_override(area=area):
			bpy.ops.outliner.show_hierarchy('INVOKE_DEFAULT')
			for i in range(state):
				bpy.ops.outliner.expanded_toggle()
			area.tag_redraw()
	"""

class ANIM_OT_rename_nearest_marker(bpy.types.Operator):
	"""Rename the nearest marker"""
	bl_idname = "anim.rename_nearest_marker"
	bl_label = "Rename Nearest Marker"
	bl_options = {'REGISTER', 'UNDO'}
	bl_property = "marker_name"

	marker_name: bpy.props.StringProperty(
		name="Marker Name",
		description="New name for the nearest marker",
		default="Marker"
	)

	def nearestMarker(self, context):
		scene = context.scene
		current_frame = scene.frame_current

		nearest_marker = None
		min_distance = float('inf')

		for marker in scene.timeline_markers:
			distance = abs(marker.frame - current_frame)
			if distance < min_distance:
				min_distance = distance
				nearest_marker = marker

		# Rename the nearest marker
		if nearest_marker:
			return nearest_marker
		else:
			return None

	def execute(self, context):
		nearest_marker = self.nearestMarker(context)
		if nearest_marker is not None:
			nearest_marker.name = self.marker_name
			self.report({'INFO'}, f"Marker renamed to {self.marker_name}")
		else:
			self.report({'WARNING'}, "No marker found to rename")

		return {'FINISHED'}

		
	def invoke(self, context, event):
		nearest_marker = self.nearestMarker(context)
		if nearest_marker is not None:
			self.marker_name = nearest_marker.name
		return context.window_manager.invoke_props_dialog(self)

class ANIM_OT_RefreshDriver(bpy.types.Operator):
	bl_label = "Refresh Driver"
	bl_idname = "zephkit.refresh_driver"

	def execute(self, context):
		bpy.ops.anim.copy_driver_button()
		bpy.ops.anim.driver_button_remove(all=True)
		bpy.ops.anim.paste_driver_button()

		return {'FINISHED'}

class ANIM_OT_NLAFrameSkipOperator(bpy.types.Operator):
	"""Skip to Start or End of NLA Strips"""
	bl_idname = "nla.frame_skip"
	bl_label = "Skip NLA Frames"
	
	direction: bpy.props.EnumProperty(
		items=[
			('PREV', "Previous", "Go to the start of the previous strip"),
			('NEXT', "Next", "Go to the end of the next strip")
		]
	)
	
	@staticmethod
	def get_closest_strip(context, current_frame, direction):
		nla_tracks = context.object.animation_data.nla_tracks
		all_strips = [strip for track in nla_tracks for strip in track.strips]
		
		if direction == 'PREV':
			strips = [strip for strip in all_strips if strip.frame_start < current_frame]
			return max(strips, key=lambda s: s.frame_start, default=None)
		elif direction == 'NEXT':
			strips = [strip for strip in all_strips if strip.frame_end > current_frame]
			return min(strips, key=lambda s: s.frame_end, default=None)
	
	def execute(self, context):
		current_frame = context.scene.frame_current
		strip = self.get_closest_strip(context, current_frame, self.direction)
		
		if not strip:
			self.report({'INFO'}, "No suitable NLA strip found.")
			return {'CANCELLED'}
		
		if self.direction == 'PREV':
			context.scene.frame_current = int(strip.frame_start)
		elif self.direction == 'NEXT':
			context.scene.frame_current = int(strip.frame_end)
		
		return {'FINISHED'}

class ANIM_OT_ZJumpToKeyframe(bpy.types.Operator):
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
		for fcurve in utils.fcurves_all(action):
			for keyframe_point in fcurve.keyframe_points:
				prevSelect[keyframe_point] = [keyframe_point.select_control_point, keyframe_point.select_left_handle, keyframe_point.select_right_handle]
				keyframe_point.select_control_point = False
				keyframe_point.select_left_handle = False
				keyframe_point.select_right_handle = False

		area = next(a for a in bpy.context.screen.areas if a.type == 'DOPESHEET_EDITOR')

		if area:
			with context.temp_override(area=area):
				bpy.ops.action.select_all(action='SELECT')
			for fcurve in utils.fcurves_all(action):
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
			for fcurve in utils.fcurves_all(action):
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

class ANIM_OT_CutKeyframe(bpy.types.Operator):
	bl_idname = "screen.cut_keyframe"
	bl_label = "Cut Keyframes"

	def execute(self, context):
		bpy.ops.action.copy()
		bpy.ops.action.delete()
		return {'FINISHED'}

class ANIM_OT_QuickNewAction(bpy.types.Operator):
	bl_idname = "zephkit.quick_new_action"
	bl_label = "Quick New Action"

	blending: bpy.props.EnumProperty(name="Blend Mode",default=0,
		items = [
			('ADD','Additive',''), 
			('REP','Replace',''),
		 ]
	)

	def execute(self, context):
		obj = context.object
		prevArea = context.area.type
		context.area.type = "NLA_EDITOR"
		if obj.animation_data:
			activeTrack =obj.animation_data.nla_tracks.active
			selectedStrip = None
			for strip in activeTrack.strips: 
				if strip.active:
					selectedStrip = strip

			if selectedStrip:
				existingAdditive = None
				bpy.ops.nla.tracks_add(above_selected=True)
				track = obj.animation_data.nla_tracks.active
				# track.name = "Additive" if self.blending == 'ADD' else "Replace"
				# create a new action
				action = selectedStrip.action.copy()
				action.name = context.object.name +"_"+track.name
				# delete the modifiers. (they confused the fuck out of me as well)
				for fcurve in utils.fcurves_all(action):
					for modifier in fcurve.modifiers:
						fcurve.modifiers.remove(modifier)
				# disable these to prevent the confusion that i suffered.
				#bpy.data.actions.new(context.object.name +"_"+track.name)
				prevAction = obj.animation_data.action
				# clear the keyframes
				for fcurve in utils.fcurves_all(action):
					fcurve.keyframe_points.clear()
				if self.blending == 'ADD':
					for fcurve in utils.fcurves_all(action):
						fcurve.keyframe_points.insert(context.scene.frame_current,0)
				else:
					obj.animation_data.action = action
					old_type = bpy.context.area.type
					bpy.context.area.type = "DOPESHEET_EDITOR"
					bpy.ops.action.keyframe_insert(type = 'ALL')
					bpy.context.area.type = old_type
					obj.animation_data.action = prevAction

				# add the action to the track.
				strip = track.strips.new(track.name,context.scene.frame_current,action)
				strip.blend_type = 'ADD' if self.blending == 'ADD' else 'REPLACE'
			context.area.type = prevArea

		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

class ANIM_OT_RandomizeCurveIndices(bpy.types.Operator):
	bl_idname = "zephkit.randomize_curve_indices"
	bl_label = "Select Random Curve Point"
	bl_options = {'REGISTER', 'UNDO'}

	def execute(self, context):
		baseObj = context.active_object
		
		if baseObj is None or baseObj.type != 'CURVE':
			self.report({'WARNING'}, "Active object is not a curve")
			return {'CANCELLED'}
		
		for x in range(5):
			new_collection = bpy.data.collections.new("TemporaryCollection")
			bpy.context.scene.collection.children.link(new_collection)
			new_collection.objects.link(baseObj)

			bpy.ops.object.mode_set(mode='EDIT')
			bpy.ops.curve.select_all(action='DESELECT')
			bpy.ops.curve.select_random(ratio=0.1)
			bpy.ops.curve.select_linked()
			bpy.ops.curve.separate()

			bpy.ops.object.mode_set(mode='OBJECT')
			bpy.ops.object.select_all(action='DESELECT')
			for obj in new_collection.objects:
				obj.select_set(True)
			bpy.context.view_layer.objects.active = baseObj
			bpy.ops.object.join()
			bpy.data.collections.remove(new_collection)
		
		return {'FINISHED'}

class ANIM_OT_TweakAll(bpy.types.Operator):
	"""Enter or Exit Tweak Mode on all objects"""
	bl_idname = "zephkit.tweak_mode_all"
	bl_label = "Toggle Tweak Mode for All"
	bl_options = {'REGISTER', 'UNDO'}

	enter: bpy.props.BoolProperty(name="Enter Tweak Mode", default=True)
	only_loops: bpy.props.BoolProperty(name="Only ZephKit Loops", default=False)

	def execute(self, context):
		original_active = bpy.context.view_layer.objects.active
		original_object = context.object
		original_area_type = context.area.type
		context.area.type = 'NLA_EDITOR'

		for obj in bpy.data.objects:
			# Checks to avoid errors.
			if obj.name not in context.scene.objects:
				continue
			# Linked from elsewhere
			if obj.library is not None:
				continue
			# Not visible in view layer
			if obj.name not in context.view_layer.objects:
				continue
			# Has no animation data
			if not obj.animation_data:
				continue

			try:
				bpy.context.view_layer.objects.active = obj
				obj.select_set(True)
				anim_data = obj.animation_data
				active_action = anim_data.action
				tweak_storage_before = anim_data.action_tweak_storage
				tweak_mode_enabled = True
			except RuntimeError:
				continue;

			# Blender doesn't directly give us NLA info so let's just check if it would allow us to enter tweak mode.
			if bpy.ops.nla.tweakmode_enter.poll():
				tweak_mode_enabled = False
			else:
				tweak_mode_enabled = True

			if self.enter: # If we want to begin tweaking all actions...
				if not tweak_mode_enabled: # If tweak mode wasn't already enabled, tweak!
					bpy.ops.nla.tweakmode_enter(use_upper_stack_evaluation=True)
			else: # If we want to exit tweak mode for all actions...
				if tweak_mode_enabled: # If tweak mode was already enabled, exit!
					bpy.ops.nla.tweakmode_exit()
			obj.select_set(False)

		# Restore original state
		context.area.type = original_area_type
		bpy.context.view_layer.objects.active = original_active
		
		original_object.select_set(True)
		return {'FINISHED'}


def register():
	bpy.utils.register_class(ANIM_OT_tweak_mode_all)
	bpy.ops.anim.tweak_mode_all(enter=False)

def unregister():
	bpy.utils.unregister_class(ANIM_OT_tweak_mode_all)

if __name__ == "__main__":
	register()


modules = [
	ANIM_OT_ZJumpToKeyframe,
	ANIM_OT_collapse_all_collections,
	ANIM_OT_RefreshDriver,
	ANIM_OT_rename_nearest_marker,
	ANIM_OT_NLAFrameSkipOperator,
	ANIM_OT_CutKeyframe,
	ANIM_OT_QuickNewAction,
	ANIM_OT_RandomizeCurveIndices,
	ANIM_OT_TweakAll
]

addon_keymaps = []

def register():
	for module in modules:
		bpy.utils.register_class(module)

def unregister():
	for module in reversed(modules):
		bpy.utils.unregister_class(module)