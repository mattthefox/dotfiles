import bpy
import math
import os
import random
import pydub
from pydub import AudioSegment
from mutagen.wave import WAVE  # Replace with appropriate format if not mp3

from bpy.types import Menu, Header
from contextlib import contextmanager
from collections import Counter

quickNameSymbols = {
    "LOOP":"⟳",
    "MALE":"🥒",
    "FEMALE":"🍑",   
    "SPEED":"⇉",
    "ADDITIVE":"✧",
    "ACTION":" ↯"
}

# Property update events
def useZLoopUpdate(self, context):
    if self.use_zloop:
        bpy.ops.wm.create_loop()
    else:
        bpy.ops.wm.delete_loop()
def animSpeedUpdate(self, context):
    bpy.ops.wm.update_time_for_speed()
def loopRangeUpdate(self,context):
    bpy.ops.wm.update_loop_markers()
def actionRename(self,context):
    bpy.ops.wm.quick_rename(newName=self.zname)

# Custom Properties
bpy.types.Action.use_animated_speed = bpy.props.BoolProperty(
    name= "Use Animated Speed",
    description= "Should this NLA strip use the animated speed provided?",
    default = False,
    override={'LIBRARY_OVERRIDABLE'},
)
bpy.types.Action.zanimtools = bpy.props.BoolProperty(
    name= "ZAnimTools",
    description= "Whether or not this action has been touched by ZAnimTools",
    default = False,
)
bpy.types.Scene.filter_layers = bpy.props.BoolProperty(
    name= "Filter Anim Layers",
    description= "Show only in-range strips?",
    default = True,
)
bpy.types.Scene.tweak_without_stack = bpy.props.BoolProperty(
    name= "Tweak without AnimStack",
    description= "Disable all influence and speed to preview the loop in its purest form.",
    default = True,
)
bpy.types.Scene.displayLoopPoints = bpy.props.BoolProperty(
    name= "Loop Markers",
    description= "",
    default = True,
)
bpy.types.Action.use_zloop = bpy.props.BoolProperty(
    name = "Use ZLoop",
    description= "Should this NLA strip enable auto-cycling?",
    default = False,
    update = useZLoopUpdate
)
bpy.types.Object.animated_speed = bpy.props.FloatProperty(
    name="Animated Speed",
    description= "The speed factor for this object.",
    default=1.0,
    options={'LIBRARY_EDITABLE','ANIMATABLE'},
    override={'LIBRARY_OVERRIDABLE'},
    update = animSpeedUpdate
)
bpy.types.Action.loop_start = bpy.props.IntProperty(
    name="Loop Start",
    description= "The start point of this action.",
    default = 0,
    update = loopRangeUpdate
)
bpy.types.Action.audio_pool = bpy.props.StringProperty(
    name="Audio Pool Folder",
    description= "Folder to randomly select audio files from.",
    maxlen=1024,
    subtype='DIR_PATH'
)
bpy.types.Action.audio_offset = bpy.props.IntProperty(
    name="Offset",
    description= "Offset for sound effect.",
    default = 0,
)
bpy.types.Action.audio_volume = bpy.props.FloatProperty(
    name="Gain",
    description= "Volume of audio.",
    default=1.0,
)
bpy.types.Action.loop_end = bpy.props.IntProperty(
    name="Loop End",
    description= "The end point of this action.",
    default = 1,
    update = loopRangeUpdate
)
bpy.types.Action.zname = bpy.props.StringProperty(
    name="Name",
    description= "Renames both the strip and action.",
    update = actionRename
)
bpy.types.Object.last_edited_action = bpy.props.StringProperty(
    name="Last Edited Action",
    description= "The last action edited by ZAnimTools.",
    options={'LIBRARY_EDITABLE'},
)

class NLATweakData(bpy.types.PropertyGroup):
    tweak_object = bpy.props.StringProperty (name = "Object", description = "")
    tweak_strip = bpy.props.StringProperty (name = "Strip", description = "")
    tweak_track = bpy.props.StringProperty (name = "Track", description = "")
bpy.utils.register_class(NLATweakData)
bpy.types.Scene.tweak_paths = bpy.props.CollectionProperty(type=NLATweakData)

@contextmanager
def sub_context(area_type: str):
    area = bpy.context.area
    former_area_type = area.type
    area.type = area_type
    try:
        yield area
    finally:
        area.type = former_area_type

# Define a custom panel class
class NLAActiveStripPanel(bpy.types.Panel):
    # Set the panel properties
    bl_label = "ZAnimTools"
    bl_idname = "NLA_PT_active_strip"
    bl_space_type = 'NLA_EDITOR'
    bl_region_type = 'UI'
    bl_category = "Strip"

    # Draw the panel content
    def draw(self, context):
        layout = self.layout
        # Get the active object and its animation data
        obj = context.object
        anim_data = obj.animation_data
        # Check if the object has animation data and an active NLA track
        row = layout.split(align=True)
        row.operator("wm.update_loop_markers",text="Loop Points",depress=context.scene.displayLoopPoints)
        row.operator("wm.update_time_for_speed",text="⟳ Time")
        row.operator("nla.stop_tweaking")
        if anim_data and anim_data.nla_tracks.active:
            # Get the active NLA track and its strips
            track = anim_data.nla_tracks.active
            strips = track.strips
            # Loop through the strips and find the active one
            for strip in strips:
                if strip.active:
                    # Display the name of the active strip
                    # layout.label(text=f"Active strip: {strip.name}")
                    layout.prop(strip.action, "zname");
                    layout.operator("wm.quick_new_action", text="Create Strip")
                    zloopRow = layout.row()
                    zloopRow.prop(strip.action, "use_zloop",text="")
                    frameRow = zloopRow.split(align=True)
                    frameRow.prop(strip.action, "loop_start")
                    frameRow.prop(strip.action, "loop_end")
                    speedRow = layout.row()
                    speedRow.prop(strip.action, "use_animated_speed")
                    speedRow.prop(obj, "animated_speed")
                    audioPoolRow = layout.row(align=True)
                    audioPoolRow.prop(strip.action,"audio_pool",text="")
                    row = layout.row();
                    row.prop(strip.action,"audio_offset")
                    break
            else:
                # No active strip found
                layout.label(text="No active strip")
        else:
            # No animation data or active NLA track
            layout.label(text="No active NLA track")
        row = layout.row()
        row.operator("wm.render_loops_audio")

class ZAnimToolsPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_zanimtools_panel"
    bl_label = "ZAnimTools"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_category = "Action"
 
    def draw(self, context):
        layout = self.layout
        obj = context.object
        row = layout.split(align=True)
        row.operator("wm.update_loop_markers",text="Loop Points",depress=context.scene.displayLoopPoints)
        row.operator("wm.update_time_for_speed",text="⟳ Time")

        if obj:
            if obj.animation_data:
                if obj.animation_data.action:
                    action = obj.animation_data.action

                    zloopRow = layout.row()
                    zloopRow.prop(action, "use_zloop",text="")

                    frameRow = zloopRow.split(align=True)
                    frameRow.prop(action, "loop_start")
                    frameRow.prop(action, "loop_end")

                    speedRow = layout.row()
                    speedRow.prop(action, "use_animated_speed",text="")
                    speedRow.prop(obj, "animated_speed")

                    audioPoolRow = layout.row(align=True)
                    audioPoolRow.prop(action,"audio_pool")
                    selectAudioPool = audioPoolRow.operator("zanimtools.audiopool.select")
                    selectAudioPool.action = action;
                else:
                    layout.label(text="No NLA controls available")
            else:
                layout.label(text="No animation data.")
            if obj.animation_data and obj.animation_data.action:
                row = layout.row()
                row.label(text="Active Action: " + obj.animation_data.action.name)
                row.operator("wm.quick_new_action",text="Quick new Action")
        else:
            layout.label(text="No active object.")

class AnimationLayersPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_zanimlayers_panel"
    bl_label = "Animation Layers"
    bl_space_type = "DOPESHEET_EDITOR"
    bl_region_type = "UI"
    bl_category = "Action"
 
    def draw(self, context):
        layout = self.layout
        obj = context.object
        layout.operator("nla.stop_tweaking")
        if obj:
            box = layout.box()
            row = box.row(align=True)
            row.prop(context.scene, "filter_layers",icon="FILTER",text="Active")
            row.prop(context.scene, "tweak_without_stack",icon="PRESET",text="Lower Stack")
            activeActionRow = box.row(align=True)
            foundActiveAction = False
            #layout.separator()
            if obj.animation_data:
                if obj.animation_data.nla_tracks:
                    for track in reversed(obj.animation_data.nla_tracks):
                        relevant_strip = None
                        # First, try to find a strip that contains the current frame.
                        for strip in track.strips:
                            if strip.frame_start <= context.scene.frame_current <= strip.frame_end:
                                relevant_strip = strip
                                break  # Found the strip containing the current frame, no need to search further.
                        # If no strip contains the current frame, find the last strip before the current frame.
                        if not relevant_strip:
                            for strip in track.strips:
                                if strip.frame_end < context.scene.frame_current:
                                    relevant_strip = strip
                                    break
                        # If that also failed, then find the first strip after the current frame.
                        if not relevant_strip:
                            for strip in reversed(track.strips):
                                if strip.frame_start > context.scene.frame_current:
                                    relevant_strip = strip
                                    break
                        # If a relevant strip was found, create its button.
                        if relevant_strip:
                            # If filter is enabled, check if this strip is in range.
                            if (relevant_strip.frame_end >= context.scene.frame_current >= relevant_strip.frame_start if context.scene.filter_layers else True):
                                row = box.row(align=True)
                                if context.scene.filter_layers:
                                    doEmboss = True
                                    #doEmboss = relevant_strip.action == obj.animation_data.action or obj.last_edited_action == relevant_strip.action.name
                                else:
                                    doEmboss =relevant_strip.frame_end >= context.scene.frame_current >= relevant_strip.frame_start
                                relevantStripName = relevant_strip.name
                                for symbol in quickNameSymbols.values(): # Remove all symbols from our name in order to tidy up
                                    relevantStripName = relevantStripName.replace(symbol,"")
                                #op = row.operator("nla.tweak_strip", depress = (relevant_strip.action == obj.animation_data.action),emboss = doEmboss, text=relevantStripName+" ["+track.name+"]")
                                """for i in range(50):
                                    relevantStripName += " "
                                """

                                if relevant_strip.action == obj.animation_data.action:
                                    foundActiveAction = True
                                op = row.operator("nla.tweak_strip", depress = (relevant_strip.action == obj.animation_data.action),emboss = doEmboss, text=relevantStripName)
                                op.track_name = track.name
                                op.strip_name = relevant_strip.name
                                row.prop(track,"is_solo",emboss=False,icon="SOLO_ON" if track.is_solo else "SOLO_OFF",text="")
                                row.prop(track,"mute",emboss=False,icon="HIDE_ON" if track.mute else "HIDE_OFF",text="")
                    if not foundActiveAction:
                        if obj.animation_data.action:
                            activeActionRow.operator("action.unlink",depress=True,text=obj.animation_data.action.name)
                else:
                    box.label(text="No tracks available.")
            else:
                box.label(text="No NLA strips available.")
        else:
            layout.label(text="No active object.")

tweaking_paths = {}

# Operators
class TweakNLAStripOperator(bpy.types.Operator):
    """Tweak NLA Strip"""
    bl_idname = "nla.tweak_strip"
    bl_label = "Tweak NLA Strip"
    
    track_name: bpy.props.StringProperty()
    strip_name: bpy.props.StringProperty()

    def execute(self, context):
        global tweaking_paths
        obj = context.object
        if obj and obj.animation_data and obj.animation_data.nla_tracks:
            if self.strip_name in tweaking_paths:
                del tweaking_paths[self.strip_name]
            else:
                tweaking_paths[self.strip_name] = [obj, self.track_name]
            prevArea = context.area.type
            context.area.type = "NLA_EDITOR"
            if context.scene.is_nla_tweakmode:
                bpy.ops.nla.tweakmode_exit()
            bpy.ops.nla.select_all(action='DESELECT')

            if len(tweaking_paths) > 0:
                for tweakStripName in tweaking_paths.keys():
                    data = tweaking_paths[tweakStripName]
                    tweakObject = data[0]
                    tweakTrackName = data[1]
                    tweakTrack = tweakObject.animation_data.nla_tracks.get(tweakTrackName)
                    tweakStrip = tweakTrack.strips.get(tweakStripName)
                    tweakObject.select_set(True)

                    tweakObject.animation_data.nla_tracks.active = tweakTrack
                    tweakStrip.select = True
                    tweakObject.last_edited_action = tweakStrip.action.name
            
                bpy.ops.nla.tweakmode_enter(use_upper_stack_evaluation=True)
                
            bpy.context.area.type = prevArea

        return {'FINISHED'}

class StopTweakingAll(bpy.types.Operator):
    """Tweak NLA Strip"""
    bl_idname = "nla.stop_tweaking"
    bl_label = "Stop All Tweaking"
    
    track_name: bpy.props.StringProperty()
    strip_name: bpy.props.StringProperty()

    def execute(self, context):
        global tweaking_paths
        if context.scene.is_nla_tweakmode:
            prevArea = context.area.type
            context.area.type = "NLA_EDITOR"
            bpy.ops.nla.tweakmode_exit()
            context.area.type = prevArea
        tweaking_paths.clear()

        return {'FINISHED'}

class UpdateTimeForSpeed(bpy.types.Operator):
    bl_idname = "wm.update_time_for_speed"
    bl_label = "Update Time for Speed"

    def execute(self, context):
        for obj in context.scene.objects:
            if obj.animation_data:
                #obj = context.object
                anim_data = obj.animation_data
                speedCurve = None

                for nla_track in anim_data.nla_tracks:
                    for strip in nla_track.strips:
                        if strip:
                            if strip.action:
                                if not strip.action.use_animated_speed:
                                    for fcu in strip.action.fcurves:
                                        if fcu.data_path == "animated_speed":
                                            speedCurve = fcu
                                            break;break;break
                
                if speedCurve:
                    for nla_track in anim_data.nla_tracks:
                        for strip in nla_track.strips:
                            print(strip)
                            if strip.action.use_animated_speed:
                                strip.use_animated_time = True
                                strip.use_animated_time_cyclic = False

                                integral = strip.action_frame_start
                                timeCurve = None
                                for fcu in strip.fcurves:
                                    if fcu.data_path == "strip_time":
                                        timeCurve = fcu
                                        break
                                
                                if timeCurve:
                                    timeCurve.keyframe_points.clear()
                                    for frame in range(int(strip.action_frame_start),int(strip.action_frame_end)):
                                        timeCurve.keyframe_points.insert(frame=frame,value=round(integral,2))
                                        integral += speedCurve.evaluate(frame)
                            else:
                                # clear animated time for ones that previously had animated speed, but no longer have it enabled
                                for fcu in strip.fcurves:
                                    if fcu.data_path == "strip_time":
                                        fcu.keyframe_points.clear()
                
        return {'FINISHED'}

class CreateLoopOperator(bpy.types.Operator):
    bl_idname = "wm.create_loop"
    bl_label = "Create Loop"

    prop_name: bpy.props.StringProperty(name="Property Name", default="Loop Dummy")
    prop_value: bpy.props.FloatProperty(name="Property Value", default=0.0)
    

    def execute(self, context):
        action = None

        obj = context.object
        if obj.animation_data:
            if obj.animation_data.action: # but use the action being edited as our last resort.
                action = obj.animation_data.action
            else:
                return {'CANCELLED'}
        
        if action:
            #[↺1] name of marker
            # Add the custom property to the object
            obj[self.prop_name] = self.prop_value
            if action.zanimtools:
                loopRangeUpdate(self,context)
            else:
                action.zanimtools = True
                action.loop_start = int(action.curve_frame_range[0])
                action.loop_end = int(action.curve_frame_range[1])
            # Insert dummy keyframes
            prevFrame = context.scene.frame_current
            bpy.context.scene.frame_current = action.loop_start
            obj.keyframe_insert(data_path='["%s"]' % self.prop_name)
            bpy.context.scene.frame_current = action.loop_end + 2 # offset by 2 just to make it easy to move
            obj.keyframe_insert(data_path='["%s"]' % self.prop_name)
            bpy.context.scene.frame_current = prevFrame
            
            # Loop through all the fcurves in the action
            for fcurve in action.fcurves:
            # Add a Cycles modifier to the fcurve if it doesn't exist already
                if not "AnimToolsLoop" in fcurve.modifiers:
                    modifier = fcurve.modifiers.new(type='CYCLES')
                    if modifier:
                        # Set the modifier options as desired
                        modifier.name="AnimToolsLoop"
                        modifier.mode_before = 'REPEAT'
                        modifier.mode_after = 'REPEAT'
                        modifier.use_restricted_range = True
                        modifier.frame_start = int(action.curve_frame_range[0])
                        modifier.frame_end = 99999

        return {'FINISHED'}

class DeleteLoopOperator(bpy.types.Operator):
    bl_idname = "wm.delete_loop"
    bl_label = "Delete Loop"

    def execute(self, context):
        obj = context.object
        if obj.animation_data:
            activeTrack =obj.animation_data.nla_tracks.active
            for strip in activeTrack.strips: 
                if strip.active:
                    action = strip.action

        if action:
            # Loop through all the fcurves in the action
            for fcurve in action.fcurves:
                for modifier in fcurve.modifiers:
                    if modifier.name == "AnimToolsLoop":
                        fcurve.modifiers.remove(modifier)

        return {'FINISHED'}

class QuickNewAction(bpy.types.Operator):
    bl_idname = "wm.quick_new_action"
    bl_label = "Quick New Action"

    blending: bpy.props.EnumProperty(name="Blend Mode",default=0,
        items = [
            ('ADD','Additive',''), 
            ('REP','Replace',''),
         ]
    )

    def execute(self, context):
        obj = context.object
        if obj.animation_data:
            activeTrack =obj.animation_data.nla_tracks.active
            selectedStrip = None
            for strip in activeTrack.strips: 
                if strip.active:
                    selectedStrip = strip

            if selectedStrip:
                existingAdditive = None
                bpy.ops.nla.tracks_add(above_selected=True)
                track = obj.animation_data.nla_tracks.active
                # track.name = "Additive" if self.blending == 'ADD' else "Replace"
                # create a new action
                action = selectedStrip.action.copy()
                action.name = context.object.name +"_"+track.name
                # delete the modifiers. (they confused the fuck out of me as well)
                for fcurve in action.fcurves:
                    for modifier in fcurve.modifiers:
                        fcurve.modifiers.remove(modifier)
                # disable these to prevent the confusion that i suffered.
                action.use_animated_speed = False
                action.use_zloop = False
                action.zanimtools = False
                action.zname = "New " + "Additive" if self.blending == 'ADD' else "Replace" + " Animation"
                
                #bpy.data.actions.new(context.object.name +"_"+track.name)
                prevAction = obj.animation_data.action
                # clear the keyframes
                for fcurve in action.fcurves:
                    fcurve.keyframe_points.clear()
                if self.blending == 'ADD':
                    for fcurve in action.fcurves:
                        fcurve.keyframe_points.insert(context.scene.frame_current,0)
                else:
                    obj.animation_data.action = action
                    old_type = bpy.context.area.type
                    bpy.context.area.type = "DOPESHEET_EDITOR"
                    bpy.ops.action.keyframe_insert(type = 'ALL')
                    bpy.context.area.type = old_type
                    obj.animation_data.action = prevAction

                # add the action to the track.
                strip = track.strips.new(track.name,context.scene.frame_current,action)
                strip.name = action.zname
                strip.blend_type = 'ADD' if self.blending == 'ADD' else 'REPLACE'
                


        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self)

class QuickRename(bpy.types.Operator):
    bl_idname = "wm.quick_rename"
    bl_label = "Quick Rename"

    newName: bpy.props.StringProperty(name="New Strip Name")

    def execute(self, context):

        # Get the active NLA track and its strips
        track = context.object.animation_data.nla_tracks.active
        strips = track.strips
        # Loop through the strips and find the active one
        for strip in strips:
            if strip.active:
                symbol = ""
                postSymbol = ""
                if strip.action.use_zloop:
                    postSymbol = quickNameSymbols["LOOP"]
                if "-m" in self.newName:
                    symbol += quickNameSymbols["MALE"]
                elif "-f" in self.newName:
                    symbol += quickNameSymbols["FEMALE"]
                if "speed" in self.newName.lower():
                    symbol = quickNameSymbols["SPEED"]
                if strip.blend_type == "ADD":
                    postSymbol += quickNameSymbols["ADDITIVE"]

                name = symbol + self.newName.replace("-m","").replace("-f","") + postSymbol

                strip.name = name
                strip.action.name = name+" "+quickNameSymbols["ACTION"]
                return {'FINISHED'}

        return {'CANCELLED'}

class AUDIOPOOL_OT_select(bpy.types.Operator):
    bl_idname = "wm.audiopool_select"
    bl_label = "Select Folder"
    bl_description = "Select a folder to use"

    action: bpy.props.PointerProperty(
        name="Action",
        type=bpy.types.Action,
        description="Action to set audio pool"
    )

    directory: bpy.props.StringProperty(
        name="Directory",
        description="Choose a directory",
        maxlen=1024,
        subtype='DIR_PATH'
    )

    def execute(self, context):
        # Store the selected directory in the scene properties
        context.scene.selected_folder = self.directory
        self.report({'INFO'}, f"Selected folder: {self.directory}")
        return {'FINISHED'}

    def invoke(self, context, event):
        context.window_manager.fileselect_add(self)
        return {'RUNNING_MODAL'}

def constructListofLoopPoints(self, context, condition):
    loopData = {}
    loopingStrips = []

    # Find every NLA strip that uses looping and store it.
    for obj in context.scene.objects:
        if obj.animation_data and obj.animation_data.nla_tracks:
            for track in obj.animation_data.nla_tracks:
                for strip in track.strips:
                    if condition(strip):
                        loopingStrips.append(strip)
        
    if loopingStrips:
        for strip in loopingStrips:
            loopData[strip] = []
            next_threshold = strip.action.loop_start
            length = strip.action.loop_end - strip.action.loop_start
            current_frame = strip.action.loop_start
            
            if strip.use_animated_time:
                fcurve = strip.fcurves.find("strip_time")  # Replace "property_name" with the actual property name

                if fcurve:
                    while current_frame <= strip.frame_end:  # Iterate over every frame
                        # If current time is at or past the next threshold
                        if fcurve.evaluate(current_frame) >= next_threshold:
                            loopData[strip].append(int(current_frame))
                            # Update the next threshold to the next multiple
                            next_threshold += length
                        # Move to the next frame
                        current_frame += 1
            else:
                while current_frame <= strip.frame_end:  # Iterate over every frame
                    # If current time is at or past the next threshold
                    if current_frame >= next_threshold:
                        loopData[strip].append(int(current_frame))
                        # Update the next threshold to the next multiple
                        next_threshold += length
                    # Move to the next frame
                    current_frame += 1

        return loopData
    else:
        return False

class ANIM_OT_rename_nearest_marker(bpy.types.Operator):
    """Rename the nearest marker"""
    bl_idname = "anim.rename_nearest_marker"
    bl_label = "Rename Nearest Marker"
    bl_options = {'REGISTER', 'UNDO'}
    bl_property = "marker_name"

    marker_name: bpy.props.StringProperty(
        name="Marker Name",
        description="New name for the nearest marker",
        default="Marker"
    )

    def nearestMarker(self, context):
        scene = context.scene
        current_frame = scene.frame_current

        nearest_marker = None
        min_distance = float('inf')

        for marker in scene.timeline_markers:
            distance = abs(marker.frame - current_frame)
            if distance < min_distance:
                min_distance = distance
                nearest_marker = marker

        # Rename the nearest marker
        if nearest_marker:
            return nearest_marker
        else:
            return None

    def execute(self, context):
        nearest_marker = self.nearestMarker(context)
        if nearest_marker is not None:
            nearest_marker.name = self.marker_name
            self.report({'INFO'}, f"Marker renamed to {self.marker_name}")
        else:
            self.report({'WARNING'}, "No marker found to rename")

        return {'FINISHED'}

        
    def invoke(self, context, event):
        nearest_marker = self.nearestMarker(context)
        if nearest_marker is not None:
            self.marker_name = nearest_marker.name
        return context.window_manager.invoke_props_dialog(self)

class UpdateLoopMarkers(bpy.types.Operator):
    bl_idname = "wm.update_loop_markers"
    bl_label = "Update Loop Markers"

    def execute(self, context):
        # [speedAction,loop_start,loop_end]
        for marker in context.scene.timeline_markers:
            if "↺" in marker.name:
                context.scene.timeline_markers.remove(marker)
        bpy.ops.marker.select_all(action='SELECT')
        if not context.scene.displayLoopPoints:
            def loopMarkersCondition(strip):
                return hasattr(strip.action, "use_zloop") and strip.action.use_zloop
            data = constructListofLoopPoints(self, context, loopMarkersCondition);
            print(data)
            for points in data.values():
                for i, point in enumerate(points):
                    name = "↺"+str(i)
                    context.scene.timeline_markers.new(name=name, frame=point)
                    context.scene.timeline_markers[name].select = False
            context.scene.displayLoopPoints = True
        else:
            bpy.ops.marker.select_all(action='DESELECT')
            context.scene.displayLoopPoints = False

        return {'FINISHED'}

class RenderLoopsAudio(bpy.types.Operator):
    bl_idname = "wm.render_loops_audio"
    bl_label = "Render Sound loops"

    def execute(self, context):
        def soundLoopsCondition(strip):
            return hasattr(strip.action, "use_zloop") and strip.action.use_zloop and not strip.action.audio_pool == ""
        data = constructListofLoopPoints(self,context, soundLoopsCondition)
        AudioSegment.ffmpeg = r"C:\Users\ngray\Desktop\ffmpeg.exe"
        AudioSegment.converter = r"C:\Users\ngray\Desktop\ffmpeg.exe"

        if data:
            audio_files = []
            start_times = []
            offsets = []
            fps = context.scene.render.fps
            frame_end = context.scene.frame_end
            frame_start = context.scene.frame_start

            for strip in data.keys():
                for point in data[strip]:
                    folder_path = strip.action.audio_pool
                    files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f))]
                    if not files:
                        print("Folder is empty.")
                        continue
                    audio_file = os.path.join(folder_path, random.choice(files))
                    audio_files.append(audio_file)
                    start_times.append(point/fps)
                    offsets.append(strip.action.audio_offset)

            # Initialize empty audio object
            final_audio = AudioSegment.silent(((frame_end-frame_start)/fps)*1000)
            # make stereo.
            final_audio.set_channels(2)

            # Loop through each audio file and start time
            for audio_file, start_time, offset in zip(audio_files, start_times, offsets):
                try:
                    # Read audio file using pydub
                    audio_segment = AudioSegment.from_file(audio_file)

                    # Convert to stereo if not already
                    if audio_segment.channels != 2:
                        audio_segment = audio_segment.set_channels(2)


                    # Get audio duration using mutagen
                    audio_duration = WAVE(audio_file).info.length
                    print(f"Audio duration: {audio_duration}s")

                    # Combine sliced audio with the existing final audio (consider silence for gaps)
                    final_audio = final_audio.overlay(audio_segment, position=int((start_time-((frame_start-offset)/fps)) * 1000))

                except Exception as e:
                    print(f"Error processing file {audio_file}: {e}")

            # Export final audio to desired output format
            path = os.path.join(bpy.path.abspath("//"), "zanim_audio_render_"+context.scene.name+".wav")
  
            print(final_audio)
            final_audio.export(path, format="wav")

            prevArea = bpy.context.area.type
            bpy.context.area.type = "SEQUENCE_EDITOR"

            bpy.ops.sequencer.select_all(action='DESELECT')

            for strip in bpy.context.scene.sequence_editor.sequences_all:
                if strip.type == "SOUND":
                    if strip.name == "zanim_render":
                        strip.select = True

            bpy.ops.sequencer.delete()

            bpy.ops.sequencer.sound_strip_add(filepath=path, frame_start=frame_start)

            for strip in bpy.context.selected_sequences:
                strip.name = "zanim_render"

            bpy.context.area.type = prevArea

            print("Compiled audio exported successfully.")
        else:
            return {'CANCELLED'}

        return {'FINISHED'}

def get_full_data_path(obj, property_name):
    """
    Attempts to find the full data path for any property of a given object.

    Args:
    obj (bpy.types.Object): The Blender object.
    property_name (str): The name of the property.

    Returns:
    str: The full data path or an empty string if not found.
    """
    try:
        # First, attempt to use path_from_id if the property is directly accessible
        if hasattr(obj, property_name):
            return obj.path_from_id(property_name)
    except TypeError:
        # If the direct approach fails, handle specific known cases
        pass

    # Handle custom properties, which are common and straightforward
    if property_name in obj.keys():
        return f'["{property_name}"]'

    # Handle properties in nested structures like shape keys
    if "shape_keys" in property_name and obj.type == 'MESH' and obj.data.shape_keys:
        key_blocks = obj.data.shape_keys.key_blocks
        if property_name in key_blocks:
            return key_blocks[property_name].path_from_id("value")

    # For materials, textures, modifiers, etc., you would add specific cases
    # For example, material properties:
    if "material" in property_name:
        path_parts = property_name.split('.')
        if len(path_parts) > 1 and path_parts[0] in obj.material_slots:
            mat = obj.material_slots[path_parts[0]].material
            if mat:
                # Assumes the material property follows the naming convention 'material.property'
                return mat.path_from_id(path_parts[1])

    # Add more cases as needed for different types of properties

    return ""  # Return empty string if no valid path is found

def add_bone_driver(context, armature, obj, data_path):
    """Utility function to add a bone and driver based on a custom property."""
    bpy.context.view_layer.objects.active = armature
    bpy.ops.object.mode_set(mode='EDIT')
    
    bone_name = "promoted_property"
    if "promoted_property" not in armature.data.edit_bones:
        new_bone = armature.data.edit_bones.new(bone_name)
        new_bone.head = (0, 0, 0)
        new_bone.tail = (0, 0, 1)
    object = eval('.'.join(split_path(data_path)[0:-1])) # beginning to second to last is the object.
    prop_name = split_path(data_path)[-1]
    custom_prop_name = ''.join(split_path(data_path)[-2:]).replace('"','').replace("'","").replace("[","").replace("]","").replace(".","_")[:60] # truncate 60 characters cause its the limit.
    bpy.ops.object.mode_set(mode='OBJECT')
    bone = armature.pose.bones[bone_name]
    prop_value = eval(data_path)  # Access custom property directly
    bone[custom_prop_name] = prop_value  # Set the custom property on the bone

    #pose.bones["promoted_property"]["bpy.data.shape_keys_Key_.key_blocks_A_.value"]
    #pose.bones["promoted_property"]["bpy.data.shape_keys_Key_.key_blocks_A_.value"]


    #should be
    # pose.bones["promoted_property"]["bpy.data.shape_keys[\"Key\"].key_blocks[\"A\"].value"]
    # current
    # pose.bones['promoted_property']['bpy.data.shape_keys["Key"].key_blocks["A"].value']


    # Adding a driver to the original property
    fcurve = object.driver_add(f'{prop_name}')
    var = fcurve.driver.variables.new()
    var.name = "var"
    var.type = 'SINGLE_PROP'
    var.targets[0].id = armature
    var.targets[0].data_path = f'pose.bones["promoted_property"]["{custom_prop_name}"]'
    fcurve.driver.expression = "var"
    for obj in bpy.context.scene.objects:
        obj.hide_render = obj.hide_render
    return {"armature": armature.name, "propertyName": custom_prop_name}

def split_path(data_path):
    '''
    Split a data_path into parts
    '''
    if not data_path:
        return []

    # extract names from data_path
    names = data_path.split('"')[1::2]
    data_path_no_names = ''.join(data_path.split('"')[0::2])

    # segment into chunks
    # ID props will be segmented by replacing ][ with ].[
    data_chunks = data_path_no_names.replace('][', '].[').split('.')
    # probably regex should be used here and things put into dictionary
    # so it's clear what chunk is what
    # depends of use case, the main idea is to extract names, segment, then put back

    # put names back into chunks where [] are
    for id, chunk in enumerate(data_chunks):
        if chunk.find('[]') > 0:
            data_chunks[id] = chunk.replace('[]', '["' + names.pop(0) + '"]')

    return data_chunks

def get_mirrored_name(name):
    if '.L' in name:
        return name.replace('.L', '.R')
    elif '.R' in name:
        return name.replace('.R', '.L')
    return None


modules = [
    AUDIOPOOL_OT_select,
    StopTweakingAll,
    RenderLoopsAudio,
    #AnimationLayersPanel,
    UpdateTimeForSpeed,
    CreateLoopOperator,
    DeleteLoopOperator,
    QuickNewAction,
    UpdateLoopMarkers,
    TweakNLAStripOperator,
    NLAActiveStripPanel,
    #ZAnimToolsPanel,
    QuickRename,
    ANIM_OT_rename_nearest_marker,
]

def on_startup():
    for screen in bpy.data.screens:
        bpy.ops.wm.collapse_all_collections()

# Register the menu and update the header
def register():
    for cls in modules:
        bpy.utils.register_class(cls)
    bpy.types.WindowManager.loopEnd = bpy.props.IntProperty()
    bpy.app.handlers.load_post.append(on_startup)
    
def unregister():
    bpy.app.handlers.load_post.remove(on_startup)
    for cls in reversed(modules):
        bpy.utils.unregister_class(cls)