extends Node2D

@export var main_path: NodePath = NodePath("..")

# Level banner display
var _banner: Label
var _banner_timer: float = 0.0
const BANNER_DURATION: float = 1.5

func _ready() -> void:
	_banner = Label.new()
	_banner.text = ""
	_banner.anchor_left = 0.5
	_banner.anchor_top = 0.5
	_banner.anchor_right = 0.5
	_banner.anchor_bottom = 0.5
	_banner.offset_left = -50.0
	_banner.offset_top = -15.0
	_banner.custom_minimum_size = Vector2(100.0, 30.0)
	_banner.add_theme_font_size_override("font_size", 16)
	_banner.visible = false
	add_child(_banner)

	# Load and apply the Press Start 2P font
	var font: Font = load("res://assets/fonts/PressStart2P-Regular.ttf")
	if font == null:
		font = ThemeDB.fallback_font
	_banner.add_theme_font_override("font", font)

# Show the level banner with the given level number
func show_level_banner(level: int) -> void:
	_banner.text = "LEVEL %d" % level
	_banner.modulate = Color.WHITE
	_banner_timer = BANNER_DURATION
	_banner.visible = true

func _process(delta: float) -> void:
	if _banner_timer > 0.0:
		_banner_timer -= delta
		if _banner_timer <= 0.0:
			_banner.visible = false
		else:
			# Fade out in the last 0.3 seconds
			var fade_start: float = 0.3
			if _banner_timer <= fade_start:
				var fade_alpha: float = _banner_timer / fade_start
				_banner.modulate = Color(1.0, 1.0, 1.0, fade_alpha)

func _draw() -> void:
	var main := get_node_or_null(main_path)
	if main and main.has_method("_draw_overlay_on") and main.phase != "playing":
		main._draw_overlay_on(self)
