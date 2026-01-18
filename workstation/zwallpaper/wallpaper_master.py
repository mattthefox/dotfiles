import glfw
from OpenGL.GL import *
import numpy as np
from PIL import Image
import time, os, random

# ------------------------
# Directories
# ------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
SHADERS_DIR = os.path.join(SCRIPT_DIR, "shaders")

# ------------------------
# Shader Utilities
# ------------------------
def load_shader_from_file(path):
    with open(path, "r") as f:
        return f.read()

def compile_shader(src, shader_type):
    shader = glCreateShader(shader_type)
    glShaderSource(shader, src)
    glCompileShader(shader)
    if not glGetShaderiv(shader, GL_COMPILE_STATUS):
        raise RuntimeError(glGetShaderInfoLog(shader).decode())
    return shader

def create_program(vs_src, fs_src):
    vs = compile_shader(vs_src, GL_VERTEX_SHADER)
    fs = compile_shader(fs_src, GL_FRAGMENT_SHADER)
    prog = glCreateProgram()
    glAttachShader(prog, vs)
    glAttachShader(prog, fs)
    glLinkProgram(prog)
    if not glGetProgramiv(prog, GL_LINK_STATUS):
        raise RuntimeError(glGetProgramInfoLog(prog).decode())
    glDeleteShader(vs)
    glDeleteShader(fs)
    return prog

# ------------------------
# Shader Manager
# ------------------------
class ShaderManager:
    def __init__(self, base_dir=SHADERS_DIR):
        self.base_dir = base_dir
        self.effects = self._discover_effects()

    def _discover_effects(self):
        effects = {}
        for name in os.listdir(self.base_dir):
            effect_dir = os.path.join(self.base_dir, name)
            if os.path.isdir(effect_dir):
                vs = os.path.join(effect_dir, "vertex.glsl")
                fs = os.path.join(effect_dir, "fragment.glsl")
                if os.path.exists(vs) and os.path.exists(fs):
                    effects[name] = (vs, fs)
        if not effects:
            raise RuntimeError("No shader effects found in " + self.base_dir)
        return effects

    def load(self, effect_name):
        if effect_name not in self.effects:
            raise ValueError(f"Effect '{effect_name}' not found. Available: {list(self.effects.keys())}")
        vs_path, fs_path = self.effects[effect_name]
        return create_program(load_shader_from_file(vs_path),
                              load_shader_from_file(fs_path))

    def random_effect(self):
        return random.choice(list(self.effects.keys()))

# ------------------------
# Texture Utilities
# ------------------------
def load_texture(path):
    img = Image.open(path).convert("RGBA")
    img_data = np.array(img)[::-1]  # flip vertically for OpenGL
    tex = glGenTextures(1)
    glBindTexture(GL_TEXTURE_2D, tex)
    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img.width, img.height, 0,
                 GL_RGBA, GL_UNSIGNED_BYTE, img_data)
    glGenerateMipmap(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR_MIPMAP_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    return tex

# ------------------------
# Wallpaper Manager
# ------------------------
class WallpaperManager:
    def __init__(self, folder, switch_interval=5):
        self.folder = os.path.expanduser(folder)
        self.switch_interval = switch_interval
        self.last_switch = 0
        self.current_tex = None
        self.wallpapers = [os.path.join(self.folder, f) for f in os.listdir(self.folder)
                           if f.lower().endswith((".jpg", ".jpeg", ".png"))]

        if not self.wallpapers:
            raise RuntimeError("No wallpapers found in " + folder)

        self.switch_wallpaper()

    def switch_wallpaper(self):
        path = random.choice(self.wallpapers)
        print(f"[Wallpaper] Switched to {os.path.basename(path)}")
        if self.current_tex:
            glDeleteTextures(1, [self.current_tex])
        self.current_tex = load_texture(path)
        self.last_switch = time.time()

    def update(self):
        if time.time() - self.last_switch > self.switch_interval:
            self.switch_wallpaper()

# ------------------------
# Effect Switcher
# ------------------------
class EffectSwitcher:
    def __init__(self, shader_mgr, switch_interval=15):
        self.shader_mgr = shader_mgr
        self.switch_interval = switch_interval
        self.last_switch = 0
        self.program = None
        self.time_loc = None
        self.switch()

    def switch(self):
        effect = self.shader_mgr.random_effect()
        print(f"[Shader] Switched to {effect}")
        if self.program:
            glDeleteProgram(self.program)
        self.program = self.shader_mgr.load(effect)
        self.time_loc = glGetUniformLocation(self.program, "u_time")
        self.last_switch = time.time()

    def update(self):
        if time.time() - self.last_switch > self.switch_interval:
            self.switch()



# ------------------------
# Main
# ------------------------
def main():
    if not glfw.init():
        raise RuntimeError("Failed to init GLFW")

    # Create borderless window
    glfw.window_hint(glfw.DECORATED, glfw.FALSE)
    glfw.window_hint(glfw.RESIZABLE, glfw.TRUE)
    glfw.window_hint(glfw.FLOATING, glfw.TRUE)
    window = glfw.create_window(3440, 1440, "shader-bg", None, None)
    glfw.make_context_current(window)

    # Fullscreen quad
    vertices = np.array([
        -1, -1, 0, 0,
         1, -1, 1, 0,
         1,  1, 1, 1,
        -1,  1, 0, 1,
    ], dtype=np.float32)
    indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

    vao = glGenVertexArrays(1)
    glBindVertexArray(vao)

    vbo = glGenBuffers(1)
    glBindBuffer(GL_ARRAY_BUFFER, vbo)
    glBufferData(GL_ARRAY_BUFFER, vertices.nbytes, vertices, GL_STATIC_DRAW)

    ebo = glGenBuffers(1)
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo)
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.nbytes, indices, GL_STATIC_DRAW)

    glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(0))
    glEnableVertexAttribArray(0)
    glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 16, ctypes.c_void_p(8))
    glEnableVertexAttribArray(1)

    # Managers
    shader_mgr = ShaderManager()
    effect_switcher = EffectSwitcher(shader_mgr, switch_interval=60 * 10)  # switch shader every 10 minutes
    wallpaper_mgr = WallpaperManager("~/Documents/Wallpapers", switch_interval=60 * 5)  # switch wallpaper every 5s

    start = time.time()

    while not glfw.window_should_close(window):
        glClear(GL_COLOR_BUFFER_BIT)

        # Update
        wallpaper_mgr.update()
        effect_switcher.update()

        # Use current shader
        glUseProgram(effect_switcher.program)
        t = time.time() - start
        glUniform1f(effect_switcher.time_loc, t)

        # Bind texture
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, wallpaper_mgr.current_tex)
        glUniform1i(glGetUniformLocation(effect_switcher.program, "u_tex"), 0)

        # Draw
        glBindVertexArray(vao)
        glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, None)

        glfw.swap_buffers(window)
        glfw.poll_events()

    glfw.terminate()

if __name__ == "__main__":
    main()
