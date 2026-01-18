#version 330 core
in vec2 fragUV;
out vec4 FragColor;

uniform float u_time;
uniform sampler2D u_tex;

float rand(float n) { return fract(sin(n) * 43758.5453); }

void main() {
    vec2 uv = fragUV;

    // -----------------------------
    // 1. Random horizontal line shifts
    // -----------------------------
    float line = floor((uv.y + u_time * 0.01) * 300.0);          // line index
    float shift = (rand(line + floor(u_time*2.0)) - 0.5) * 0.001; 
    uv.x += shift; 
    uv.x += 0.0005 * cos(uv.y * 60.0 + u_time * 3);

    // -----------------------------
    // 2. Chromatic aberration (RGB channel offsets)
    // -----------------------------
    float aberr = 0.001; // strength
    vec3 col;
    col.r = texture(u_tex, uv + vec2(aberr, 0.0)).r;
    col.g = texture(u_tex, uv).g;
    col.b = texture(u_tex, uv - vec2(aberr, 0.0)).b;

    // -----------------------------
    // 3. Subtle scanlines
    // -----------------------------
    float scan = sin(uv.y * 1200.0) * 0.04; // adjust frequency/strength
    col *= (1.0 - scan);

    // -----------------------------
    // 4. Vignette
    // -----------------------------
    float dist = length(uv - 0.5);
    float vignette = smoothstep(0.7, 0.9, dist);
    col *= (1.0 - vignette * 0.5);

    FragColor = vec4(col, 1.0);
}
