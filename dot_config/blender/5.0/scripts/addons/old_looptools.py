bl_info = {
	'name': 'ZephKit Loop Tools old',
	'author': 'azephynight',
	'description': 'Helpful tools for animation!',
	'blender': (4, 1, 0),
	'version': (1, 0, 0),
	'location': 'View3D',
	'category': 'Animation',
}

import pprint
from collections import Counter, defaultdict
import bpy
from bpy.props import StringProperty, IntProperty, CollectionProperty, PointerProperty, BoolProperty, EnumProperty, FloatProperty
from perlin_noise import PerlinNoise
from mutagen.wave import WAVE  # Replace with appropriate format if not mp3
import os
import random
from math import log10
import sys
sys.path.append('/home/mantra/myenv/lib/python3.13/site-packages')

ANIMATED_SPEED_ACTION = "ANIMATED SPEED"
ANIMATED_SPEED_FCURVE = "animated_speed"
ANIMATED_INTENSITY_FCURVE = "animated_intensity"

FULLBLOCK = "█"

### PROPERTY UPDATE FUNCTIONS.
def PROP_getFrameStart(self):
	action_data = bpy.context.object.animation_data
	if not action_data or not action_data.action:
		return -1
	
	action = action_data.action

	# Check if linked_loop exists and is valid
	linked_loop = action.linked_loop
	if linked_loop is None or not str(linked_loop).isdigit():
		return -1

	# Ensure linked_loop is an integer and is within bounds
	linked_loop_index = int(linked_loop)
	if linked_loop_index < 0 or linked_loop_index >= len(bpy.context.scene.loop_list):
		return -1

	loop = bpy.context.scene.loop_list[linked_loop_index]
	return updateAction(bpy.context, [action])[0]
def PROP_update_intensities(self, context):
	IGNORE_PROPERTIES = [ # Properties containing these substrings will not be considered for Intensity. (Butt Ripples, Breath value, Blush value. Pretty much everything besides bones.)
		"move",
		"breath",
		"blush",
		"grip",
		"ripple"
	]

	def loopCondition(loop):
		return True
	loopData = constructListofLoopPoints(self, context, loopCondition, True)
	print(loopData)
	infoDict = action_info(all_objects(), context)
	scene = context.scene

	# Retrieve or create the animated intensity curve.
	action_name = ANIMATED_SPEED_ACTION
	action = bpy.data.actions.get(action_name) or bpy.data.actions.new(name=action_name)
	print(f"Using action: {action_name}")

	intensityCurve = None
	for fc in action.fcurves:
		if fc.data_path == ANIMATED_INTENSITY_FCURVE:
			intensityCurve = fc
			break
	if not intensityCurve:
		intensityCurve = action.fcurves.new(data_path=ANIMATED_INTENSITY_FCURVE, index=0)
		intensityCurve.keyframe_points.add(1)
		intensityCurve.keyframe_points[0].co = (0.0, 1.0)  # Default keyframe

	# Assign the action to the scene if not already assigned
	if not scene.animation_data:
		scene.animation_data_create()
	if scene.animation_data.action != action:
		scene.animation_data.action = action

	# Remove any existing actions containing "zk_overlay"
	for existing_action in bpy.data.actions:
		if "zk_overlay" in existing_action.name:
			bpy.data.actions.remove(existing_action)

	cleared = {} # A dictionary storing flags if the NLA strips were cleared for each object
	
	for info in infoDict:
		overlay_track = None
		obj = info["object"]
		track = info["track"]
		strip = info["strip"]
		loopIndex = info["loop"]
		loop = info["loopObject"]

		# Validation
		if not obj or not obj.animation_data or not obj.animation_data.nla_tracks:
			continue
		if not track or track.name not in obj.animation_data.nla_tracks:
			continue
		if not strip or strip.name not in track.strips:
			continue
		if not strip.action:
			continue
		if not loop:
			continue
		
		if strip.action.use_intensity:
			nla_tracks = obj.animation_data.nla_tracks
			track.select = True
			
			# Check if an overlay track exists
			for t in nla_tracks:
				if "zk_overlay" in t.name.lower():
					overlay_track = t
					break
			
			if not overlay_track:
				overlay_track = nla_tracks.new()
				overlay_track.name = f"zk_overlay_{track.name}"
			
			newStripName = f"{FULLBLOCK*4}strip.name" # for visual distinction.
			# Remove all strips on the track before adding them back, if they haven't been removed from this object already
			if obj not in cleared:
				for track_strip in overlay_track.strips:
					overlay_track.strips.remove(track_strip)
				cleared[obj] = True
				
			# Create a new action for the overlay, excluding ignored properties and with only first frame.
			overlay_action = bpy.data.actions.new(name=f"zk_overlay_{strip.action.name}")
			overlay_action.linked_loop = 'None'
			print(f"Creating new action: {overlay_action.name}")

			# Copy relevant fcurves from the original action to the new overlay action
			for fc in strip.action.fcurves:
				# Exclude the properties in IGNORE_PROPERTIES
				if any(ignore.lower() in fc.data_path.lower() for ignore in IGNORE_PROPERTIES):
					continue
				
				new_fc = overlay_action.fcurves.new(
					data_path=fc.data_path, 
					index=fc.array_index
				)
				for keyframe in fc.keyframe_points:
					new_fc.keyframe_points.insert(
						frame=keyframe.co[0], 
						value=keyframe.co[1], 
						options={'FAST'}
					)
			
			try:
				new_strip = overlay_track.strips.new(
					name=newStripName,
					start=int(strip.frame_start),
					action=overlay_action
				)
			except RuntimeError:
				continue
			new_strip.name = newStripName # so it's visually distinct
			new_strip.frame_end = strip.frame_end
			new_strip.action_frame_start = strip.action_frame_start
			new_strip.action_frame_end = strip.action_frame_end
			new_strip.blend_type = 'REPLACE'
			extrap_mapping = {
				"NOTHING": "NOTHING",
				"HOLD_FORWARD": "NOTHING",
				"HOLD": "HOLD_FORWARD"
			}
			new_strip.extrapolation = extrap_mapping[strip.extrapolation]
			
			# Force the overlay strip to always play only the first frame.
			new_strip.use_animated_time = True
			new_strip.use_animated_influence = True
			# Use the resting frame as an offset.
			new_strip.strip_time = new_strip.action_frame_start + loop.rest_frame
			# Retrieve or create the strip_time F-curve
			timeCurve = new_strip.fcurves.find('strip_time')
			influenceCurve = new_strip.fcurves.find("influence")

			timeCurve.keyframe_points.insert(frame=new_strip.frame_start, value=new_strip.action_frame_start + loop.rest_frame)
			loopFrames = loopData[loopIndex]
			# Now bake all of it.
			for frame in range(int(new_strip.frame_start), int(new_strip.frame_end) + 1):
				# Sample the existing fcurve value at the given frame
				sampled_value = intensityCurve.evaluate(frame)
				# Offset this by a random value, with the nearest frame in loopData array being the seed.
				# Find the nearest previous frame in loopData
				previous_frames = [f for f in loopFrames if f <= frame]
				if previous_frames:
					seed_frame = max(previous_frames)  # Get the closest previous frame
					# Use this as seed for randomness
					random.seed(seed_frame)
					variation = random.uniform(0, 0.3 * loop.intensity_variation)
					# Apply variation.
					new_value = (1 - sampled_value) + variation
				else:
					new_value = 1 - sampled_value # keyframe how it was before.
				
				# Insert the sampled value as a new keyframe
				influenceCurve.keyframe_points.insert(frame=frame, value=new_value, options={'FAST'})
				keyframe = influenceCurve.keyframe_points[-1]  # Get the last inserted keyframe
				keyframe.interpolation = 'CONSTANT'  # Set interpolation to constant
def PROP_setFrameStart(self, value):
	# offset all keyframes by the delta value.

	offset = value - self.loop_start
	
	if not offset == 0:
		# This is the dumbest thing ive ever had to do. Why do bpy collections not have basic insert methods or list concatenation. Why
		actions = self.actions # dont modifiy original list
		active_action = bpy.context.object.animation_data.action
		for i, action in enumerate(actions):
			if action.action == active_action:		
				actions.remove(i) # remove
		# do the active action first
		for fcurve in active_action.fcurves:
			for keyframe in fcurve.keyframe_points:
				keyframe.co[0] += offset
			basic_update(bpy.context, active_action)
		# do the rest
		for loop in actions:
			action = loop.action
			for fcurve in action.fcurves:
				for keyframe in fcurve.keyframe_points:
					keyframe.co[0] += offset
			basic_update(bpy.context, action)
		new_action_item = actions.add()
		new_action_item.action = active_action
def PROP_getFrameEnd(self):
	action_data = bpy.context.object.animation_data
	if not action_data or not action_data.action:
		return -1
	
	action = action_data.action

	# Check if linked_loop exists and is valid
	linked_loop = action.linked_loop
	if linked_loop is None or not str(linked_loop).isdigit():
		return -1

	# Ensure linked_loop is an integer and is within bounds
	linked_loop_index = int(linked_loop)
	if linked_loop_index < 0 or linked_loop_index >= len(bpy.context.scene.loop_list):
		return -1

	loop = bpy.context.scene.loop_list[linked_loop_index]
	return updateAction(bpy.context, [action])[1]
def PROP_updateDuration(self, context):
	# Use negative to input an absolute frame.
	if (self.duration < 0):
		frame_end = abs(self.duration)
		self.duration = frame_end - self.loop_start

	for loop in self.actions:
		basic_update(context, loop.action, True)
def PROP_update_loop(self, context):
	action = context.object.animation_data.action
	if action:
		basic_update(context, action)
def PROP_setAudioPool(self, value):
	self.audio_pool = value.split("run/",1)[1] # trim before root folder to get rid of relative path nonsense
def PROP_link_action_to_loop(self, context):
	print("WORKING")
	scene = context.scene
	active_action = context.object.animation_data.action

	if not active_action:
		return

	# Fetch the loop using the loop_index passed
	loop = scene.loop_list[int(self.linked_loop)]

	# Check if action is already linked to this loop and unlink it
	for loop_item in scene.loop_list:
		for i, action_item in enumerate(loop_item.actions):
			if action_item.action == active_action:
				loop_item.actions.remove(loop_item.actions.find(action_item.name))  # Remove the action from the loop

	if not int(self.linked_loop) == -1: # dont set it if it's set to none
		# Now, link the action to the selected loop
		action_item = loop.actions.add()
		action_item.action = active_action
		PROP_updateDuration(loop, context)

### CUSTOM TYPES AND PROPERTIES.
def register_custom_properties():
	bpy.types.Scene.loop_list = CollectionProperty(type=SceneLoopProperties)
	bpy.types.Scene.zephkit_view_all_loops = BoolProperty(
		name="View All Loops",
		description="Toggle between scene-wide and action-specific loop views",
		default=False
	)
	bpy.types.Action.linked_loop = EnumProperty(
		name= "This action is linked to...",
		description= "Choose a loop to link the current action",
		items=get_loop_items,
		default=-1,
		update=PROP_link_action_to_loop
	)
	bpy.types.Action.use_intensity = BoolProperty(
		name= "Use Animated Intensity",
		description= "Use animated intensity? (This is per action.)",
		default=False,
		update=PROP_update_intensities
	)
	bpy.types.Action.loop_offset = IntProperty(
		name= "Offset",
		description= "Offset of this action from other loop actions",
		default=0,
		update = PROP_update_loop
	)
	bpy.types.Scene.animated_speed = FloatProperty(
		name="Speed",
		description= "The speed factor for this loop.",
		default=1.0,
		options={'LIBRARY_EDITABLE','ANIMATABLE'},
		override={'LIBRARY_OVERRIDABLE'},
		update = PROP_update_loop
	)
	bpy.types.Scene.animated_intensity = FloatProperty(
		name="Intensity",
		description= "The intensity factor for this loop.",
		default=1.0,
		options={'LIBRARY_EDITABLE','ANIMATABLE'},
		override={'LIBRARY_OVERRIDABLE'},
		update = PROP_update_intensities
	)
	bpy.types.Scene.animated_influence = FloatProperty(
		name="Animated Influence",
		description= "The influence factor for the current loop.",
		default=1.0,
		options={'LIBRARY_EDITABLE','ANIMATABLE'},
		override={'LIBRARY_OVERRIDABLE'},
		update = PROP_update_loop
	)
class ActionItem(bpy.types.PropertyGroup):
	action: PointerProperty(
		name="Action",
		type=bpy.types.Action,
		description="Pointer to an action"
	)

class SceneLoopProperties(bpy.types.PropertyGroup):
	name: StringProperty(name="Name",
		description="Name of the loop"
	)
	loop_start: IntProperty(name="Loop Start",
		description="Loop start point",
		default=0,
		get = PROP_getFrameStart,
		set = PROP_setFrameStart,
	)
	loop_end: IntProperty(name="Loop End",
		description="Loop end point",
		default=0,
		get = PROP_getFrameEnd,
	)
	duration: IntProperty(name="Duration",
		description="Duration of the loop. Input a negative value to specify the absolute end frame.",
		default=0,
		update = PROP_updateDuration
	)
	stepped: BoolProperty(name="Stepped Interpolation",
		description="Stepped interpolation",
		default=True,
		update = PROP_update_loop
	)
	use_animated_speed: BoolProperty(update = PROP_update_loop)
	use_intensity: BoolProperty(update = PROP_update_intensities)
	intensity_variation: FloatProperty(
		name="Variation",
		update = PROP_update_intensities,
		default=1.0
	)
	rest_frame: IntProperty(name="Rest Frame",
		description="Relative frame of the loop that is the 'resting' position that intensity variation will use.",
		default=0,
		update = PROP_update_intensities
	)
	
	audio_pool: StringProperty(
		name="Audio Pool Folder",
		description= "Folder to randomly select audio files from.",
		maxlen=1024,
		subtype='DIR_PATH',
	)
	audio_offset: IntProperty(
		name="Offset",
		description= "Offset for sound effect.",
		default = 0,
		#update = PROP_update_with_audio
	)
	audio_volume: FloatProperty(
		name="Gain",
		description= "Volume of audio.",
		default=1.0,
		soft_min=0,
		soft_max=2
	)
	audio_rate: FloatProperty(
		name="Rate",
		description= "Multiplier for loop sounds to occur.",
		default=1,
	)
	actions: CollectionProperty(type=ActionItem,
		name="Actions",
		description="List of actions assigned to this loop"
	)
def get_loop_items(self, context):
	scene = context.scene
	# Ensure the loops are always updated and return the correct items
	loop_items = [("None","None","",'QUESTION',-1)] # add default

	for i, loop in enumerate(scene.loop_list):
		loop_items.append((str(i), loop.name, "", 'ACTION', i))
	return loop_items

### AUDIO RELATED HELPER FUNCTIONS.
def PROP_update_with_audio(self, context):
	audio_update(self, context)
def constructListofLoopPoints(self, context, condition, use_all, use_rate=False):
	loopData = {}
	objects = all_objects() if use_all else [context.object]
	loop_info = action_info(objects, context)  # Get loop info on all objects
	located_loops = set()
	
	if not use_all:
		active_action = context.object.animation_data.action
		loop_info = [entry for entry in loop_info if entry["action"] == active_action]

	for info in loop_info:
		loop_index = int(info["loop"])
		if loop_index in located_loops:
			continue  # Skip already processed loops

		loop = context.scene.loop_list[loop_index]
		if not condition(loop):
			continue

		located_loops.add(loop_index)
		loopData[loop_index] = []

		frame_range = updateAction(context, [x.action for x in loop.actions])  # Get accurate loop points
		if not frame_range:
			continue

		loop_in = frame_range[0]
		loop_out = frame_range[1] - loop_in

		loop_out = (loop_out * loop.audio_rate) if use_rate else loop_out

		next_threshold, length = loop_in + loop.audio_offset, loop_out
		current_frame, end = loop_in, loop_in + loop.duration
		strip = info["strip"]

		if strip.use_animated_time:
			fcurve = strip.fcurves.find("strip_time")
			if fcurve:
				evaluate_curve = fcurve.evaluate  # Store method reference for speed
				while current_frame <= end:
					if evaluate_curve(current_frame) >= next_threshold:
						loopData[loop_index].append(current_frame)
						next_threshold += length
					current_frame += 1
		else:
			while current_frame <= end:
				if current_frame >= next_threshold:
					loopData[loop_index].append(current_frame)
					next_threshold += length
				current_frame += 1

	return loopData

import bpy
import os
import random
import subprocess
from math import log10
from perlin_noise import PerlinNoise

def audio_update(self, context, use_all=False):
    def loopCondition(loop):
        return bool(loop.audio_pool)

    def isAudioFile(f):
        return f.lower().endswith(('.mp3', '.wav'))

    data = constructListofLoopPoints(self, context, loopCondition, use_all, use_rate=True)
    if not data:
        return {'CANCELLED'}

    audio_data = []
    fps = context.scene.render.fps
    frame_end = context.scene.frame_end
    frame_start = context.scene.frame_start
    noise = PerlinNoise(octaves=50, seed=5)

    folder_files_cache = {}
    action_name = "ANIMATED SPEED"
    action = bpy.data.actions.get(action_name) or bpy.data.actions.new(name=action_name)
    intensityCurve = next((fc for fc in action.fcurves if fc.data_path == "animated_intensity"), None)

    total_steps = sum(len(points) for points in data.values()) + 1
    wm = context.window_manager
    wm.progress_begin(0, total_steps)
    progress_step = 0

    overlay_commands = []
    filter_complex_parts = []
    input_file_index = 0
    final_volume_filters = []

    for info, points in data.items():
        loop = context.scene.loop_list[info]
        folder_path = os.path.normpath(bpy.path.abspath(loop.audio_pool))

        if folder_path not in folder_files_cache:
            try:
                files = [
                    os.path.join(folder_path, f) for f in os.listdir(folder_path)
                    if os.path.isfile(os.path.join(folder_path, f)) and isAudioFile(f)
                ]
                folder_files_cache[folder_path] = files
            except Exception as e:
                print(f"Error accessing folder {folder_path}: {e}")
                continue

        files = folder_files_cache.get(folder_path, [])
        if not files:
            print(f"Empty or inaccessible folder: {folder_path}")
            continue

        for point in points:
            animated_intensity = min(intensityCurve.evaluate(point), 1) if intensityCurve else 1.0
            volume_offset = noise([(point * 0.5) / frame_end]) * 0.5
            total_volume = (loop.audio_volume * (1 + volume_offset)) * animated_intensity

            file_path = random.choice(files)
            start_time_sec = point / fps

            # ffmpeg input
            overlay_commands.extend(["-i", file_path])

            # Random pitch factor between 0.9 and 1.1
            pitch_factor = 1.0 + random.uniform(-0.1, 0.1)
            atempo = min(max(pitch_factor, 0.5), 2.0)  # limit for ffmpeg atempo

            volume_db = 20 * log10(total_volume) if total_volume > 0 else -60

            filter_complex_parts.append(
                f"[{input_file_index}:a] "
                f"atempo={atempo}, "
                f"volume={volume_db}dB, "
                f"adelay={int(start_time_sec * 1000)}|{int(start_time_sec * 1000)} "
                f"[a{input_file_index}]"
            )

            input_file_index += 1
            progress_step += 1
            wm.progress_update(progress_step)

    if not filter_complex_parts:
        wm.progress_end()
        print("No audio segments to process.")
        return {'CANCELLED'}

    filter_complex = "; ".join(filter_complex_parts)
    mix_inputs = "".join(f"[a{i}]" for i in range(input_file_index))
    filter_complex += f"; {mix_inputs}amix=inputs={input_file_index}:dropout_transition=0:normalize=0[aout]"

    output_path = os.path.join(bpy.path.abspath("//"), f"zanim_audio_render_{context.scene.name}.wav")

    ffmpeg_command = ["ffmpeg", "-y"] + overlay_commands + [
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "pcm_s16le",
        output_path
    ]

    print("Running ffmpeg command:")
    print(" ".join(ffmpeg_command))

    try:
        subprocess.run(ffmpeg_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"ffmpeg failed: {e}")
        wm.progress_end()
        return {'CANCELLED'}

    # Update VSE
    prev_area = bpy.context.area.type
    bpy.context.area.type = "SEQUENCE_EDITOR"

    seq = bpy.context.scene.sequence_editor
    if seq:
        bpy.ops.sequencer.select_all(action='DESELECT')
        for strip in seq.sequences_all:
            if strip.type == "SOUND" and strip.name == "zanim_render":
                strip.select = True
        bpy.ops.sequencer.delete()

    bpy.ops.sequencer.sound_strip_add(filepath=output_path, frame_start=frame_start)
    for strip in bpy.context.selected_sequences:
        strip.name = "zanim_render"

    bpy.context.area.type = prev_area
    wm.progress_end()
    print("Compiled audio exported successfully.")
    return {'FINISHED'}


### LOOP RELATED HELPER FUNCTIONS.
def updateAction(context, actions):
	# Get all F-curves from the action
	fcurves = []
	for action in actions:
		fcurves.extend(action.fcurves)
	total_channels = len(fcurves)
	if total_channels == 0:
		print("Action has no F-curve channels.")
		return None

	# Determine the majority threshold
	majority_threshold = total_channels / 2

	# Map frame numbers to the number of channels with keyframes
	frame_channel_map = defaultdict(set)  # Frame -> set of F-curve indices

	for i, fcurve in enumerate(fcurves):
		for keyframe in fcurve.keyframe_points:
			frame = round(keyframe.co[0])  # Frame number
			frame_channel_map[frame].add(i)  # Track the F-curve index for this frame

	# Identify frames with keyframes on a majority of channels
	majority_frames = [frame for frame, channels in frame_channel_map.items()
					   if len(channels) > majority_threshold]
	
	if not majority_frames:
		print("No frames have keyframes on a majority of the channels.")
		return None

	# Determine the loop start and end frames
	start_frame = min(majority_frames)
	end_frame = max(majority_frames)

	return start_frame, end_frame

def action_info(objects, context):
	info = []
	action_to_strips = {}

	# Step 1: Pre-create a mapping of object actions to strips.
	for obj in objects:
		anim_data = obj.animation_data
		if not anim_data or not anim_data.nla_tracks:
			continue

		for trackIndex, track in enumerate(anim_data.nla_tracks):
			if "zk_overlay" in track.name:
				continue
			for strip in track.strips:
				if FULLBLOCK in strip.name:
					continue
				action_to_strips.setdefault(strip.action, []).append((obj, track, strip, trackIndex))

	# Step 2: Gather loop info and match actions.
	for i, loop in enumerate(context.scene.loop_list):
		for a in loop.actions:
			if a.action in action_to_strips:
				info.extend(
					{
						"loop": i,
						"action": a.action,
						"object": obj,
						"track": track,
						"strip": strip,
						"trackIndex": trackIndex,
						"loopObject": loop,
					}
					for obj, track, strip, trackIndex in action_to_strips[a.action]
				)

	# Step 3: Filter out incomplete entries.
	return [entry for entry in info if None not in entry.values()]

def all_objects():
	ls = []
	for obj in bpy.data.objects:
		ls.append(obj)

	return ls

def update_time_for_speed(context):
	obj = context.object
	scene = context.scene
	action_name = "ANIMATED SPEED"

	# Retrieve or create the action
	action = bpy.data.actions.get(action_name) or bpy.data.actions.new(name=action_name)
	print(f"Using action: {action_name}")

	# Retrieve or create the animated speed curve
	speed_curve = next((fc for fc in action.fcurves if fc.data_path == "animated_speed"), None)
	if not speed_curve:
		speed_curve = action.fcurves.new(data_path="animated_speed", index=0)
		speed_curve.keyframe_points.add(1)
		speed_curve.keyframe_points[0].co = (0.0, 1.0)

	# Assign the action to the scene
	if not scene.animation_data:
		scene.animation_data_create()
	if scene.animation_data.action != action:
		scene.animation_data.action = action

	info_dict = action_info(all_objects(), context)

	for info in info_dict:
		strip, action_offset = info["strip"], info["action"].loop_offset
		if not strip:
			continue

		loop = scene.loop_list[info["loop"]]
		strip.use_animated_time = loop.use_animated_speed or action_offset != 0
		strip.use_animated_time_cyclic = False

		# Retrieve or create the strip_time F-curve
		time_curve = strip.fcurves.find("strip_time")
		if not time_curve:
			continue

		# Clear keyframes if animation is disabled
		if not loop.use_animated_speed and action_offset == 0:
			time_curve.keyframe_points.clear()
			continue

		# Clear existing keyframes before adding new ones
		time_curve.keyframe_points.clear()
		
		integral = strip.action_frame_start - 1
		for frame in range(int(strip.action_frame_start), int(strip.action_frame_end)):
			speed_value = speed_curve.evaluate(frame)
			absolute = speed_value < 0

			if absolute:  # Absolute frame number
				time_value = -speed_value + action_offset
				integral = time_value
			else:  # Incremental speed
				time_value = integral + speed_value
				integral = time_value

			time_curve.keyframe_points.insert(frame=frame, value=round(time_value, 2) + (action_offset * int(not absolute)))

def basic_update(context, action, use_all=False):
	# This will update animated speed, marker rendering, and cycles modifiers
	if not int(action.linked_loop) == -1:
		index = int(action.linked_loop)
		loop = context.scene.loop_list[index]

		# fancy naming
		foundStrip = None
		if not use_all:
			action.name = f"{context.object.name.upper()}×{loop.name.upper()}"
		for track in context.object.animation_data.nla_tracks:
			for strip in track.strips:
				if strip.action == action:
					foundStrip = strip
					if not use_all:
						strip.name = loop.name.upper()
					break;break;

		# set manual frame range and cyclic
		loop_start = loop.loop_start
		loop_end = loop_start + loop.duration - 0.1
		action.use_frame_range = True
		action.frame_start = loop_start
		action.frame_end = loop_end
		action.use_cyclic = True
		if foundStrip:
			foundStrip.frame_end_ui = loop_end
		
		# apply cycles modifiers
		for fcurve in action.fcurves:
			if not len(fcurve.modifiers) == 0:
				fcurve.modifiers.remove(fcurve.modifiers[0])
			modifier = fcurve.modifiers.new(type='CYCLES')
			if modifier:
				# Set the modifier options as desired
				modifier.name="ZK"
				modifier.mode_before = 'REPEAT'
				modifier.mode_after = 'REPEAT'

		# Animated speed
		update_time_for_speed(context)

def get_loop_for_action(self, context):
	scene = context.scene
	active_action = context.object.animation_data.action

	if not active_action:
		self.report({'ERROR'}, "No active action found")
		return None

	# Search for the loop that has the active action linked
	for loop in scene.loop_list:
		for action_item in loop.actions:
			if action_item.action == active_action:
				return loop  # Return the loop where the action is assigned

	self.report({'ERROR'}, f"Action '{active_action.name}' not found in any loop")
	return None

def get_or_create_collection(name, parent_name=None):
	if parent_name:
		if parent_name not in bpy.data.collections:
			parent_collection = bpy.data.collections.new(parent_name)
			bpy.context.scene.collection.children.link(parent_collection)
		else:
			parent_collection = bpy.data.collections[parent_name]
		
		if name not in bpy.data.collections:
			new_collection = bpy.data.collections.new(name)
			parent_collection.children.link(new_collection)
		else:
			new_collection = bpy.data.collections[name]
	else:
		if name not in bpy.data.collections:
			new_collection = bpy.data.collections.new(name)
			bpy.context.scene.collection.children.link(new_collection)
		else:
			new_collection = bpy.data.collections[name]
	
	return new_collection

def add_visibility_driver(obj, loop_indices, invert = False, path="hide_viewport"):
	# Create a single driver variable for all loops
	scene = bpy.context.scene
	fcurve = obj.driver_add(path)
	driver = fcurve.driver
	driver.type = 'SCRIPTED'
	
	# Create a list of conditions for all loops
	conditions = []
	
	for i in loop_indices:
		loop = scene.loop_list[i]
		condition = f"(frame >= loop_start_{i}) and (frame <= loop_end_{i})"
		conditions.append(condition)
		
		# Create driver variables for each loop
		var_loop_start = driver.variables.new()
		var_loop_start.name = f"loop_start_{i}"
		var_loop_start.targets[0].id_type = 'SCENE'
		var_loop_start.targets[0].id = bpy.context.scene
		var_loop_start.targets[0].data_path = f"loop_list[{i}].actions[0].action.frame_start"  # loop start
		
		var_loop_end = driver.variables.new()
		var_loop_end.name = f"loop_end_{i}"
		var_loop_end.targets[0].id_type = 'SCENE'
		var_loop_end.targets[0].id = bpy.context.scene
		var_loop_end.targets[0].data_path = f"loop_list[{i}].actions[0].action.frame_end"  # loop end
	
	# Combine all conditions with OR
	driver.expression = " or ".join(conditions)
	if invert:
		driver.expression = "not (" + driver.expression + ")"
	return driver.expression

### OPERATORS
class ZEPHKIT_OT_SetViewMode(bpy.types.Operator):
	"""Create a new loop"""
	bl_idname = "zephkit.set_view_mode"
	bl_label = "View Mode"

	val: BoolProperty()

	def execute(self, context):
		context.scene.zephkit_view_all_loops = self.val
		return {'FINISHED'}

class ZEPHKIT_OT_NewLoop(bpy.types.Operator):
	"""Create a new loop"""
	bl_idname = "zephkit.new_loop"
	bl_label = "New Loop"

	loop_name: StringProperty(name="Loop Name", default="New Loop")

	def execute(self, context):
		scene = context.scene
		new_loop = scene.loop_list.add()
		new_loop.name = self.loop_name
		new_loop.loop_start = 0
		new_loop.duration = 100
		self.report({'INFO'}, f"Created new loop: {new_loop.name}")
		return {'FINISHED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

class ZEPHKIT_OT_LinkActionToLoop(bpy.types.Operator):
	"""Link the active action to a selected loop"""
	bl_idname = "zephkit.link_action_to_loop"
	bl_label = "Link Action to Loop"

	loop_index: bpy.props.IntProperty()

	def execute(self, context):
		scene = context.scene
		active_action = context.object.animation_data.action

		if not active_action:
			self.report({'ERROR'}, "No active action found")
			return {'CANCELLED'}

		# Fetch the loop using the loop_index passed
		loop = scene.loop_list[self.loop_index]

		# Check if the action is already linked to any loop and unlink it
		for loop_item in scene.loop_list:
			for i, action_item in enumerate(loop_item.actions):
				if action_item.action == active_action:
					loop_item.actions.remove(i)  # Remove the action from the loop

		# Check if the action is already in the selected loop
		for action_item in loop.actions:
			if action_item.action == active_action:
				self.report({'INFO'}, f"Action '{active_action.name}' is already linked to loop '{loop.name}'")
				return {'FINISHED'}

		new_action_item = loop.actions.add()
		new_action_item.action = active_action

		updateAction(context, [active_action])
		PROP_updateDuration(loop, context)

		self.report({'INFO'}, f"Linked action '{active_action.name}' to loop '{loop.name}'")
		return {'FINISHED'}

class ZEPHKIT_OT_GlobalUpdate(bpy.types.Operator):
	"""Update all actions with parameter changes"""
	bl_idname = "zephkit.global_update"
	bl_label = "Update All"

	def set_action(self, obj, action):
		try:
			obj.animation_data.action = action
		except AttributeError:
			print("Failed to set action")

	def execute(self, context):
		bpy.ops.zephkit.tweak_mode_all(enter=False)
		actionInfo = action_info(all_objects(), context)
		for info in actionInfo:
			obj = info["object"]
			action = info["action"]

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

			context.view_layer.objects.active = obj

			self.set_action(obj, action)
			basic_update(context, action, True)
			self.set_action(obj, None)
			
		update_time_for_speed(context)

		return {'FINISHED'}

class ZEPHKIT_OT_TestUpdateIntensity(bpy.types.Operator):
	"""Remove a loop from the scene"""
	bl_idname = "zephkit.update_intensity"
	bl_label = "Update Intensity"


	def execute(self, context):
		PROP_update_intensities(self, context)

		return {'FINISHED'}

class ZEPHKIT_OT_UnlinkRemoveLoop(bpy.types.Operator):
	"""Remove a loop from the scene"""
	bl_idname = "zephkit.unlink_remove"
	bl_label = "Unlink/Remove Loop"

	loop_index: IntProperty()

	def execute(self, context):
		scene = context.scene
		if scene.zephkit_view_all_loops:
			scene = context.scene
			try:
				scene.loop_list.remove(self.loop_index)
				self.report({'INFO'}, f"Removed loop at index {self.loop_index}")
			except IndexError:
				self.report({'ERROR'}, f"Invalid loop index: {self.loop_index}")
			return {'FINISHED'}
		else:
			active_action = context.object.animation_data.action

			if not active_action:
				self.report({'ERROR'}, "No active action found")
				return {'CANCELLED'}

			loop = scene.loop_list[self.loop_index]
			for i, item in enumerate(loop.actions):
				if item.action == active_action:
					loop.actions.remove(i)
					self.report({'INFO'}, f"Unlinked action '{active_action.name}' from loop '{loop.name}'")
					return {'FINISHED'}

			self.report({'ERROR'}, f"Action '{active_action.name}' not found in loop '{loop.name}'")
			return {'CANCELLED'}

class ZEPHKIT_OT_TweakActionMode(bpy.types.Operator):
	"""Put the first action in the loop into tweak mode"""
	bl_idname = "zephkit.tweak_action_mode"
	bl_label = "Tweak Action Mode"

	loop_index: IntProperty()

	def execute(self, context):
		print(self.loop_index)
		scene = context.scene
		obj = context.object
		loop = scene.loop_list[self.loop_index]

		if not obj.animation_data:
			self.report({'INFO'}, f"Object has no NLA Data")
			return {'FINISHED'}
		
		foundTrack = None
		foundStrip = None

		# Exit tweak mode for all objects.
		bpy.ops.zephkit.tweak_mode_all(enter=False)

		for track in obj.animation_data.nla_tracks:
			for strip in track.strips:
				strip.select = False
				print(f"{strip.action} in {[x.action for x in loop.actions]}")
				if strip.action in [x.action for x in loop.actions]: # If action is part of current loop, 
					if not obj.animation_data.action == strip.action: # If not already being tweaked
						foundStrip = strip
						foundTrack = track

		if foundStrip:
			prevArea = context.area.type
			context.area.type = "NLA_EDITOR"
			foundTrack.select = True
			foundStrip.select = True
			bpy.ops.nla.tweakmode_enter(use_upper_stack_evaluation=True)
			
			context.area.type = prevArea

		updateAction(context, [obj.animation_data.action])
		bpy.ops.action.view_all()

		return {'FINISHED'}

class ZEPHKIT_OT_LinkObjectToLoop(bpy.types.Operator):
	"""Create a new loop and remove from the Scene Collection"""
	bl_idname = "zephkit.link_object_to_loop"
	bl_label = "Link"

	link_loop: bpy.props.EnumProperty(
		name="Loop",
		description="Choose a loop to link the object",
		items=get_loop_items,
		default=-1,
	)

	def execute(self, context):
		if int(self.link_loop) == -1:
			self.report({'WARNING'}, "You must select a loop!")
			return {'CANCELLED'}
		else:
			scene = context.scene
			loop_indices = [int(self.link_loop)]  # Start with the selected loop index

			# Get the current object
			obj = context.object

			# Ensure the object is not already in the collection bpy.context.view_layer.objects.active = original_object
			collection = get_or_create_collection("TEMP#" + str(int(self.link_loop)), "TEMPORAL")
			if collection:
				# Link the object to the loop collection
				collection.objects.link(obj)
				self.report({'INFO'}, f"Linked {obj.name} to {collection.name}")

				# Remove the object from the Scene Collection
				scene_collection = bpy.context.scene.collection
				if obj.name in scene_collection.objects:
					scene_collection.objects.unlink(obj)
					self.report({'INFO'}, f"Unlinked {obj.name} from the Scene Collection")
					
				bpy.ops.zephkit.update_drivers()


				"""
				old method
				# Find the other TEMP# collections the object is part of
				for coll in bpy.data.collections:
					if coll.name.startswith("TEMP#") and obj.name in coll.objects:
						# Add the index of each loop (TEMP# collection) the object is part of
						loop_index = int(coll.name.split("#")[1])  # Extract loop index from collection name
						if loop_index not in loop_indices:
							loop_indices.append(loop_index)

				# Add the visibility driver for the current and other loops
				add_visibility_driver(obj, loop_indices, True)  # Pass all loop indices to the function
				# Add it to all geonodes modifiers as well.
				for modifier in obj.modifiers:
					if modifier.type == 'NODES':  # Ensure it's a Geometry Nodes modifier
						add_visibility_driver(modifier, loop_indices, False, "show_viewport")
				"""

				return {'FINISHED'}
			else:
				self.report({'WARNING'}, "Something went wrong...")
				return {'CANCELLED'}

	def invoke(self, context, event):
		return context.window_manager.invoke_props_dialog(self)

class ZEPHKIT_OT_UpdateDrivers(bpy.types.Operator):
	"""Update visibility drivers for all objects in TEMP# collections"""
	bl_idname = "zephkit.update_drivers"
	bl_label = "Update"

	def execute(self, context):
		# Iterate through all TEMP# collections
		used_index_sets = [] # Reuse existing drivers, drive from their visibility rather than the full expression.
		"""
		([loop_indices], object)
		"""
		scene = context.scene
		loop_indices = []

		# Collect all TEMP# collections
		temp_collections = [coll for coll in bpy.data.collections if coll.name.startswith("TEMP#")]
		
		if not temp_collections:
			self.report({'WARNING'}, "No TEMP# collections found!")
			return {'CANCELLED'}

		# Loop through each TEMP# collection
		objects_dict = {
			#<object>:[<loop indices>]
		}
		# Collect a dictionary of data
		for coll in temp_collections:
			for obj in coll.objects:
				if obj not in objects_dict.keys():
					objects_dict[obj] = []
				objects_dict[obj].append(int(coll.name[-1]))

		for obj in objects_dict.keys():
			# remove all drivers before adding new ones...
			if obj.animation_data:
				for fcurve in obj.animation_data.drivers:
					if "frame >=" in fcurve.driver.expression:
						obj.animation_data.drivers.remove(fcurve)
			# And then add drivers using the key's value.
			# Add the visibility driver for the object in the collection
			add_visibility_driver(obj, objects_dict[obj], invert=True)  # For hide_viewport

			# Add visibility driver for all Geometry Nodes modifiers as well
			for modifier in obj.modifiers:
				if modifier.type == 'NODES':  # Ensure it's a Geometry Nodes modifier
					add_visibility_driver(modifier, objects_dict[obj], invert=False, path="show_viewport")
		self.report({'INFO'}, "Drivers updated for all objects in TEMP# collections")
		return {'FINISHED'}

class ZEPHKIT_OT_RenameLoop(bpy.types.Operator):
	"""Rename a loop from the scene"""
	bl_idname = "zephkit.rename_loop"
	bl_label = "Rename Loop"
	bl_options = {'REGISTER', 'UNDO'}

	loop_index: IntProperty(options={'HIDDEN'})
	name: StringProperty(name="New Name", default="")

	def execute(self, context):
		scene = context.scene
		if 0 <= self.loop_index < len(scene.loop_list):
			loop = scene.loop_list[self.loop_index]
			loop.name = self.name
			self.report({'INFO'}, f"Renamed loop to '{self.name}'")
		else:
			self.report({'ERROR'}, "Invalid loop index")
		return {'FINISHED'}

	def invoke(self, context, event):
		scene = context.scene
		if 0 <= self.loop_index < len(scene.loop_list):
			# Pre-fill the current name of the loop
			self.name = scene.loop_list[self.loop_index].name
		return context.window_manager.invoke_props_dialog(self)

class ZEPHKIT_PT_RenderLoopsAudio(bpy.types.Operator):
	bl_idname = "zephkit.render_loops_audio"
	bl_label = "Render Sound loops"

	def execute(self, context):
		return audio_update(self, context, True)

class ZEPHKIT_OT_UnlinkTempObject(bpy.types.Operator):
	"""Remove a loop from the scene, ensuring object stays in the Scene Collection and removing the visibility driver"""
	bl_idname = "zephkit.unlink_temp_object"
	bl_label = "Unlink Object"

	loop_index: bpy.props.IntProperty()

	def execute(self, context):
		obj = context.object
		if not obj:
			self.report({'WARNING'}, "No active object selected")
			return {'CANCELLED'}

		collection_name = f"TEMP#{self.loop_index}"
		collection = bpy.data.collections.get(collection_name)
		
		if collection and obj.name in collection.objects:
			# Ensure object is in the Scene Collection
			scene_collection = bpy.context.scene.collection
			if obj.name not in scene_collection.objects:
				scene_collection.objects.link(obj)
				self.report({'INFO'}, f"Linked {obj.name} back to the Scene Collection")

			# Unlink the object from the loop collection
			collection.objects.unlink(obj)
			self.report({'INFO'}, f"Unlinked {obj.name} from {collection_name}")

			# Remove the visibility driver
			if obj.animation_data:
				for fcurve in obj.animation_data.drivers:
					# Check if the driver is controlling the 'hide_viewport' property
					if fcurve.data_path == "hide_viewport":
						obj.animation_data.drivers.remove(fcurve)
						self.report({'INFO'}, f"Removed visibility driver from {obj.name}")
		else:
			self.report({'WARNING'}, f"Object not found in {collection_name}")
		
		return {'FINISHED'}

class ZEPHKIT_OT_RemoveActionFromLoop(bpy.types.Operator):
	"""Remove an action from a loop."""
	bl_idname = "zephkit.remove_action_from_loop"
	bl_label = "Remove Action"
	bl_options = {'REGISTER', 'UNDO'}

	action: StringProperty(name="Action", default="")
	loop_index: IntProperty(name="Loop Index", default=-1)

	def execute(self, context):
		scene = context.scene
		if 0 <= self.loop_index < len(scene.loop_list):
			loop = scene.loop_list[self.loop_index]
			
			# Find and remove the action from the loop's actions collection
			for i, item in enumerate(loop.actions):
				if item.action and item.action.name == self.action:
					loop.actions.remove(i)
					self.report({'INFO'}, f"Removed action '{self.action}' from loop '{loop.name}'")
					return {'FINISHED'}
			
			self.report({'WARNING'}, f"Action '{self.action}' not found in loop '{loop.name}'")
		else:
			self.report({'ERROR'}, "Invalid loop index")

		return {'CANCELLED'}

class ZEPHKIT_OT_NewAction(bpy.types.Operator):
	"""Remove an action from a loop."""
	bl_idname = "zephkit.new_action"
	bl_label = "New Action"
	bl_options = {'REGISTER', 'UNDO'}

	additive: BoolProperty(name="Additive", default=False)

	def execute(self, context):
		original_area_type = context.area.type
		context.area.type = 'NLA_EDITOR'
		# Exit all tweaking before
		bpy.ops.zephkit.tweak_mode_all(enter=False)
		

		# Restore original state
		context.area.type = original_area_type
		bpy.context.view_layer.objects.active = original_object



		return {'CANCELLED'}

### UI AND PANELS
class ZEPHKIT_PT_LoopToolsPanel(bpy.types.Panel):
	"""ZephKit Loop Tools Panel"""
	bl_label = "ZephKit Loop Tools"
	bl_idname = "ZEPHKIT_PT_loop_tools"
	bl_space_type = 'DOPESHEET_EDITOR'
	bl_region_type = 'UI'
	bl_category = "ZephKit"

	def draw(self, context):
		layout = self.layout
		obj = context.object;
		scene = context.scene
		view_all = scene.zephkit_view_all_loops

		# NLA quick tools
		row = layout.row(align=True)
		enterall = row.operator("zephkit.tweak_mode_all", text="Tweak all", icon="SELECT_EXTEND").enter = True
		exitall = row.operator("zephkit.tweak_mode_all", text="Tweak none", icon="SELECT_SUBTRACT").enter = False

		# Update menu
		row = layout.row(align=True)
		row.label(icon="FILE_REFRESH", text="Refresh")
		row.operator("zephkit.update_intensity", text="FX", icon="IPO_ELASTIC")
		row.operator('zephkit.render_loops_audio',text="SFX",icon="FILE_SOUND")
		row.operator("zephkit.global_update",text="All", icon="WORLD")


		# Loop display
		box = layout.box()
		# Tab styled object/scene switcher
		row = box.row(align=True)
		row.operator("zephkit.set_view_mode", text="Local", icon="MESH_UVSPHERE", depress=not view_all).val = False
		row.operator("zephkit.set_view_mode", text="Global", icon="WORLD", depress=view_all).val = True
		col = box.column(align=True)

		if view_all:
			# If we are in scene view mode
			for i, loop in enumerate(scene.loop_list):
				row = col.row(align=True)
				row.operator("zephkit.unlink_remove", icon='TRASH', text="").loop_index = i
				row.operator("zephkit.rename_loop", text=loop.name).loop_index = i
		else:
			# if we are in object view mode
			if not obj.animation_data:
				layout.label(text="Object has no NLA data.", icon='ERROR')
				return

			# If we are in scene view mode
			for i, loop in enumerate(scene.loop_list):
				row = col.row(align=True)
				depress = obj.animation_data.action in [x.action for x in scene.loop_list[i].actions]
				row.operator("zephkit.unlink_remove", icon='UNLINKED', text="",depress=depress).loop_index = i
				row.operator("zephkit.tweak_action_mode", text=loop.name, depress=depress).loop_index = i

		col.operator("zephkit.new_loop",text="+")

		# Loop properties menu
		active_action = obj.animation_data.action

		if active_action:
			box = layout.box()
			row = box.row()
			# Header with linked loop.
			row.label(text="Active Action", icon="PROPERTIES")
			# the action
			row.prop(active_action, "linked_loop", text="")
			# Solo action
			#row.operator(icon="SOLO_ON",text="")

			active_loop_index = -1;
			for i,loop in enumerate(scene.loop_list):
				if active_action in [x.action for x in loop.actions]:
					active_loop_index = i;
					break
			if not active_loop_index == -1:
				loop_props = scene.loop_list[active_loop_index]

				# Timing
				row = box.row()
				row.label(text="Timing", icon="TIME")
				row.prop(loop_props, "rest_frame", text="Resting frame")
				loop_times = box.split(align=True)
				range_row = loop_times.split(align=True)
				range_row.prop(loop_props, "loop_start", text="")
				range_row.prop(loop_props, "loop_end", text="")
				loop_times.prop(loop_props, "duration", icon="TIME")
				# Animated Speed
				row = box.row(align=True)
				row.prop(loop_props, "use_animated_speed",text="", icon="RENDER_ANIMATION")
				time_row = row.split(align=True,factor=0.4)
				time_row.prop(active_action, "loop_offset")
				time_row.prop(scene, "animated_speed")

				row = box.row()
				row.label(text="Intensity", icon="SOLO_ON")
				row.prop(active_action, "use_intensity",text="Enabled", icon="PREFERENCES")
				# Animated Intensity
				row = box.row(align=True)
				row.prop(loop_props, "intensity_variation", text="Var.")
				row.prop(scene, "animated_intensity")

				row = box.row()
				row.label(text="Sound", icon="SPEAKER")
				row.prop(loop_props,"audio_volume",text="Vol",icon="PLAY_SOUND")

				row = box.split(align=True,factor=0.2)
				row.prop(loop_props,"audio_offset",text="")
				row = row.split(align=True,factor=0.2)
				row.prop(loop_props,"audio_rate",text="")
				row.prop(loop_props,"audio_pool",text="")

				layout.label(text="--Linked Loops--")

				# LINKED LOOPS

				for x in loop_props.actions:
					row = layout.row()
					if x.action.name == active_action.name:
						row.label(text=" * "+x.action.name)
					else:
						row.label(text=" - "+x.action.name)

					removeButton = row.operator("zephkit.remove_action_from_loop", text="", icon="TRASH")
					removeButton.action = x.action.name
					removeButton.loop_index = active_loop_index

class ZEPHKIT_PT_TemporalObjectsPanel(bpy.types.Panel):
	bl_idname = "ZEPHKIT_Temporals"
	bl_label = "Temporal"
	bl_space_type = "VIEW_3D"
	bl_region_type = "TOOLS"
 
	def draw(self, context):
		layout = self.layout
		col = layout.column(align=True)
		obj = context.object
		col.operator("zephkit.update_drivers")
		if obj:
			temp_collection = get_or_create_collection("TEMPORAL")
			if temp_collection:
				for coll in temp_collection.children:
					if obj.name in coll.objects:
						loop_index = int(coll.name[-1]) # Last character is a number that is our index,
						loop_name = context.scene.loop_list[loop_index].name

						row = col.row(align=True)
						unlink = row.operator("zephkit.unlink_temp_object",text="",icon="TRASH")
						unlink.loop_index = loop_index
						row.label(text=loop_name)
		col.operator("zephkit.link_object_to_loop",text="+")
		
			
modules = [
	ZEPHKIT_OT_SetViewMode,
	ZEPHKIT_OT_RemoveActionFromLoop,
	ZEPHKIT_OT_NewLoop,
	ZEPHKIT_OT_TweakActionMode,
	ZEPHKIT_OT_LinkActionToLoop,
	ZEPHKIT_PT_LoopToolsPanel,
	ZEPHKIT_OT_UnlinkRemoveLoop,
	ZEPHKIT_OT_RenameLoop,
	ZEPHKIT_PT_RenderLoopsAudio,
	ZEPHKIT_OT_GlobalUpdate,
	ZEPHKIT_OT_TestUpdateIntensity,
	ZEPHKIT_OT_UpdateDrivers,
	ZEPHKIT_OT_LinkObjectToLoop,
	ZEPHKIT_OT_UnlinkTempObject,
	ZEPHKIT_PT_TemporalObjectsPanel,
]

def register():
	bpy.utils.register_class(ActionItem)
	bpy.utils.register_class(SceneLoopProperties)
	register_custom_properties()

	for module in modules:
		bpy.utils.register_class(module)
def unregister():
	del bpy.types.Scene.zephkit_view_all_loops
	del bpy.types.Scene.loop_list

	for module in reversed(modules):
		bpy.utils.unregister_class(module)
	bpy.utils.unregister_class(ActionItem)
	bpy.utils.unregister_class(SceneLoopProperties)