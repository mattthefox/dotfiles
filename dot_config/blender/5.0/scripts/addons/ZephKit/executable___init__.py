bl_info = {
	'name': 'ZephKit',
	'author': 'azephynight',
	'description': 'Helpful tools for animation!',
	'blender': (4, 1, 0),
	'version': (1, 0, 0),
	'location': 'View3D',
	'category': 'Animation',
}

addon_keymaps = []

import bpy
import logging
import sys
import os

from . import lighting_tools
from . import animation_operators
from . import armature_baker
from . import data_management
#from . import loop_tools
from . import color_keys
from . import make_space
#from . import timeline_buttons

modules = [
	lighting_tools,
	armature_baker,
	animation_operators,
	data_management,
	#loop_tools,
	color_keys,
	make_space,
	#timeline_buttons,
]


def register():
	for module in modules:
		module.register()
	# registering keymaps
	wm = bpy.context.window_manager
	kc = wm.keyconfigs.addon
	if kc:
		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("anim.rename_nearest_marker", type='PERIOD', value='PRESS')
		addon_keymaps.append((km, kmi))

		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("screen.zjump_to_keyframe", type='THREE', value='PRESS')
		addon_keymaps.append((km, kmi))
		kmi.properties.direction = False

		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("screen.zjump_to_keyframe", type='FOUR', value='PRESS')
		addon_keymaps.append((km, kmi))
		kmi.properties.direction = True

		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("nla.frame_skip", 'LEFT_ARROW', 'PRESS')
		kmi.properties.direction = 'PREV'
		addon_keymaps.append((km, kmi))
		
		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("nla.frame_skip", 'RIGHT_ARROW', 'PRESS')
		kmi.properties.direction = 'NEXT'
		addon_keymaps.append((km, kmi))

		km = kc.keymaps.new(name='Dopesheet', space_type='DOPESHEET_EDITOR')
		kmi = km.keymap_items.new("dopesheet.cut_keyframe", type='X', value='PRESS', ctrl=True)
		addon_keymaps.append((km, kmi))



def unregister():
	for module in reversed(modules):
		module.unregister()
	for km, kmi in addon_keymaps:
		km.keymap_items.remove(kmi)
	addon_keymaps.clear()

if __name__ == "__main__":
	register()