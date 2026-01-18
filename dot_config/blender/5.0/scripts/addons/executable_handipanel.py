bl_info = {
    "name": "HandiPanel",
    "blender": (4, 00, 0),
    "category": "Object",
}

import bpy
import time
physics_visiblity = False

class OBJECT_PT_HandiPanelMenu(bpy.types.Panel):
    bl_label = "Physics"
    bl_idname = "PT_HandiPanelMenu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'ZEPHKIT ↓'
    bl_options = {'DEFAULT_CLOSED'}

    @classmethod
    def poll(cls, context):
        # Show the panel in Object Mode and Pose Mode
        return context.object and (context.mode == 'OBJECT' or context.mode == 'POSE')

    def draw(self, context):
        layout = self.layout

        row = self.layout.row()
        row.operator("object.reset_physics", text="Reset", icon="FILE_REFRESH")

        box = layout.box()
        all_row = box.row()
        all_row.operator("object.toggle_all_cloth_objects", text="", icon='RESTRICT_VIEW_ON' if physics_visiblity else 'RESTRICT_VIEW_OFF')
        all_row.operator("object.toggle_all_cloth_objects", text="All physics objects")
        
        # Check all objects in the scene
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.modifiers:
                for modifier in obj.modifiers:
                    if modifier.type == 'CLOTH':
                        row = box.row(align=True)
                        op_visibility = row.operator("object.toggle_cloth_visibility", text="", emboss=False, icon='RESTRICT_VIEW_OFF' if modifier.show_viewport else 'RESTRICT_VIEW_ON')
                        op_visibility.object_name = obj.name
                        op_select = row.operator("object.select_cloth_object", text=obj.name)
                        op_select.object_name = obj.name

## === ##
# Operators

class OBJECT_OT_ResetPhysics(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.reset_physics"
    bl_label = "Reset Physics"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        def adjustAllCaches(amount):
            for o in bpy.context.scene.objects:
                if o.type == 'MESH':
                    for x in o.modifiers:
                        if x.type == "CLOTH":
                            x.settings.time_scale += amount
        
        bpy.context.scene.physics_reset = not bpy.context.scene.physics_reset
        adjustAllCaches(.1)
        bpy.ops.screen.animation_play()
        time.sleep(.05)
        bpy.ops.screen.animation_play()
        adjustAllCaches(-.1)
        
        return {'FINISHED'}

class OBJECT_OT_DisablePhysics(bpy.types.Operator):
    """Tooltip"""
    bl_idname = "object.disable_physics"
    bl_label = "Disable Physics"

    @classmethod
    def poll(cls, context):
        return context.active_object is not None

    def execute(self, context):
        bpy.context.scene.physics_disabled = not bpy.context.scene.physics_disabled
        toggle = bpy.context.scene.physics_disabled
        for o in bpy.context.scene.objects:
            if o.type == 'MESH':
                for x in o.modifiers:
                    if x.type == "SURFACE_DEFORM" or x.type == "CLOTH":
                        x.show_viewport = toggle
            if o.type == "MESH":
                found = False
                for x in o.modifiers:
                    if x.type == "CLOTH":
                        found = True;
                        break
                if found:
                    o.hide_viewport = not toggle

        return {'FINISHED'}

class OBJECT_OT_ToggleClothVisibility(bpy.types.Operator):
    bl_label = "Toggle Cloth Visibility"
    bl_idname = "object.toggle_cloth_visibility"
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)

        if obj:
            # Toggle Cloth Visibility
            cloth_modifier = None
            for modifier in obj.modifiers:
                if modifier.type == 'CLOTH':
                    cloth_modifier = modifier
                    break

            if cloth_modifier:
                state = not cloth_modifier.show_viewport
                cloth_modifier.show_viewport = state
            else:
                state = False

            # Toggle related Surface Deform modifiers
            for other_obj in bpy.context.scene.objects:
                if other_obj.type == 'MESH' and other_obj.modifiers:
                    for modifier in other_obj.modifiers:
                        if modifier.type == "SURFACE_DEFORM" and modifier.target == obj:
                            modifier.show_viewport = state
                        if modifier.type == "NODES" and modifier.node_group and "Stepped Vertex Interpolation" in modifier.node_group.name:
                            modifier.show_viewport = state

        return {'FINISHED'}

class OBJECT_OT_SelectClothObject(bpy.types.Operator):
    bl_label = "Select Cloth Object"
    bl_idname = "object.select_cloth_object"
    object_name: bpy.props.StringProperty()

    def execute(self, context):
        obj = bpy.data.objects.get(self.object_name)

        if obj:
            # Select Cloth Object
            bpy.ops.object.select_all(action='DESELECT')
            obj.select_set(True)
            bpy.context.view_layer.objects.active = obj

        return {'FINISHED'}

class OBJECT_OT_ToggleAllClothVisibility(bpy.types.Operator):
    bl_label = "Toggle All Cloth Objects"
    bl_idname = "object.toggle_all_cloth_objects"

    def execute(self, context):
        global physics_visiblity
        for obj in bpy.context.scene.objects:
            if obj.type == 'MESH' and obj.modifiers:
                for modifier in obj.modifiers:
                    if modifier.type == 'CLOTH':
                        modifier.show_viewport = physics_visiblity
                    if modifier.type == "NODES" and modifier.node_group and "Stepped Vertex Interpolation" in modifier.node_group.name:
                        modifier.show_viewport = physics_visiblity
                    elif modifier.type == "SURFACE_DEFORM":
                        if modifier.target.type == "MESH":
                            for x in modifier.target.modifiers:
                                if x.type == "CLOTH":
                                    modifier.show_viewport = physics_visiblity
                                    break
                              
        physics_visiblity = not physics_visiblity

        return {'FINISHED'}

def menu_func(self, context):
    self.layout.operator(OBJECT_OT_ToggleClothVisibility.bl_idname)
    self.layout.operator(OBJECT_OT_SelectClothObject.bl_idname)

def register():
    bpy.utils.register_class(OBJECT_OT_ToggleAllClothVisibility)
    bpy.utils.register_class(OBJECT_PT_HandiPanelMenu)
    bpy.utils.register_class(OBJECT_OT_ToggleClothVisibility)
    bpy.utils.register_class(OBJECT_OT_SelectClothObject)
    bpy.types.Scene.antilag = bpy.props.BoolProperty(name="physics_disabled", description="", default=False)
    bpy.types.Scene.physics_reset = bpy.props.BoolProperty(name="physics_reset", description="", default=False)
    bpy.utils.register_class(OBJECT_OT_ResetPhysics)
    bpy.utils.register_class(OBJECT_OT_DisablePhysics)
    
def unregister():
    bpy.utils.unregister_class(OBJECT_OT_ToggleAllClothVisibility)
    bpy.utils.unregister_class(OBJECT_PT_HandiPanelMenu)
    bpy.utils.unregister_class(OBJECT_OT_ToggleClothVisibility)
    bpy.utils.unregister_class(OBJECT_OT_SelectClothObject)
    bpy.utils.unregister_class(OBJECT_OT_DisablePhysics)
    bpy.utils.unregister_class(OBJECT_OT_ResetPhysics)

if __name__ == "__main__":
    register()