bl_info = {
	"name": "Touch It IK Tracker",
	"author": "azephynight + ChatGPT",
	"version": (1, 7, 0),
	"blender": (3, 0, 0),
	"location": "N/A",
	"description": "Receives hand tracking data and drives any existing rigs with IK using empties.",
	"category": "System",
}

import bpy
import socket
import json
from mathutils import Vector, Quaternion, Matrix
import time

# -----------------------------
# UDP SOCKET
# -----------------------------
UDP_IP = "0.0.0.0"
UDP_PORT = 5005
sock = None

def init_socket():
	global sock
	if sock is not None:
		return
	sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	sock.bind((UDP_IP, UDP_PORT))
	sock.setblocking(False)
	print(f"[HandReceiver] Listening on {UDP_IP}:{UDP_PORT}")

# -----------------------------
# SMOOTHING
# -----------------------------
SMOOTH_FACTOR = 0.6
last_positions = {}
last_rotations = {}

def lerp(v1, v2, factor):
	return v1.lerp(v2, factor)

def slerp(q1, q2, factor):
	return q1.slerp(q2, factor)

# -----------------------------
# MEDIAPIPE HAND LANDMARK MAPPING
# -----------------------------
# MediaPipe hand landmarks (21 points)
# See: https://google.github.io/mediapipe/images/mobile/hand_landmarks.png
MEDIAPIPE_LANDMARKS = {
    0: "WRIST",
    1: "THUMB_CMC",      # Thumb CMC (carpometacarpal)
    2: "THUMB_MCP",      # Thumb MCP (metacarpophalangeal)
    3: "THUMB_IP",       # Thumb IP (interphalangeal)
    4: "THUMB_TIP",
    5: "INDEX_FINGER_MCP",
    6: "INDEX_FINGER_PIP",
    7: "INDEX_FINGER_DIP",
    8: "INDEX_FINGER_TIP",
    9: "MIDDLE_FINGER_MCP",
    10: "MIDDLE_FINGER_PIP",
    11: "MIDDLE_FINGER_DIP",
    12: "MIDDLE_FINGER_TIP",
    13: "RING_FINGER_MCP",
    14: "RING_FINGER_PIP",
    15: "RING_FINGER_DIP",
    16: "RING_FINGER_TIP",
    17: "PINKY_MCP",
    18: "PINKY_PIP",
    19: "PINKY_DIP",
    20: "PINKY_TIP"
}

# Finger bone definitions: [start_landmark, end_landmark]
FINGER_BONES = {
    # Thumb
    "Thumb_CMC": [1, 2],    # CMC to MCP
    "Thumb_MCP": [2, 3],    # MCP to IP
    "Thumb_IP": [3, 4],     # IP to TIP
    
    # Index Finger
    "Index_MCP": [5, 6],    # MCP to PIP
    "Index_PIP": [6, 7],    # PIP to DIP
    "Index_DIP": [7, 8],    # DIP to TIP
    
    # Middle Finger
    "Middle_MCP": [9, 10],
    "Middle_PIP": [10, 11],
    "Middle_DIP": [11, 12],
    
    # Ring Finger
    "Ring_MCP": [13, 14],
    "Ring_PIP": [14, 15],
    "Ring_DIP": [15, 16],
    
    # Pinky Finger
    "Pinky_MCP": [17, 18],
    "Pinky_PIP": [18, 19],
    "Pinky_DIP": [19, 20],
}

# Additional bones from wrist to finger bases
PALM_BONES = {
    "Wrist_Thumb": [0, 1],      # Wrist to Thumb CMC
    "Wrist_Index": [0, 5],      # Wrist to Index MCP
    "Wrist_Middle": [0, 9],     # Wrist to Middle MCP
    "Wrist_Ring": [0, 13],      # Wrist to Ring MCP
    "Wrist_Pinky": [0, 17],     # Wrist to Pinky MCP
}

# -----------------------------
# CUSTOM PROPERTIES
# -----------------------------
def register_custom_properties():
	bpy.types.Scene.handtracking_data = bpy.props.StringProperty(
		name="Hand Tracking Data",
		default="{}"
	)
	bpy.types.Scene.depth_scale = bpy.props.FloatProperty(
		name="Depth Scale",
		default=0.5,
		min=0.1,
		max=10.0
	)
	bpy.types.Scene.handtracking_rig = bpy.props.PointerProperty(
		name="Target Armature",
		type=bpy.types.Object
	)
	bpy.types.Scene.show_finger_debug = bpy.props.BoolProperty(
		name="Show Finger Debug",
		default=True
	)
	bpy.types.Scene.rotation_smoothing = bpy.props.FloatProperty(
		name="Rotation Smoothing",
		default=0.5,
		min=0.0,
		max=1.0
	)
	bpy.types.Scene.position_smoothing = bpy.props.FloatProperty(
		name="Position Smoothing",
		default=0.5,
		min=0.0,
		max=1.0
	)

# -----------------------------
# CREATE EMPTIES
# -----------------------------
def ensure_hand_empties():
	"""Create empties for all hand bones"""
	for hand in range(2):
		# Create empties for each landmark (for reference/debug)
		for lm_id, lm_name in MEDIAPIPE_LANDMARKS.items():
			name = f"Hand{hand}_LM_{lm_id}_{lm_name}"
			if name not in bpy.data.objects:
				empty = bpy.data.objects.new(name, None)
				empty.empty_display_type = 'SPHERE'
				empty.empty_display_size = 0.01
				bpy.context.scene.collection.objects.link(empty)
		
		# Create empties for palm bones
		for bone_name, _ in PALM_BONES.items():
			name = f"Hand{hand}_{bone_name}"
			if name not in bpy.data.objects:
				empty = bpy.data.objects.new(name, None)
				empty.empty_display_type = 'ARROWS'
				empty.empty_display_size = 0.03
				empty.rotation_mode = 'QUATERNION'
				bpy.context.scene.collection.objects.link(empty)
		
		# Create empties for finger bones
		for bone_name, _ in FINGER_BONES.items():
			name = f"Hand{hand}_{bone_name}"
			if name not in bpy.data.objects:
				empty = bpy.data.objects.new(name, None)
				empty.empty_display_type = 'ARROWS'
				empty.empty_display_size = 0.02
				empty.rotation_mode = 'QUATERNION'
				bpy.context.scene.collection.objects.link(empty)

# -----------------------------
# ROTATION CALCULATION
# -----------------------------
def calculate_bone_rotation(start_pos, end_pos, up_reference=None):
	"""
	Calculate rotation quaternion for a bone pointing from start to end.
	
	Args:
		start_pos: Vector start position
		end_pos: Vector end position
		up_reference: Optional reference up vector for twist control
	
	Returns:
		Quaternion rotation
	"""
	# Calculate direction vector
	direction = (end_pos - start_pos).normalized()
	
	# If direction is zero, return identity
	if direction.length < 0.001:
		return Quaternion()
	
	# Default up vector
	if up_reference is None:
		up_reference = Vector((0, 0, 1))
	
	# Calculate right vector (perpendicular to direction and up)
	right = direction.cross(up_reference).normalized()
	
	# Recalculate up vector to ensure orthogonality
	up = right.cross(direction).normalized()
	
	# Create rotation matrix
	rot_matrix = Matrix()
	rot_matrix[0] = right        # X axis
	rot_matrix[1] = up           # Y axis  
	rot_matrix[2] = direction    # Z axis
	
	# Convert to quaternion
	return rot_matrix.to_quaternion()

# -----------------------------
# UPDATE EMPTIES
# -----------------------------
def update_empties(packet):
	"""Update all empties based on hand tracking data"""
	cam = bpy.context.scene.camera
	if cam is None:
		print("No camera found!")
		return

	# Process each hand
	for hand_data in packet.get("hands", []):
		hand_index = hand_data["hand_index"]
		
		# Convert all landmarks to world space
		landmark_world_positions = {}
		for lm in hand_data["landmarks"]:
			lm_id = lm["id"]
			world_pos = convert_landmark_to_world(lm, cam)
			landmark_world_positions[lm_id] = world_pos
			
			# Update landmark debug empties
			lm_name = MEDIAPIPE_LANDMARKS.get(lm_id, f"LM{lm_id}")
			empty_name = f"Hand{hand_index}_LM_{lm_id}_{lm_name}"
			empty = bpy.data.objects.get(empty_name)
			if empty:
				update_empty_position(empty, world_pos)
		
		# Update palm bones (wrist to finger bases)
		for bone_name, (start_id, end_id) in PALM_BONES.items():
			if start_id in landmark_world_positions and end_id in landmark_world_positions:
				start_pos = landmark_world_positions[start_id]
				end_pos = landmark_world_positions[end_id]
				
				# Calculate midpoint for empty position
				midpoint = (start_pos + end_pos) / 2
				
				# Calculate rotation
				rotation = calculate_bone_rotation(start_pos, end_pos)
				
				# Update empty
				empty_name = f"Hand{hand_index}_{bone_name}"
				empty = bpy.data.objects.get(empty_name)
				if empty:
					update_empty_position(empty, midpoint)
					update_empty_rotation(empty, rotation)
		
		# Update finger bones
		for bone_name, (start_id, end_id) in FINGER_BONES.items():
			if start_id in landmark_world_positions and end_id in landmark_world_positions:
				start_pos = landmark_world_positions[start_id]
				end_pos = landmark_world_positions[end_id]
				
				# Calculate midpoint for empty position
				midpoint = (start_pos + end_pos) / 2
				
				# For better orientation, we can use the palm as up reference
				palm_up = None
				if 0 in landmark_world_positions:  # Wrist
					palm_up = (landmark_world_positions[0] - midpoint).normalized()
				
				# Calculate rotation
				rotation = calculate_bone_rotation(start_pos, end_pos, palm_up)
				
				# Update empty
				empty_name = f"Hand{hand_index}_{bone_name}"
				empty = bpy.data.objects.get(empty_name)
				if empty:
					update_empty_position(empty, midpoint)
					update_empty_rotation(empty, rotation)

def convert_landmark_to_world(lm_data, cam):
	"""Convert MediaPipe landmark to Blender world space"""
	cam_pos = cam.matrix_world.translation
	forward = cam.matrix_world.to_quaternion() @ Vector((0, 0, -1))
	right = cam.matrix_world.to_quaternion() @ Vector((1, 0, 0))
	up = cam.matrix_world.to_quaternion() @ Vector((0, 1, 0))
	
	depth_scale = bpy.context.scene.depth_scale
	xy_scale = 1.0
	
	x = lm_data["x"]
	y = 1 - lm_data["y"]
	z = lm_data["z"] * -1
	
	world_pos = (
		cam_pos +
		forward * depth_scale +
		right * ((x - 0.5) * xy_scale) +
		up * ((y - 0.5) * xy_scale) +
		forward * (z * depth_scale * 0.5)
	)
	
	return world_pos

def update_empty_position(empty, target_position):
	"""Update empty position with smoothing"""
	empty_name = empty.name
	
	# Apply smoothing
	if empty_name in last_positions:
		smoothing = bpy.context.scene.position_smoothing
		smoothed_pos = lerp(last_positions[empty_name], target_position, smoothing)
	else:
		smoothed_pos = target_position
	
	last_positions[empty_name] = smoothed_pos
	empty.location = smoothed_pos

def update_empty_rotation(empty, target_rotation):
	"""Update empty rotation with smoothing"""
	empty_name = empty.name
	
	# Apply smoothing
	if empty_name in last_rotations:
		smoothing = bpy.context.scene.rotation_smoothing
		smoothed_rot = slerp(last_rotations[empty_name], target_rotation, smoothing)
	else:
		smoothed_rot = target_rotation
	
	last_rotations[empty_name] = smoothed_rot
	empty.rotation_quaternion = smoothed_rot

# -----------------------------
# OPERATORS
# -----------------------------
class HANDTRACKING_OT_Receiver(bpy.types.Operator):
	bl_idname = "handtracking.receiver"
	bl_label = "Hand Tracking Receiver"
	_timer = None

	def modal(self, context, event):
		if event.type == "TIMER":
			try:
				data, addr = sock.recvfrom(65535)
				packet = json.loads(data.decode("utf-8"))
				context.scene.handtracking_data = json.dumps(packet)
				update_empties(packet)
			except BlockingIOError:
				pass
			except Exception as e:
				print("Receive error:", e)
		return {"PASS_THROUGH"}

	def execute(self, context):
		init_socket()
		ensure_hand_empties()
		
		wm = context.window_manager
		self._timer = wm.event_timer_add(0.01, window=context.window)
		wm.modal_handler_add(self)
		return {"RUNNING_MODAL"}

	def cancel(self, context):
		wm = context.window_manager
		wm.event_timer_remove(self._timer)

class HANDTRACKING_OT_ClearEmpties(bpy.types.Operator):
	"""Clear all hand tracking empties"""
	bl_idname = "handtracking.clear_empties"
	bl_label = "Clear Empties"
	
	def execute(self, context):
		# Clear all empties created by this addon
		empties_to_remove = []
		for obj in bpy.data.objects:
			if obj.name.startswith("Hand") and obj.type == 'EMPTY':
				empties_to_remove.append(obj)
		
		for empty in empties_to_remove:
			bpy.data.objects.remove(empty)
		
		# Clear smoothing data
		global last_positions, last_rotations
		last_positions.clear()
		last_rotations.clear()
		
		self.report({'INFO'}, f"Cleared {len(empties_to_remove)} empties")
		return {'FINISHED'}

# -----------------------------
# PANELS
# -----------------------------
class HANDTRACKING_PT_Panel(bpy.types.Panel):
	bl_label = "Hand Tracking Receiver"
	bl_idname = "HANDTRACKING_PT_panel"
	bl_space_type = "VIEW_3D"
	bl_region_type = "UI"
	bl_category = "Hand Tracking"

	def draw(self, context):
		layout = self.layout
		
		# Target armature selection
		layout.prop(context.scene, "handtracking_rig", text="Target Armature")
		
		# Main controls
		box = layout.box()
		box.label(text="Controls", icon='PLAY')
		box.operator("handtracking.receiver", text="Start Receiver", icon='PLAY')
		box.operator("handtracking.clear_empties", text="Clear Empties", icon='TRASH')
		
		# Settings
		box = layout.box()
		box.label(text="Settings", icon='SETTINGS')
		box.prop(context.scene, "depth_scale")
		box.prop(context.scene, "position_smoothing")
		box.prop(context.scene, "rotation_smoothing")
		
		# Debug
		box = layout.box()
		box.label(text="Debug", icon='INFO')
		box.prop(context.scene, "show_finger_debug")
		
		if context.scene.show_finger_debug:
			box.label(text="Landmark Names:")
			for lm_id, lm_name in MEDIAPIPE_LANDMARKS.items():
				box.label(text=f"  {lm_id}: {lm_name}")
			
			box.label(text="Current Data:")
			box.prop(context.scene, "handtracking_data", text="")

# -----------------------------
# REGISTRATION
# -----------------------------
classes = (
	HANDTRACKING_OT_Receiver,
	HANDTRACKING_OT_ClearEmpties,
	HANDTRACKING_PT_Panel,
)

def register():
	register_custom_properties()
	for c in classes:
		bpy.utils.register_class(c)

def unregister():
	for c in reversed(classes):
		bpy.utils.unregister_class(c)
	del bpy.types.Scene.handtracking_data
	del bpy.types.Scene.depth_scale
	del bpy.types.Scene.handtracking_rig
	del bpy.types.Scene.show_finger_debug
	del bpy.types.Scene.rotation_smoothing
	del bpy.types.Scene.position_smoothing

if __name__ == "__main__":
	register()