bl_info = {
    "name": "Render WAV (FFmpeg)",
    "author": "azephynight / modified by ChatGPT",
    "version": (1, 1, 0),
    "blender": (4, 0, 0),
    "location": "Sequencer > Add",
    "description": "Audio render using FFmpeg for stability and speed",
    "category": "Sequencer",
}

import bpy
import os
import subprocess
import tempfile
import shutil

class RENDER_OT_WAV(bpy.types.Operator):
    """Render Sequencer Audio to WAV (using FFmpeg)"""
    bl_idname = "sequencer.render_wav_ffmpeg"
    bl_label = "Render WAV (FFmpeg)"
    
    def execute(self, context):
        fps = context.scene.render.fps
        frame_start = context.scene.frame_start
        frame_end = context.scene.frame_end
        scene_duration_sec = (frame_end - frame_start) / fps
        scene_duration_ms = scene_duration_sec * 1000

        temp_dir = tempfile.mkdtemp()
        audio_inputs = []
        filters = []
        input_args = []
        output_path = os.path.join(bpy.path.abspath("//"), "sequencer_audio.wav")

        try:
            for idx, strip in enumerate(context.scene.sequence_editor.strips_all):
                if strip.type != 'SOUND' or strip.mute:
                    continue

                strip_path = bpy.path.abspath(strip.sound.filepath)
                if not os.path.isfile(strip_path):
                    self.report({'WARNING'}, f"Missing audio file: {strip_path}")
                    continue

                # Timing calculations
                clip_start_sec = (strip.frame_final_start - frame_start) / fps
                offset_sec = strip.frame_offset_start / fps
                duration_sec = strip.frame_final_duration / fps
                volume = strip.volume

                # Generate filter for each audio strip
                input_args.extend(['-i', strip_path])
                filter_cmd = (
                    f"[{idx}:a]"
                    f"atrim=start={offset_sec}:duration={duration_sec},"
                    f"adelay={int(clip_start_sec * 1000)}|{int(clip_start_sec * 1000)},"
                    f"volume={volume}[a{idx}]"
                )
                filters.append(filter_cmd)
                audio_inputs.append(f"[a{idx}]")

            if not audio_inputs:
                self.report({'WARNING'}, "No valid audio strips to render.")
                return {'CANCELLED'}

            # Mix all audio tracks together
            filter_complex = ";".join(filters) + f";{''.join(audio_inputs)}amix=inputs={len(audio_inputs)}:normalize=0[aout]"
            ffmpeg_cmd = ['ffmpeg', '-y'] + input_args + [
                '-filter_complex', filter_complex,
                '-map', '[aout]',
                '-ac', '2',
                output_path
            ]

            subprocess.run(ffmpeg_cmd, check=True)
            self.report({'INFO'}, f"Audio exported: {output_path}")

        except subprocess.CalledProcessError as e:
            self.report({'ERROR'}, f"FFmpeg failed: {e}")
        except Exception as e:
            self.report({'ERROR'}, f"Error: {str(e)}")
        finally:
            shutil.rmtree(temp_dir)

        return {'FINISHED'}

# Register operator
def menu_func(self, context):
    self.layout.operator(RENDER_OT_WAV.bl_idname, text="Render WAV (FFmpeg)")

def menu_bar_func(self, context):
    self.layout.menu("SEQUENCER_MT_render")

def register():
    bpy.utils.register_class(RENDER_OT_WAV)
    bpy.types.SEQUENCER_MT_add.append(menu_func)
    bpy.types.TOPBAR_MT_render.append(menu_bar_func)

def unregister():
    bpy.utils.unregister_class(RENDER_OT_WAV)
    bpy.types.SEQUENCER_MT_add.remove(menu_func)
    bpy.types.TOPBAR_MT_render.remove(menu_bar_func)

if __name__ == "__main__":
    register()
