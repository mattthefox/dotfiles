#version 330 core
in vec2 fragUV;
out vec4 FragColor;

uniform float u_time;
uniform sampler2D u_tex;

const float PI = 3.14159265359;

// Convert UV to polar coordinates
vec2 toPolar(vec2 uv) {
    vec2 centered = uv - 0.5;
    float r = length(centered);
    float a = atan(centered.y, centered.x);
    return vec2(a, r);
}

// Convert polar back to UV
vec2 toCartesian(vec2 polar) {
    return vec2(cos(polar.x), sin(polar.x)) * polar.y + 0.5;
}

void main() {
    vec2 uv = fragUV;

    // -----------------------------
    // 1. Kaleidoscope mapping
    // -----------------------------
    vec2 polar = toPolar(uv);

    // Number of slices (like a kaleidoscope mirror count)
    float slices = 6.0;
    float angle = mod(polar.x, 2.0 * PI / slices);
    angle = abs(angle - (PI / slices));
    polar.x = angle;

    // Map back to cartesian space
    uv = toCartesian(polar);

    // -----------------------------
    // 2. Psychedelic swirl distortion
    // -----------------------------
    float swirl = sin(u_time * 0.8 + uv.y * 10.0) * 0.05;
    uv += vec2(cos(u_time + uv.y * 20.0), sin(u_time + uv.x * 20.0)) * 0.01;
    uv += swirl;

    // -----------------------------
    // 3. Chromatic shifting
    // -----------------------------
    float aberr = 0.003;
    vec3 col;
    col.r = texture(u_tex, uv + vec2(aberr, 0.0)).r;
    col.g = texture(u_tex, uv).g;
    col.b = texture(u_tex, uv - vec2(aberr, 0.0)).b;

    // -----------------------------
    // 4. Pulse effect (color vibration)
    // -----------------------------
    float pulse = sin(u_time * 3.0) * 0.5 + 0.5;
    col *= vec3(0.8 + 0.2 * pulse, 0.7 + 0.3 * pulse, 1.0);

    FragColor = vec4(col, 1.0);
}
