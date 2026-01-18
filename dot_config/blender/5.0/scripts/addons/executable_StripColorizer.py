bl_info = {
    "name": "Live VSE Strip Colorizer",
    "blender": (3, 0, 0),
    "description": "Automatically color VSE strips by track",
    "category": "Sequencer",
}

import bpy
from bpy.app.handlers import persistent

MAX_COLORS = 8
TRACK_COLOR_MAP = {
    0: 'COLOR_01',
    1: 'COLOR_02',
    2: 'COLOR_03',
    3: 'COLOR_04',
    4: 'COLOR_05',
    5: 'COLOR_06',
    6: 'COLOR_07',
    7: 'COLOR_08',
}


def color_strips_by_track(scene):
    sequences = scene.sequence_editor.sequences_all

    for seq in sequences:
        track = seq.channel
        color_index = (track - 1) % MAX_COLORS  # Tracks start at 1
        desired_color = TRACK_COLOR_MAP.get(color_index, 'COLOR_01')
        if seq.color_tag != desired_color:
            seq.color_tag = desired_color


@persistent
def depsgraph_colorizer(scene, depsgraph):
	color_strips_by_track(scene)



def register():
    bpy.app.handlers.depsgraph_update_post.append(depsgraph_colorizer)


def unregister():
    if depsgraph_colorizer in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_colorizer)