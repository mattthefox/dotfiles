bl_info = {
    "name": "Better Blender Tools",
    "author": "azephynight",
    "version": (1, 0),
    "blender": (3, 0, 0),
    "location": "View3D > Object > Copy Shape Key Drivers",
    "description": "Copies drivers from shape keys of source object to target object, plus color tools",
    "category": "Object",
}

import bpy
from bpy.types import UI_MT_button_context_menu
import mathutils
from mathutils import Vector

def linear_to_srgb(c):
    """Convert a single channel from linear to sRGB"""
    if c <= 0.0031308:
        return 12.92 * c
    else:
        return 1.055 * (c ** (1.0 / 2.4)) - 0.055

# -------- COLOR COPY OPERATOR --------
class COLOR_OT_copy_hex(bpy.types.Operator):
    bl_idname = "color.copy_hex"
    bl_label = "Copy Hex Color"
    bl_description = "Copy the current material color's hex code (sRGB) to clipboard"

    def execute(self, context):
        mat = context.object.active_material if context.object else None
        if mat and mat.use_nodes:
            bsdf = mat.node_tree.nodes.get("Principled BSDF")
            if bsdf:
                col = bsdf.inputs["Base Color"].default_value
                # Convert to sRGB
                r, g, b = [linear_to_srgb(c) for c in col[:3]]
                r, g, b = [max(0, min(255, round(c * 255))) for c in (r, g, b)]
                hex_code = "#{:02X}{:02X}{:02X}".format(r, g, b)
                context.window_manager.clipboard = hex_code
                self.report({'INFO'}, f"Copied {hex_code}")
                return {'FINISHED'}

        self.report({'WARNING'}, "No material color found")
        return {'CANCELLED'}

def draw_copy_hex(self, context):
    self.layout.operator(COLOR_OT_copy_hex.bl_idname)

# -------- SHAPE KEY TOOLS --------
class OBJECT_OT_copy_shape_key_drivers(bpy.types.Operator):
    """Copy drivers from shape keys of active object to selected object"""
    bl_idname = "object.copy_shape_key_drivers"
    bl_label = "Copy Shape Key Drivers"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        objs = context.selected_objects
        if len(objs) != 2:
            self.report({'ERROR'}, "Select exactly two objects (source first, then target)")
            return {'CANCELLED'}

        source, target = objs

        if not source.data.shape_keys:
            self.report({'ERROR'}, "Source object has no shape keys")
            return {'CANCELLED'}

        if not target.data.shape_keys:
            self.report({'ERROR'}, "Target object has no shape keys")
            return {'CANCELLED'}

        source_keys = source.data.shape_keys
        target_keys = target.data.shape_keys

        for src_key in source_keys.key_blocks:
            fcurves = [
                fc for fc in source_keys.animation_data.drivers
                if fc.data_path.startswith(f'key_blocks["{src_key.name}"].value')
            ]

            for fc in fcurves:
                if src_key.name not in target_keys.key_blocks:
                    self.report({'WARNING'}, f"Key {src_key.name} not in target")
                    continue

                try:
                    target_keys.driver_remove(f'key_blocks["{src_key.name}"].value')
                except:
                    pass

                new_driver = target_keys.driver_add(f'key_blocks["{src_key.name}"].value').driver
                new_driver.type = fc.driver.type
                new_driver.expression = fc.driver.expression

                for var in fc.driver.variables:
                    new_var = new_driver.variables.new()
                    new_var.name = var.name
                    new_var.type = var.type
                    for i, targ in enumerate(var.targets):
                        new_targ = new_var.targets[i]
                        new_targ.id = targ.id
                        new_targ.data_path = targ.data_path
                        new_targ.bone_target = targ.bone_target
                        new_targ.rotation_mode = targ.rotation_mode
                        new_targ.transform_space = targ.transform_space
                        new_targ.transform_type = targ.transform_type

        self.report({'INFO'}, "Shape key drivers copied successfully")
        return {'FINISHED'}

def enum_armature_items(self, context):
    items = []
    for obj in bpy.data.objects:
        if obj.type == 'ARMATURE':
            items.append((obj.name, obj.name, "", 'ARMATURE_DATA', len(items)))
    if not items:
        items.append(("None", "No Armatures Found", "", 'ERROR', 0))
    return items

class OBJECT_OT_change_shape_key_driver_targets(bpy.types.Operator):
    """Change the target armature in all shape key drivers"""
    bl_idname = "object.change_shape_key_driver_targets"
    bl_label = "Change Shape Key Driver Targets"
    bl_options = {'REGISTER', 'UNDO'}

    new_target: bpy.props.EnumProperty(
        name="New Armature",
        description="Armature object to set as the new driver target",
        items=enum_armature_items
    )

    def execute(self, context):
        active_obj = context.active_object
        if not active_obj:
            self.report({'ERROR'}, "No active object selected")
            return {'CANCELLED'}

        if not active_obj.data.shape_keys:
            self.report({'ERROR'}, "Active object has no shape keys")
            return {'CANCELLED'}

        shape_keys = active_obj.data.shape_keys
        if not shape_keys.animation_data or not shape_keys.animation_data.drivers:
            self.report({'ERROR'}, "No drivers found on shape keys")
            return {'CANCELLED'}

        if self.new_target == "None":
            self.report({'ERROR'}, "No valid armature selected")
            return {'CANCELLED'}

        target_obj = bpy.data.objects[self.new_target]

        for fc in shape_keys.animation_data.drivers:
            if not fc.data_path.startswith('key_blocks["'):
                continue

            for var in fc.driver.variables:
                for targ in var.targets:
                    targ.id = target_obj

        self.report({'INFO'}, f"Driver targets changed to armature '{target_obj.name}'")
        return {'FINISHED'}

    def invoke(self, context, event):
        wm = context.window_manager
        return wm.invoke_props_dialog(self)

class OBJECT_OT_toggle_visibility_mods(bpy.types.Operator):
    bl_idname = "object.toggle_visibility_modifiers"
    bl_label = "Enable/Disable object"
    bl_description = "Show or hide all traces of an object, at the current frame."

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

def resample_points(points, target_count):
    """Resample a list of Vector points to target_count evenly."""
    if len(points) == target_count:
        return points[:]  # Nothing to do

    distances = [0.0]
    for i in range(1, len(points)):
        distances.append(distances[-1] + (points[i] - points[i-1]).length)

    total_length = distances[-1]
    if total_length == 0:
        return [points[0].copy()] * target_count

    step = total_length / (target_count - 1)
    new_points = []

    for i in range(target_count):
        d = i * step
        for j in range(len(distances)-1):
            if distances[j] <= d <= distances[j+1]:
                t = (d - distances[j]) / (distances[j+1] - distances[j])
                new_points.append(points[j].lerp(points[j+1], t))
                break

    return new_points

def spline_selected(spl):
    """Return True if a spline has *any* selected control points."""
    if spl.type == 'BEZIER':
        return any(p.select_control_point for p in spl.bezier_points)
    else:
        return any(p.select for p in spl.points)

def spline_to_world_points(obj, spl):
    """Return list of world-space points from a spline."""
    if spl.type == 'BEZIER':
        return [obj.matrix_world @ p.co for p in spl.bezier_points]
    else:
        return [obj.matrix_world @ p.co for p in spl.points]

class CURVE_OT_bridge_splines_average(bpy.types.Operator):
    """Create a new spline averaging between two selected spline islands"""
    bl_idname = "curve.bridge_splines_average"
    bl_label = "Bridge Spline Islands (Average)"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object

        if not obj or obj.type != 'CURVE':
            self.report({'ERROR'}, "Select a curve object")
            return {'CANCELLED'}

        curve = obj.data

        # Collect splines that have selected control points
        selected_splines = [spl for spl in curve.splines if spline_selected(spl)]

        if len(selected_splines) != 2:
            self.report({'ERROR'}, "Select control points from exactly TWO spline islands")
            return {'CANCELLED'}

        s1, s2 = selected_splines

        # Extract world-space points
        p1 = spline_to_world_points(obj, s1)
        p2 = spline_to_world_points(obj, s2)

        # Resample if counts differ
        target_count = max(len(p1), len(p2))
        p1 = resample_points(p1, target_count)
        p2 = resample_points(p2, target_count)

        # Average points
        avg_points = [(a + b) * 0.5 for a, b in zip(p1, p2)]

        inv = obj.matrix_world.inverted()
        avg_local = [inv @ p for p in avg_points]

        # Create new spline
        new_spl = curve.splines.new('BEZIER')
        new_spl.points.add(len(avg_local)-1)

        for i, p in enumerate(avg_local):
            new_spl.points[i].co = (p.x, p.y, p.z, 1.0)

        new_spl.use_cyclic_u = False

        return {'FINISHED'}

def register():
    bpy.utils.register_class(CURVE_OT_bridge_splines_average)

def unregister():
    bpy.utils.unregister_class(CURVE_OT_bridge_splines_average)

if __name__ == "__main__":
    register()

# -------- REGISTER / UNREGISTER --------
classes = (
    COLOR_OT_copy_hex,
    OBJECT_OT_copy_shape_key_drivers,
    OBJECT_OT_change_shape_key_driver_targets,
    CURVE_OT_bridge_splines_average,
    OBJECT_OT_toggle_visibility_mods
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    UI_MT_button_context_menu.append(draw_copy_hex)

def unregister():
    UI_MT_button_context_menu.remove(draw_copy_hex)
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)

if __name__ == "__main__":
    register()
