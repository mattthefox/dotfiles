bl_info = {
	'name': 'yoink',
	'author': 'azephynight',
	'description': 'Helpful tools for animation!',
	'blender': (4, 1, 0),
	'version': (1, 0, 0),
	'location': 'View3D',
	'category': 'Animation',
}

import bpy
import mathutils

def linear_to_srgb_channel(c):
    # simple gamma approx (good enough here)
    if c <= 0.0:
        return 0.0
    return pow(c, 1.0 / 2.2)

class ZephKit_YoinkColor(bpy.types.Operator):
    """Average active vertex color attribute and set as brush color"""
    bl_idname = "zephkit.yoink_color"
    bl_label = "Yoink Average Vertex Color"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        obj = context.active_object
        if not obj or obj.type != 'MESH':
            self.report({'ERROR'}, "No active mesh object found")
            return {'CANCELLED'}

        mesh = obj.data
        color_attr = mesh.color_attributes.active_color
        if not color_attr:
            self.report({'ERROR'}, "No active color attribute found")
            return {'CANCELLED'}

        brush = context.tool_settings.vertex_paint.brush
        if not brush:
            self.report({'ERROR'}, "No active vertex paint brush found")
            return {'CANCELLED'}

        domain = color_attr.domain  # 'POINT' or 'CORNER'
        # We'll compute a true per-vertex average regardless of domain:
        vert_totals = [mathutils.Vector((0.0, 0.0, 0.0)) for _ in mesh.vertices]
        vert_alpha_totals = [0.0] * len(mesh.vertices)
        vert_counts = [0] * len(mesh.vertices)

        if domain == 'POINT':
            # color_attr.data is aligned to vertices
            for v_idx, elem in enumerate(color_attr.data):
                r, g, b, a = elem.color
                vert_totals[v_idx] += mathutils.Vector((r, g, b))
                vert_alpha_totals[v_idx] += a
                vert_counts[v_idx] += 1
        elif domain == 'CORNER':
            # color_attr.data is per-loop; map loops -> vertex
            for loop_index, loop in enumerate(mesh.loops):
                v_idx = loop.vertex_index
                elem = color_attr.data[loop_index]
                r, g, b, a = elem.color
                vert_totals[v_idx] += mathutils.Vector((r, g, b))
                vert_alpha_totals[v_idx] += a
                vert_counts[v_idx] += 1
        else:
            self.report({'ERROR'}, f"Unsupported color domain: {domain}")
            return {'CANCELLED'}

        # compute per-vertex average, then average across vertices
        global_rgb = mathutils.Vector((0.0, 0.0, 0.0))
        global_alpha = 0.0
        vertex_with_data = 0

        for i, cnt in enumerate(vert_counts):
            if cnt == 0:
                continue
            avg_rgb_v = vert_totals[i] / cnt
            avg_a_v = vert_alpha_totals[i] / cnt

            # Auto-detect likely premultiplied alpha:
            # if max channel is <= alpha + small epsilon, it's likely premultiplied.
            max_ch = max(avg_rgb_v[0], avg_rgb_v[1], avg_rgb_v[2])
            if avg_a_v > 0.0 and max_ch <= (avg_a_v + 1e-6):
                # unpremultiply
                avg_rgb_v = avg_rgb_v / avg_a_v

            global_rgb += avg_rgb_v
            global_alpha += avg_a_v
            vertex_with_data += 1

        if vertex_with_data == 0:
            self.report({'ERROR'}, "No color values found to average")
            return {'CANCELLED'}

        avg_rgb = global_rgb / vertex_with_data
        avg_a = global_alpha / vertex_with_data

        # Convert from linear float space to sRGB for brush display (approx).
        srgb = mathutils.Vector((
            linear_to_srgb_channel(avg_rgb[0]),
            linear_to_srgb_channel(avg_rgb[1]),
            linear_to_srgb_channel(avg_rgb[2]),
        ))

        # Clamp just in case:
        for i in range(3):
            srgb[i] = min(max(srgb[i], 0.0), 1.0)

        brush.color = srgb
        # set brush strength from averaged alpha (optional; clip to [0,1])
        brush.strength = min(max(avg_a, 0.0), 1.0)

        self.report({'INFO'}, f"Brush color set to {tuple(srgb)} (strength {brush.strength:.3f})")
        return {'FINISHED'}

# Register (use your existing registration flow)
def register():
    bpy.utils.register_class(ZephKit_YoinkColor)

def unregister():
    bpy.utils.unregister_class(ZephKit_YoinkColor)

if __name__ == "__main__":
    register()
