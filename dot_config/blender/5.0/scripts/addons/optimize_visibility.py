bl_info = {
    "name": "Toggle Object & Modifier Visibility (Keyframed)",
    "author": "azephynight",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "description": "Toggles active object visibility + all modifiers, with auto keyframing",
    "category": "Object"
}

import bpy

class OBJECT_OT_toggle_visibility_mods(bpy.types.Operator):
    bl_idname = "object.toggle_visibility_modifiers"
    bl_label = "Toggle Object + Modifiers Visibility"
    bl_description = "Toggle visibility of active object and all its modifiers (with keyframe)"

    def execute(self, context):
        obj = context.active_object
        if not obj:
            self.report({'WARNING'}, "No active object")
            return {'CANCELLED'}

        # Toggle value
        new_state = not obj.hide_viewport
        obj.hide_viewport = new_state
        obj.hide_render = not new_state
        obj.keyframe_insert("hide_viewport")
        obj.keyframe_insert("hide_render")

        # Toggle all modifiers
        for m in obj.modifiers:
            if hasattr(m, "show_viewport"):
                m.show_viewport = not new_state
                try:
                    m.keyframe_insert("show_viewport")
                except:
                    pass

            if hasattr(m, "show_render"):
                m.show_render = not new_state
                try:
                    m.keyframe_insert("show_render")
                except:
                    pass

        return {'FINISHED'}


class OBJECT_PT_toggle_visibility_mods(bpy.types.Panel):
    bl_label = "Toggle Object Visibility"
    bl_idname = "OBJECT_PT_toggle_visibility_mods"
    bl_space_type = "PROPERTIES"
    bl_region_type = "WINDOW"
    bl_context = "object"

    def draw(self, context):
        col = self.layout.column()
        col.operator("object.toggle_visibility_modifiers")


classes = (
    OBJECT_OT_toggle_visibility_mods,
    OBJECT_PT_toggle_visibility_mods,
)

def register():
    for c in classes:
        bpy.utils.register_class(c)

def unregister():
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

if __name__ == "__main__":
    register()
