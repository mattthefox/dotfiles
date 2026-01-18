bl_info = {
    "name": "Timeline Buttons",
    "author": "TinkerBoi",
    "version": (1, 0, 0),
    "blender": (4, 2, 0),
    "description": "Put the buttons in timeline to other animation related editors, Affected Editors - Dopesheet Editor, Graph Editor, NLA Editor, Sequencer",
    "doc_url": "",
    "tracker_url": "https://support.tinkerboi.com",
    "category": "Animation",
}

import bpy

def draw_player(self, context):
    layout = self.layout
    scene = context.scene
    tool_settings = context.tool_settings
    screen = context.screen

    if context.area.ui_type == "DOPESHEET":
        row = layout.row(align=True)

        row.prop(context.scene, "sync_mode",text="", icon="TIME")
        row.separator();

        if context.object.hide_viewport:
            row.operator("object.toggle_visibility_modifiers", text="Enable object", icon="CHECKBOX_DEHLT")
        else:
            row.operator("object.toggle_visibility_modifiers", text="Disable object", icon="CHECKBOX_HLT")
        row.prop(context.object, "hide_viewport",text="Hide")

        row.separator();
        row.prop(tool_settings, "use_keyframe_insert_auto", text="", toggle=True)
        sub = row.row(align=True)
        sub.active = tool_settings.use_keyframe_insert_auto
        sub.popover(
            panel="TIME_PT_auto_keyframing_Dopesheet",
            text="",
        )

    else:
        row = layout.row(align=True)

        row.prop(context.scene, "sync_mode",text="", icon="TIME")
        row.separator();
        row.prop(tool_settings, "use_keyframe_insert_auto", text="", toggle=True)
        sub = row.row(align=True)
        sub.active = tool_settings.use_keyframe_insert_auto
        sub.popover(
            panel="TIME_PT_auto_keyframing_Dopesheet",
            text="",
        )


def draw_frame_range(self, context):
    layout = self.layout
    scene = context.scene
    tool_settings = context.tool_settings
    screen = context.screen

    # layout.separator_spacer()
    if not context.area.ui_type == "TIMELINE":
        row = layout.row()
        if scene.show_subframe:
            row.scale_x = 1.15
            row.prop(scene, "frame_float", text="")
        else:
            row.scale_x = 0.95
            row.prop(scene, "frame_current", text="")

        row = layout.row(align=True)
        row.prop(scene, "use_preview_range", text="", toggle=True)
        sub = row.row(align=True)
        sub.scale_x = 0.8
        if not scene.use_preview_range:
            sub.prop(scene, "frame_start", text="Start")
            sub.prop(scene, "frame_end", text="End")
        else:
            sub.prop(scene, "frame_preview_start", text="Start")
            sub.prop(scene, "frame_preview_end", text="End")


class DopesheetButtons:
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"

class TIME_PT_SetActiveObject(bpy.types.Operator):
	"""Create a new loop"""
	bl_idname = "ui.set_active_object"
	bl_label = "Select"

	def execute(self, context):
		context.view_layer.objects.active = context.object
		return {'FINISHED'}


class TIME_PT_auto_keyframing_Dopesheet(DopesheetButtons, bpy.types.Panel):
    bl_label = "Auto Keyframing"
    bl_options = {"HIDE_HEADER"}
    bl_region_type = "HEADER"
    bl_ui_units_x = 9

    def draw(self, context):
        layout = self.layout

        tool_settings = context.tool_settings
        prefs = context.preferences

        layout.active = tool_settings.use_keyframe_insert_auto

        layout.prop(tool_settings, "auto_keying_mode", expand=True)

        col = layout.column(align=True)
        col.prop(
            tool_settings,
            "use_keyframe_insert_keyingset",
            text="Only Active Keying Set",
            toggle=False,
        )
        if not prefs.edit.use_keyframe_insert_available:
            col.prop(tool_settings, "use_record_with_nla", text="Layered Recording")

        col.prop(tool_settings, "use_keyframe_cycle_aware")


def Add_Player():
    bpy.types.DOPESHEET_MT_editor_menus.append(draw_player)
    bpy.types.DOPESHEET_HT_header.append(draw_frame_range)

    bpy.types.GRAPH_MT_editor_menus.append(draw_player)
    bpy.types.GRAPH_HT_header.append(draw_frame_range)

    bpy.types.NLA_MT_editor_menus.append(draw_player)
    bpy.types.NLA_HT_header.append(draw_frame_range)

    bpy.types.SEQUENCER_MT_editor_menus.append(draw_player)
    bpy.types.SEQUENCER_HT_header.append(draw_frame_range)


def Remove_Player():
    bpy.types.DOPESHEET_MT_editor_menus.remove(draw_player)
    bpy.types.DOPESHEET_HT_header.remove(draw_frame_range)

    bpy.types.GRAPH_MT_editor_menus.remove(draw_player)
    bpy.types.GRAPH_HT_header.remove(draw_frame_range)

    bpy.types.NLA_MT_editor_menus.remove(draw_player)
    bpy.types.NLA_HT_header.remove(draw_frame_range)

    bpy.types.SEQUENCER_MT_editor_menus.remove(draw_player)
    bpy.types.SEQUENCER_HT_header.remove(draw_frame_range)


def register():
    bpy.utils.register_class(TIME_PT_auto_keyframing_Dopesheet)
    bpy.utils.register_class(TIME_PT_SetActiveObject)
    Add_Player()


def unregister():
    bpy.utils.unregister_class(TIME_PT_SetActiveObject)
    bpy.utils.unregister_class(TIME_PT_auto_keyframing_Dopesheet)
    Remove_Player()


if __name__ == "__main__":
    register()
