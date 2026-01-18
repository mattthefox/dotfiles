import os
import subprocess
import configparser
import curses
import sys
import time
import shutil
from pathlib import Path

DIR = "/home/mantra/workstation/theme_selector"
UPDATERS_DIR = "/home/mantra/.local/share/applications/theme_updaters"
CONFIG = os.path.join(DIR, "config.ini")
THEME_DIR = os.path.join(DIR, "themes")

WALLPAPERS_DIR = Path.home() / "Documents" / "Wallpapers"
CURATED_DIR = WALLPAPERS_DIR / "curated"
WALLPAPER_UPDATER = "/home/mantra/Scripts/HyprlandWallpapers.py"
PYTHON_EXE = sys.executable  # uses the current Python interpreter
# Basic injector types.


class Injector:
	"""Base class for a theme injector"""
	def __init__(self, file_path, theme_colors):
		if file_path[0] == ".":
			self.file_path = file_path.replace(".", DIR, 1)
		else:
			self.file_path = file_path
		self.theme_colors = theme_colors
		self.load()

	# Basic methods
	def load(self):
		with open(self.file_path, 'r', encoding='utf-8') as f:
			self.lines = f.readlines()

	def inject(self):
		return self.lines

	def save(self):
		with open(self.file_path, 'w', encoding='utf-8') as f:
			f.writelines(self.lines)

	# Shared methods
	def replaceLine(self, pattern, line, replacement):
		if 0 <= (line - 1) < len(self.lines):
			self.lines[line - 1] = pattern.replace("<x>", replacement) + "\n"
		return self.lines

class ReplaceLineInjector(Injector):
	"""Sample type for simpler injectors."""
	def __init__(self, file_path, search_pattern, line_number, replacement):
		super().__init__(file_path, {})
		self.search_pattern = search_pattern
		self.line_number = line_number 
		self.replacement = replacement

	def inject(self):
		super().replaceLine(self.search_pattern, self.line_number, self.replacement)
		return self.lines

class RofiInjector(Injector):
	"""Injects Rofi app launcher"""
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)

	def inject(self):
		super().replaceLine("\tmain-bg: <x>;", 2, self.theme_colors["base"]+"CC")        # Replaces the background color with base
		super().replaceLine("\tmain-fg: <x>;", 3, self.theme_colors["text"]) # Replaces the light background color
		super().replaceLine("\tmain-br: <x>;", 4, self.theme_colors["purple"])  # Replaces the border color
		super().replaceLine("\tmain-ex: <x>;", 5, self.theme_colors["yellow"]) # Replaces the selected color
		super().replaceLine("\tselect-bg: <x>;", 6, self.theme_colors["accent"])         # Replaces the blue color
		super().replaceLine("\tselect-fg: <x>;", 7, self.theme_colors["base"])         # Replaces the foreground color 1
		return self.lines

class CSSColorInjector(Injector):
	"""Injects colors into GTK/CSS-based styles.css theme file."""
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)
		self.color_keys = [
			"crust", "base", "surface", "overlay", "muted", "subtle", "text",
			"red", "orange", "yellow", "green", "blue", "purple", "accent", "transparent", "accent_fg"
		]

	def inject(self):
		new_lines = []
		for line in self.lines:
			stripped = line.strip()
			if stripped.startswith("@define-color"):
				parts = stripped.split()
				if len(parts) >= 3:
					color_key = parts[1]
					if color_key in self.theme_colors:
						new_color = self.theme_colors[color_key]
						if new_color.startswith("#"):
							# Convert hex to rgb
							hex_color = new_color.lstrip("#")
							if len(hex_color) == 6:
								rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
								line = f"@define-color {color_key} rgb({rgb[0]}, {rgb[1]}, {rgb[2]});\n"
							elif len(hex_color) == 8:  # RGBA
								rgba = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
								alpha = round(rgba[3] / 255, 2)
								line = f"@define-color {color_key} rgba({rgba[0]}, {rgba[1]}, {rgba[2]}, {alpha});\n"
			new_lines.append(line)
		self.lines = new_lines
		return self.lines
	
class KittyInjector(Injector):
	"""Injects Kitty Terminal colors in kitty.conf"""
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)
		self.theme_colors = {key: value.upper() for key, value in self.theme_colors.items()}  # Make all colors uppercase

	def inject(self):
		# Primary UI
		super().replaceLine("foreground <x>", 12, self.theme_colors["text"])
		super().replaceLine("background <x>", 13, self.theme_colors["crust"])
		super().replaceLine("selection_foreground <x>", 14, self.theme_colors["accent"])
		super().replaceLine("selection_background <x>", 15, self.theme_colors["base"])
		super().replaceLine("cursor <x>", 18, self.theme_colors["accent"])
		super().replaceLine("cursor_text_color <x>", 19, self.theme_colors["base"])
		super().replaceLine("url_color <x>", 22, self.theme_colors["accent"])

		# Colors
		super().replaceLine("color0  <x>", 51, self.theme_colors["red"])
		super().replaceLine("color8  <x>", 52, self.theme_colors["red"])
		super().replaceLine("color1  <x>", 55, self.theme_colors["red"])
		super().replaceLine("color9  <x>", 56, self.theme_colors["red"])
		super().replaceLine("color2  <x>", 63, self.theme_colors["orange"])
		super().replaceLine("color10  <x>", 64, self.theme_colors["orange"])
		super().replaceLine("color3  <x>", 59, self.theme_colors["yellow"])
		super().replaceLine("color11  <x>", 60, self.theme_colors["yellow"])
		super().replaceLine("color4  <x>", 67, self.theme_colors["green"])
		super().replaceLine("color12  <x>", 68, self.theme_colors["green"])
		super().replaceLine("color5  <x>", 71, self.theme_colors["blue"])
		super().replaceLine("color13  <x>", 72, self.theme_colors["blue"])
		super().replaceLine("color6  <x>", 75, self.theme_colors["purple"])
		super().replaceLine("color14  <x>", 76, self.theme_colors["purple"])
		super().replaceLine("color7  <x>", 79, self.theme_colors["accent"])
		super().replaceLine("color15  <x>", 80, self.theme_colors["accent"])
		
		return self.lines

class ConkyWidgetsInjector(Injector):
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)
		self.theme_colors = {key: '"'+value+'"' for key, value in self.theme_colors.items()}  # Make all colors uppercase

	def inject(self):
		# Primary UI
		super().replaceLine("colorMuted = <x>", 4, self.theme_colors["muted"])
		super().replaceLine("colorRed = <x>", 5, self.theme_colors["red"])
		super().replaceLine("colorYellow = <x>", 6, self.theme_colors["yellow"])
		super().replaceLine("colorGreen = <x>", 7, self.theme_colors["green"])
		
		
		return self.lines

import configparser
import io

class INIFileInjector(Injector):
	"""Injects into ini format."""
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)
		self.config = configparser.ConfigParser()
		self.config.optionxform = str  # preserve case
		self.replacements = {}
		self._parse_ini()

	def _parse_ini(self):
		config_str = ''.join(self.lines)
		self.config.read_file(io.StringIO(config_str))

	def inject(self):
		# Mapping of kdeglobals color roles to theme colors
		for section, keys in self.replacements.items():
			if not self.config.has_section(section):
				self.config.add_section(section)
			for key, value in keys.items():
				self.config.set(section, key, value)

		# Rebuild self.lines from modified config
		output = io.StringIO()
		self.config.write(output, space_around_delimiters=False)
		self.lines = [line if line.strip() != '' else '\n' for line in output.getvalue().splitlines(True)]
		return self.lines

class KdeGlobalsInjector(INIFileInjector):
	"""Injects into KDE Plasma themes. Automatically assigns to the groups in .kdeglobals, but preserves the original file so KDE doesn't get bricked."""
	def inject(self):
		# Mapping of kdeglobals color roles to theme colors
		self.replacements = {
			"Colors:Window": {
				"BackgroundNormal": self.theme_colors["crust"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["text"]
			},
			"Colors:Header": {
				"BackgroundNormal": self.theme_colors["base"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["text"]
			},
			"Colors:View": {
				"BackgroundNormal": self.theme_colors["base"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["text"]
			},
			"Colors:Button": {
				"BackgroundNormal": self.theme_colors["base"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["text"]
			},
			"Colors:Selection": {
				"BackgroundNormal": self.theme_colors["accent"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["base"]
			},
			"Colors:Tooltip": {
				"BackgroundNormal": self.theme_colors["surface"],
				"BackgroundAlternate": self.theme_colors["base"],
				"ForegroundNormal": self.theme_colors["text"]
			},
			"General": {
				"AccentColor": self.theme_colors["accent"],
				"LastUsedCustomAccentColor": self.theme_colors["accent"]
			},
			"WM": {
				"activeBackground": self.theme_colors["crust"],
				"activeForeground": self.theme_colors["base"],
				"inactiveBackground": self.theme_colors["base"],
				"inactiveForeground": self.theme_colors["text"]
			}
		}

		return super().inject()

class GtkStyleInjector(Injector):
	"""Injects Kitty Terminal colors in kitty.conf"""
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)

	def inject(self):
		# Primary UI
		super().replaceLine("@define-color crust <x>;", 1, self.theme_colors["crust"])
		super().replaceLine("@define-color base <x>;", 2, self.theme_colors["base"])
		super().replaceLine("@define-color surface <x>;", 3, self.theme_colors["surface"])
		super().replaceLine("@define-color overlay <x>;", 4, self.theme_colors["overlay"])
		super().replaceLine("@define-color muted <x>;", 5, self.theme_colors["muted"])
		super().replaceLine("@define-color subtle <x>;", 6, self.theme_colors["subtle"])
		super().replaceLine("@define-color text <x>;", 7, self.theme_colors["text"])
		super().replaceLine("@define-color red <x>;", 8, self.theme_colors["red"])
		super().replaceLine("@define-color orange <x>;", 9, self.theme_colors["orange"])
		super().replaceLine("@define-color yellow <x>;", 10, self.theme_colors["yellow"])
		super().replaceLine("@define-color green <x>;", 11, self.theme_colors["green"])
		super().replaceLine("@define-color blue <x>;", 12, self.theme_colors["blue"])
		super().replaceLine("@define-color purple <x>;", 13, self.theme_colors["purple"])
		super().replaceLine("@define-color accent <x>;", 14, self.theme_colors["accent"])
		
		return self.lines

	def save(self):
		super().save()
		subprocess.run(["systemctl", "--user", "restart", "xdg-desktop-portal-gtk"])
		
class DunstInjector(Injector):
	def __init__(self, file_path, theme_colors):
		super().__init__(file_path, theme_colors)

	def inject(self):
		super().replaceLine('\tframe_color = "<x>"', 114, self.theme_colors["surface"])
		super().replaceLine('\thighlight= "<x>"', 341, self.theme_colors["accent"])

		# Low urgency
		super().replaceLine('\tbackground = "<x>99"', 345, self.theme_colors["base"])
		super().replaceLine('\tforeground = "<x>"', 346, self.theme_colors["text"])

		# Normal urgency
		super().replaceLine('\tbackground = "<x>99"', 351, self.theme_colors["base"])
		super().replaceLine('\tforeground = "<x>"', 352, self.theme_colors["text"])

		# Critical urgency
		super().replaceLine('\tbackground = "<x>99"', 358, self.theme_colors["base"])
		super().replaceLine('\tforeground = "<x>"', 359, self.theme_colors["red"])
		
		return self.lines

	def save(self):
		super().save()
		subprocess.run(["killall","dunst"])
		subprocess.run(["notify-send","Dunst theme reloaded."])

class RoundedCornersInjector(INIFileInjector):
	"""Injects into KDE Plasma themes. Automatically assigns to the groups in .kdeglobals, but preserves the original file so KDE doesn't get bricked."""
	def inject(self):
		# Mapping of kdeglobals color roles to theme colors
		self.replacements = {
			"PrimaryOutline": {
				"OutlineColor": self.theme_colors["accent"],
				"InactiveOutlineColor": self.theme_colors["accent"]
			}
		}

		return super().inject()

class ColorDictInjector(Injector):
	def __init__(self, file_path, theme_colors, mapping, lower=False):
		super().__init__(file_path, theme_colors)
		self.mapping = mapping
		self.lower = lower

	def inject(self):
		# Check if the backup already exists
		self.backup_file_path = self.file_path + ".themebak"
		if not os.path.exists(self.backup_file_path):
			# If not, create the backup file
			shutil.copy(self.file_path, self.backup_file_path)
		
		# Open the backup file and apply replacements
		with open(self.backup_file_path, 'r', encoding='utf-8') as f:
			self.lines = f.readlines()

		# Perform replacements based on the mapping
		for color_name, color_value in self.mapping.items():
			# Iterate over each line and replace the color name with the corresponding hex value
			base = color_value.lower() if self.lower else color_value.upper() 
			replace = self.theme_colors[color_name].lower() if self.lower else self.theme_colors[color_name].upper()

			self.lines = [line.replace(base, replace) for line in self.lines]

		return self.lines


# Check if the directory exists
if not os.path.isdir(THEME_DIR):
	print("Theme directory not found!")
	exit(1)

# List theme files and extract their first lines
themes = []
for root, _, files in os.walk(THEME_DIR):
	for file in files:
		theme_path = os.path.join(root, file)
		themes.append(theme_path)

if len(themes) == 0:
	print("No themes found!")
	exit(1)

# Display themes with the first line as the description for the user to select
def select_theme(stdscr):
	curses.curs_set(0)  # Hide the cursor
	curses.start_color()
	curses.use_default_colors()

	#stdscr.clear()
	#stdscr.addstr(0, 0, "Select a theme")

	for i, theme in enumerate(themes, 1):
		with open(theme, 'r') as f:
			first_line = f.readline().strip()[1:]  # Remove the first character
		themes[i-1] = (theme, first_line)

	current_row = 0
	while True:
		stdscr.erase()
		stdscr.addstr(0, 0, "Select a theme:")

		for idx, (theme, description) in enumerate(themes):
			prefix = "-> " if idx == current_row else "   "
			stdscr.addstr(2 + idx, 0, f"{prefix}{description}")

		key = stdscr.getch()

		if key == curses.KEY_UP:
			current_row = (current_row - 1) % len(themes)
		elif key == curses.KEY_DOWN:
			current_row = (current_row + 1) % len(themes)
		elif key in (10, 13):  # Enter key
			break

	return themes[current_row][0]

def add_dim_variants(theme_colors):
	RATIO = 0.4
	from colorsys import rgb_to_hls, hls_to_rgb

	def hex_to_rgb(hex_color):
		hex_color = hex_color.lstrip('#')
		return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

	def rgb_to_hex(rgb):
		return "#{:02x}{:02x}{:02x}".format(*rgb)

	def mix_colors(c1, c2, mix_ratio):
		return tuple(int(c1[i] * (1 - mix_ratio) + c2[i] * mix_ratio) for i in range(3))

	base_rgb = hex_to_rgb(theme_colors["base"])
	for key in ["purple", "blue", "green", "yellow", "orange", "accent", "red"]:
		color_rgb = hex_to_rgb(theme_colors[key])
		dim_rgb = mix_colors(base_rgb, color_rgb, RATIO)
		theme_colors["dim" + key] = rgb_to_hex(dim_rgb)

	return theme_colors

# Initialize curses and select theme
selected_theme = curses.wrapper(select_theme)

# Read theme file
config = configparser.ConfigParser()
config.read(selected_theme)

# Convert to dict
theme_data = {section: dict(config[section]) for section in config.sections()}

# Extract and remove the "colors" list
colors_str = theme_data["colors"].pop("colors", "")  # remove key and get its value
wallpaper_colors = [c.strip() for c in colors_str.split(",") if c.strip()]

# Now theme_data["colors"] no longer contains the 'colors' key
theme_colors = add_dim_variants(theme_data["colors"])

print(wallpaper_colors)
print(CURATED_DIR)

print(f"You selected: {selected_theme}")

# A basic mapping scheme based on Catpuccin Mocha
CATPUCCIN_MOCHA_MAPPING = { 
	"crust": "#11111b",
	"base": "#1e1e2e",
	"surface": "#313244",
	"overlay": "#6c7086",
	"subtle": "#9399b2",
	"muted": "#bac2de",
	"text": "#cdd6f4",
	"purple": "#cba6f7",
	"blue": "#89b4fa",
	"green": "#a6e3a1",
	"yellow": "#f9e2af",
	"orange": "#fab387",
	"accent": "#ff0000",
	"red": "#f38ba8",

	"dimpurple": "#000001",
	"dimblue": "#000002",
	"dimgreen": "#000003",
	"dimyellow": "#000004",
	"dimorange": "#000005",
	"dimaccent": "#000006",
	"dimred": "#000007"
}

LITERAL_MAPPING = { 
	"crust": "#crust",
	"base": "#base",
	"surface": "#surface",
	"overlay": "#overlay",
	"subtle": "#subtle",
	"muted": "#muted",
	"text": "#text",
	"purple": "#purple",
	"blue": "#blue",
	"green": "#green",
	"yellow": "#yellow",
	"orange": "#orange",
	"accent": "#accent",
	"red": "#red",

	"dimpurple": "#dimpurple",
	"dimblue": "#dimblue",
	"dimgreen": "#dimgreen",
	"dimyellow": "#dimyellow",
	"dimorange": "#dimorange",
	"dimaccent": "#dimaccent",
	"dimred": "#dimred"
}

TANOSHI_MAPPING = { 
	"crust": "#000000",
	"base": "#342b2d",
	"surface": "#3a3236",
	"overlay": "#9a6a68",
	"subtle": "#9399b2",
	"muted": "#bac2de",
	"text": "#dbccbe",
	"purple": "#dc9bff",
	"blue": "#5dafc2",
	"green": "#65c06b",
	"yellow": "#e4d169",
	"orange": "#ff9d63",
	"accent": "#5dafc2",
	"red": "#ec6161"
}

# Update configs
injectors = [
	#ReplaceLineInjector("./config.ini", "include-file=<x>", 1, selected_theme),
	#ReplaceLineInjector("./modules/polywins.sh", "ini_file=<x>", 4, selected_theme),
	#ReplaceLineInjector("./modules/polybar-now-playing", "theme = \"<x>\"", 14, selected_theme),
	RofiInjector("/home/mantra/.config/rofi/theme.rasi", theme_colors),
	KittyInjector("/home/mantra/.config/kitty/current-theme.conf", theme_colors),
	ColorDictInjector("/home/mantra/.vscode-oss/extensions/catppuccin.catppuccin-vsc-3.17.0-universal/themes/mocha.json", theme_colors, CATPUCCIN_MOCHA_MAPPING), # VSCode Catpuccin Mocha Injector
	ColorDictInjector("/home/mantra/.config/starship.toml", theme_colors, LITERAL_MAPPING, lower=True),
	DunstInjector("/home/mantra/.config/dunst/dunstrc", theme_colors),
	ConkyWidgetsInjector("/home/mantra/.config/conky/dial.lua", theme_colors),
	#ColorDictInjector("/home/mantra/blender-git/build_linux/bin/4.1/scripts/presets/interface_theme/BaseTheme.xml", theme_colors, TANOSHI_MAPPING, True), # Blender theme injector
	#KdeGlobalsInjector("/home/mantra/.config/kdeglobals", theme_colors),
	#RoundedCornersInjector("/home/mantra/.config/kwinrc", theme_colors),
	CSSColorInjector("/home/mantra/.config/waybar/style.css", theme_colors),
	GtkStyleInjector("/home/mantra/.themes/Lavanda-Dark/gtk-3.0/gtk.css", theme_colors)
	
	# Replace hyprland border colors

]

# WALLPAPER COLOR CURATER
if CURATED_DIR.exists() and CURATED_DIR.is_dir():
	# Delete contents
	for item in CURATED_DIR.iterdir():
		if item.is_file() or item.is_symlink():
			item.unlink()
		elif item.is_dir():
			shutil.rmtree(item)
	
	# Add curated wallpapers.
	for color in wallpaper_colors:
		# Access directory
		folder = WALLPAPERS_DIR / color
		for wallpaper in folder.iterdir():
			if wallpaper.is_file():
				# Copy it to the curated folder.
				shutil.copy2(str(wallpaper), str(CURATED_DIR / wallpaper.name))

	# Finally, trigger a wallpaper update.

	# kill existing
	subprocess.Popen([PYTHON_EXE, WALLPAPER_UPDATER])
	time.sleep(2)


else:
	print(f"Directory not found: {CURATED_DIR}")


for injector in injectors:
	injector.lines = injector.inject()
	injector.save()

"""
# Apply KWin settings
#subprocess.run(["qdbus",  "org.kde.KWin",  "/KWin", "reconfigure"])
subprocess.run(["nohup", "kwin_x11","--replace"])

# Reboot polybar
subprocess.run(["killall", "polybar"])
subprocess.run(["nohup", os.path.join(DIR, "launch.sh")])
"""