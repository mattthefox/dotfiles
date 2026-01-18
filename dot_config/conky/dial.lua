require("cairo")
require("cairo_xlib")

colorMuted = "#333738"
colorRed = "#ee6a70"
colorYellow = "#7cd39f"
colorGreen = "#7fc8db"

-- Convert hex color string to normalized RGB (0-1)
function hex_to_rgb(hex)
    hex = hex:gsub("#", "")
    if #hex == 3 then
        hex = hex:sub(1,1)..hex:sub(1,1)
            ..hex:sub(2,2)..hex:sub(2,2)
            ..hex:sub(3,3)..hex:sub(3,3)
    end
    local r = tonumber(hex:sub(1,2), 16) / 255
    local g = tonumber(hex:sub(3,4), 16) / 255
    local b = tonumber(hex:sub(5,6), 16) / 255
    return r, g, b
end

-- Draw a dial with value text inside
function draw_dial(cr, center_x, center_y, radius, width, foreground, background, value, max_value, suffix)
    suffix = suffix or ""

    local fg_r, fg_g, fg_b = hex_to_rgb(foreground)
    local bg_r, bg_g, bg_b = hex_to_rgb(background)
    local angle = value * (360 / max_value)

    -- Background circle
    cairo_new_path(cr)
    cairo_set_line_width(cr, width)
    cairo_set_source_rgba(cr, bg_r, bg_g, bg_b, 1)
    cairo_arc(cr, center_x, center_y, radius, 0, 2 * math.pi)
    cairo_stroke(cr)

    -- Foreground arc
    cairo_new_path(cr)
    cairo_set_source_rgba(cr, fg_r, fg_g, fg_b, 1)
    cairo_arc(cr, center_x, center_y, radius, (-90) * (math.pi / 180), (angle - 90) * (math.pi / 180))
    cairo_stroke(cr)

    -- Draw text in center
	local display_text = string.format("%.0f%s", value, suffix)
    cairo_select_font_face(cr, "Sans", CAIRO_FONT_SLANT_NORMAL, CAIRO_FONT_WEIGHT_BOLD)
    cairo_set_font_size(cr, radius * 0.7)
    cairo_set_source_rgba(cr, fg_r, fg_g, fg_b, 1)

    local extents = cairo_text_extents_t:create()
    cairo_text_extents(cr, display_text, extents)
    local text_x = center_x - (extents.width / 2 + extents.x_bearing)
    local text_y = center_y - (extents.height / 2 + extents.y_bearing)

    cairo_move_to(cr, text_x, text_y)
    cairo_show_text(cr, display_text)
end

function conky_draw()
    if conky_window == nil then
        return
    end

    local cairo_surface = cairo_xlib_surface_create(
        conky_window.display,
        conky_window.drawable,
        conky_window.visual,
        conky_window.width,
        conky_window.height
    )
    local cr = cairo_create(cairo_surface)

	local temp = tonumber(conky_parse("${execi 5 sensors | awk '/^Tctl:/ {gsub(\"[+°C]\", \"\", $2); print $2; exit}'}")) or 0
	local t = math.min((temp-30) / 60, 1)  -- normalize 0–1 range

	draw_dial(cr, 35, 1315, 20, 6, colorGreen, colorMuted, temp, 90, "°")

    -- GPU Usage
    local gpu_usage = tonumber(conky_parse("${execi 5 nvidia-smi --query-gpu=utilization.gpu --format=csv,noheader,nounits}")) or 0
    draw_dial(cr, 35, 1260, 20, 6, colorYellow, colorMuted, gpu_usage, 90, "%")

    cairo_destroy(cr)
    cairo_surface_destroy(cairo_surface)
end
