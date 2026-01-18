import bpy
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

class AttributeNamePG(bpy.types.PropertyGroup):
	name: bpy.props.StringProperty(name="Attribute Name")
	frame: bpy.props.IntProperty(name="Bake Frame")
 
bpy.types.Scene.tweak_paths = bpy.props.CollectionProperty(type=NLATweakData)

def register():
	bpy.utils.register_class(AttributeNamePG)
	bpy.types.Object.bake_attributes = bpy.props.CollectionProperty(type=AttributeNamePG)
	bpy.utils.register_class(NLATweakData)

def unregister():
	bpy.utils.unregister_class(NLATweakData)
	del bpy.types.Object.bake_attributes
	bpy.utils.unregister_class(AttributeNamePG)
