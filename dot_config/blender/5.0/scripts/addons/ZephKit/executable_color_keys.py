import bpy
from bpy.app.handlers import persistent
from . import utils

type_values = ["EXTREME","MOVING_HOLD","BREAKDOWN","JITTER","KEYFRAME", "GENERATED"] # Adjust your Blender theme to have these as Red, Green, Blue, Dark Blue, and Magenta respectively
previousChannelLengths = {}
previousObject = None;

def assignColors(force):
    global previousObject;
    global previousChannelLengths;
    global type_values;
    
    ob = bpy.context.object;
    if ob:
        action_name = (ob.animation_data.action.name if ob.animation_data is not None and ob.animation_data.action is not None else None)
        
        if action_name:
            if bpy.data.actions[action_name]:
                action = bpy.data.actions[action_name]
                for fcu in utils.fcurves_all(action):
                    if not previousChannelLengths.get(fcu) == len(fcu.keyframe_points) or not ob == previousObject or force:# if length, or the active object has changed, ignore them if FORCE is true
                        finalColor = fcu.array_index # 0 - 3
                        if fcu.data_path == "rotation_quaternion":
                            if fcu.array_index == 0:
                                finalColor = 3;
                            elif fcu.array_index == 1:
                                finalColor = 4;
                            else:
                                finalColor = fcu.array_index - 1;
                        elif fcu.data_path == "rotation_euler":
                            if fcu.array_index == 0:
                                finalColor = 4;
                            else:
                                finalColor = fcu.array_index;
            
                        for keyframe in fcu.keyframe_points:
                            keyframe.type = type_values[finalColor]
                    previousChannelLengths[fcu] = len(fcu.keyframe_points)
        previousObject = ob;

@persistent
def load_handler(dummy):
    assignColors(False)

@persistent
def startup_handler(dummy):
    assignColors(True)

def register():
    bpy.app.handlers.depsgraph_update_post.append(load_handler)
    bpy.app.handlers.load_post.append(startup_handler)

def unregister():
    bpy.app.handlers.depsgraph_update_post.remove(load_handler)
    bpy.app.handlers.load_post.remove(startup_handler)