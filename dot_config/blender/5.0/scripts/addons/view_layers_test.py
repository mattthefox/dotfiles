bl_info = {
    "name": "View Layer Enum Example",
    "description": "Adds a Scene property with an enum listing all view layers of the current scene.",
    "author": "Hazy Meadow Studios",
    "version": (1, 0, 0),
    "blender": (3, 0, 0),
    "category": "Scene"
}

import bpy

def get_view_layers(self, context):
    scene = context.scene
    items = []
    if scene is not None:
        for i, vl in enumerate(scene.view_layers):
            items.append((vl.name, vl.name, f"View Layer: {vl.name}", i))
    if not items:
        items.append(("NONE", "No View Layers", "", 0))
    return items

# Define the property
def register_props():
    bpy.types.Scene.view_layer_enum = bpy.props.EnumProperty(
        name="View Layer",
        description="Select a View Layer from the current scene",
        items=get_view_layers
    )

def unregister_props():
    del bpy.types.Scene.view_layer_enum

# Simple UI panel
class SCENE_PT_ViewLayerEnum(bpy.types.Panel):
    bl_label = "View Layer Enum"
    bl_idname = "SCENE_PT_view_layer_enum"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "scene"

    def draw(self, context):
        layout = self.layout
        layout.prop(context.scene, "view_layer_enum")

# Register
classes = (SCENE_PT_ViewLayerEnum,)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    register_props()

def unregister():
    unregister_props()
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
