#version 330 core

in vec2 fragUV;
out vec4 FragColor;

// ----------------- Shader Constants -----------------
const float DROP_SIZE       = 0.02;   // size of each raindrop
const float DENSITY         = 10.0;  // grid density (number of drops)
const float SPEED           = -2;   // fall speed
const float REFRACTION      = 0.05;  // strength of refraction
const float BRIGHTNESS      = 0.5;   // brightness of drops
const float LAYER_SCALE     = 1.5;   // multiplier for second layer
const float TRAIL_LENGTH    = 0.15;   // how long the trail is
const int   TRAIL_STEPS     = 5;      // number of samples per trail

// ----------------- Helpers -----------------
float rand(vec2 p) {
    return fract(sin(dot(p, vec2(12.9898,78.233))) * 43758.5453);
}

float smoothDrop(float d, float size) {
    return 1.0 - smoothstep(0.0, size, d);
}

// ----------------- Rain Generation -----------------
float DropLayer(vec2 uv, float t, float layerOffset) {
    vec2 gridUV = uv * vec2(DENSITY, DENSITY);
    vec2 id = floor(gridUV);
    vec2 f = fract(gridUV) - 0.5;

    vec2 n = vec2(rand(id + layerOffset), rand(id + layerOffset + 100.0));
    float dropY = fract(t*SPEED + n.y) * 1.2 - 0.1;

    float dist = length(f - vec2(0.0, dropY));
    return smoothDrop(dist, DROP_SIZE) * n.x;
}

// ----------------- Smearing Trails -----------------
float DropsWithTrails(vec2 uv, float t, float layerOffset) {
    float mask = 0.0;
    for(int i=0; i<TRAIL_STEPS; i++){
        float stepTime = t - float(i)*(TRAIL_LENGTH/float(TRAIL_STEPS));
        mask += DropLayer(uv, stepTime, layerOffset) * (1.0 - float(i)/float(TRAIL_STEPS));
    }
    return clamp(mask, 0.0, 1.0);
}

// ----------------- Main -----------------
uniform sampler2D u_tex;    // background
uniform float u_time;       // animation time
uniform vec2 u_resolution;  // screen size

void main() {
    vec2 uv = fragUV;

    // Layer 1 with trails
    float rainMask1 = DropsWithTrails(uv, u_time, 0.0);

    // Layer 2 (scaled and offset) with trails
    float rainMask2 = DropsWithTrails(uv * LAYER_SCALE, u_time*1.2, 10.0);

    float rainMask = clamp(rainMask1 + rainMask2, 0.0, 1.0);

    // Refraction
    vec2 offset = vec2(0.0, rainMask) * REFRACTION;

    // Sample background texture
    vec3 base = texture(u_tex, uv + offset).rgb;

    // Overlay raindrops with trails
    vec3 rainColor = mix(base, base + vec3(0.7,0.7,1.0)*rainMask, BRIGHTNESS);

    FragColor = vec4(rainColor, 1.0);
}