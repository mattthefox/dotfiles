bl_info = {
	'name': 'hands',
	'author': 'azephynight',
	'description': 'Helpful tools for animation!',
	'blender': (5, 0, 0),
	'version': (1, 0, 0),
	'location': 'View3D',
	'category': 'Animation',
}

import bpy
import socket
import json

scale_factor = 10
scale_sphere = 0.3

def receive_landmarks_from_server(host, port):
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((host, port))
    message = "Request landmarks"
    client_socket.send(message.encode('utf-8'))

    response = client_socket.recv(4096)
    client_socket.close()

    return response.decode('utf-8')

def create_sphere(name, location):
    bpy.ops.mesh.primitive_uv_sphere_add(location=location)
    sphere = bpy.context.active_object
    sphere.name = name
    sphere.scale = (scale_sphere, scale_sphere, scale_sphere)
    return sphere

def update_landmarks():
    host = "localhost"
    port = 12345
    
    try:
        response_data_str = receive_landmarks_from_server(host, port)
    except ConnectionRefusedError:
        print(f"Connection to {host}:{port} refused")
        return
    except ConnectionResetError:
        print(f"Connection to {host}:{port} reset")
        return
    except Exception as e:
        print(f"Error: {e}")
        return

    # Process response data
    response_data = json.loads(response_data_str)
    landmark_data = json.loads(response_data['landmarks'])
    closed_fist = response_data['closed_fist']

    # Update the camera position if a closed fist is detected
    update_camera_position(closed_fist, landmark_data)

    # Iterate through landmarks and create/update spheres in Blender
    for index, landmark in enumerate(landmark_data):
        sphere_name = f"landmark_{index}"
        location = (
            landmark['x'] * scale_factor,
            landmark['z'] * scale_factor,
            landmark['y'] * - scale_factor)

        sphere = bpy.data.objects.get(sphere_name)
        if sphere is None:
            create_sphere(sphere_name, location)
        else:
            sphere.location = location
            
original_index_finger_tip = None

def update_camera_position(closed_fist, landmark_data):
    global original_index_finger_tip
    
    # Get the index finger tip landmark
    index_finger_tip = landmark_data[8]

    # Calculate the new camera position relative to the original position
    if original_index_finger_tip:
        camera_position = (
            (index_finger_tip['x'] * scale_factor) - 0.5 - original_index_finger_tip[0],
            (index_finger_tip['z'] * scale_factor) - 0.5 - original_index_finger_tip[1],
            (index_finger_tip['y'] * - scale_factor) - 0.5 - original_index_finger_tip[2] 
        )
    else:
        camera_position = (
            (index_finger_tip['x'] * scale_factor) - 0.5,
            (index_finger_tip['z'] * scale_factor) - 0.5,
            (index_finger_tip['y'] * - scale_factor) - 0.5 
        )

    if not closed_fist:
        original_index_finger_tip = camera_position
        return

    # Move the camera to the new position    
    bpy.data.objects['Camera'].location = camera_position
    
class TimerOperator(bpy.types.Operator):
    bl_idname = "wm.timer_operator"
    bl_label = "Timer Operator"
    bl_label = "Handtracking"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Tools"

    _timer = None

    def modal(self, context, event):
        if event.type == 'TIMER':
            update_landmarks()

        return {'PASS_THROUGH'}

    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1.0 / 15.0, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}

    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

def menu_func(self, context):
    self.layout.operator(TimerOperator.bl_idname)

def register():
    bpy.utils.register_class(TimerOperator)
    bpy.types.VIEW3D_MT_mesh_add.append(menu_func)

def unregister():
    bpy.utils.unregister_class(TimerOperator)
    bpy.types.VIEW3D_MT_mesh_add.remove(menu_func)

if __name__ == "__main__":
    register()
