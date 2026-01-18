#version 330 core
in vec2 fragUV;
out vec4 FragColor;

uniform float u_time;
uniform sampler2D u_tex;

void main() {
    vec2 uv = fragUV;

    FragColor = texture(u_tex, uv);
}
