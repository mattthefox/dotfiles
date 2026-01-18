bl_info = {
    "name": "Save unused Materials and Textures",
    "author": "CoDEmanX",
    "version": (1, 0, 0),
    "blender": (3, 00, 0),
    "location": "(none)",
    "description": "Enable fake user to rescue unused materials / textures automatically before saving",
    "warning": "Make sure this addon is enabled by default!",
    "category": "Material"}


import bpy
from bpy.app.handlers import persistent
from itertools import chain

@persistent
def enable_fakeuser(scene):
    print("save test")
    for datablock in chain(bpy.data.actions):
    #for datablock in chain(bpy.data.materials, bpy.data.textures, bpy.data.actions):
        datablock.use_fake_user = True


def register():
    bpy.app.handlers.save_pre.append(enable_fakeuser)


def unregister():
    bpy.app.handlers.save_pre.remove(enable_fakeuser)


if __name__ == "__main__":
    register()