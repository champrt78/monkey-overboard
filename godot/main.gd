extends Node2D
# Monkey Overboard — Godot 4.6 port of the verified HTML5 prototype.
# The world is drawn in a 135x240 low-res viewport (3 screens tall = 720) and
# stretched up with nearest filtering, so everything here is "buffer space":
# the web build's pixel-buffer coordinates map 1:1 to these world units.

# ---------- config (web constants / 4) ----------
const VIEW_W := 135.0
const VIEW_H := 240.0
const WORLD_W := 135.0
const WORLD_H := 720.0
const WATER_Y := 705.0      # WORLD_H - 15
const SEESAW_Y := 700.5     # WATER_Y - 4.5
const PLANK := 20.5
const TILT := 11.5
const CATCH_RX_BASE := 14.0
const CATCH_RX_MIN := 10.0
const MONKEY_R := 5.5
const GRAV := 225.0
const LAUNCH_VY := -525.0
const DRIFT_BASE := 24.0
const DRIFT_PER_LEVEL := 4.5
const DRIFT_MAX := 57.0
const BANANA_R := 4.0
const BANANA_BASE := 12
const BANANA_PER_LEVEL := 3
const BANANA_Y_MIN := 108.0
const BANANA_Y_MAX := 645.0
const GATOR_Y_OFFSET := 7.5
const GATOR_PATROL_SPEED := 14.0
const GATOR_DASH_SPEED := 190.0
const POINTS_BANANA := 10
const POINTS_CATCH := 2
const LIVES := 3

const MONKEY_FRAMES := preload("res://assets/sprites/monkey_frames.tres")
const GATOR_FRAMES := preload("res://assets/sprites/gator_frames.tres")
const BANANA_FRAMES := preload("res://assets/sprites/banana_frames.tres")
const SPLASH_FRAMES := preload("res://assets/sprites/splash_frames.tres")
const SEESAW_TEX := preload("res://assets/sprites/seesaw_plank.png")

# ---------- palette ----------
const SKY_TOP := Color("#8fd3e6")
const SKY_BOT := Color("#5fbf8e")
const TRUNK := Color("#7a4a1e")
const TRUNK_HI := Color("#915a26")
const LEAF := Color("#2f8f3f")
const LEAF_HI := Color("#3fae4f")
const WATER := Color("#1f6fb0")
const WATER_HI := Color("#2f86c8")
const M_BODY := Color("#8a5a2b")
const M_DARK := Color("#5e3a17")
const M_FACE := Color("#f3ddc0")
const M_EYE := Color("#1a1a1a")
const GATOR := Color("#2f7d2f")
const GATOR_HI := Color("#3a9a3a")
const GATOR_DK := Color("#1f4d1f")
const BANANA := Color("#ffd23c")
const BANANA_DK := Color("#d9a81f")
const WOOD := Color("#b9742f")
const WOOD_DK := Color("#8a5a2b")
const INK := Color("#10261a")

# ---------- state ----------
var phase := "menu"  # menu | playing | gameover
var score := 0
var best := 0
var lives := LIVES
var level := 1
var time := 0.0
var monkeys := []
var air_index := 1
var seesaw := {}
var bananas := []
var gator := {}
var catch_radius := CATCH_RX_BASE
var _font: Font
var _cam_y := 0.0

@onready var _mono: Array[AnimatedSprite2D] = [$Monkey0, $Monkey1]
@onready var _gator_spr: AnimatedSprite2D = $Gator
@onready var _seesaw_spr: Sprite2D = $Seesaw
@onready var _banana_pool: Node2D = $BananaPool
@onready var _splash_pool: Node2D = $SplashPool

@onready var _snd_launch: AudioStreamPlayer = $SndLaunch
@onready var _snd_catch: AudioStreamPlayer = $SndCatch
@onready var _snd_banana: AudioStreamPlayer = $SndBanana
@onready var _snd_splash: AudioStreamPlayer = $SndSplash
@onready var _snd_chomp: AudioStreamPlayer = $SndChomp
@onready var _snd_life_lost: AudioStreamPlayer = $SndLifeLost

# Headless self-test (run with `--headless --mo-selftest`): autopilots the
# see-saw so the catch/flip loop runs with no display, then reports + quits.
var _selftest := false
var _selftest_frames := 0
var _selftest_catches := 0

const SAVE_PATH := "user://monkey-overboard.save"

func _ready() -> void:
	randomize()
	_font = ThemeDB.fallback_font
	_load_best()
	monkeys = [_make_monkey("ground"), _make_monkey("air")]
	seesaw = _make_seesaw()
	gator = _make_gator()
	bananas = []
	if "--mo-selftest" in OS.get_cmdline_args() or "--mo-selftest" in OS.get_cmdline_user_args():
		_selftest = true
		start_game()

# ---------- factories ----------
func _make_monkey(state: String) -> Dictionary:
	return {"x": 0.0, "y": 0.0, "vx": 0.0, "vy": 0.0, "state": state}

func _make_seesaw() -> Dictionary:
	return {"x": WORLD_W / 2.0, "target_x": WORLD_W / 2.0, "up_side": 1}

func _make_gator() -> Dictionary:
	return {"x": WORLD_W / 2.0, "dir": 1, "mode": "patrol", "target_x": WORLD_W / 2.0, "chomp_timer": 0.0}

func _up_end() -> Vector2:
	return Vector2(seesaw.x + seesaw.up_side * PLANK, SEESAW_Y - TILT)

func _down_end() -> Vector2:
	return Vector2(seesaw.x - seesaw.up_side * PLANK, SEESAW_Y)

func _drift_for_level() -> float:
	return min(DRIFT_MAX, DRIFT_BASE + DRIFT_PER_LEVEL * (level - 1))

func _catch_radius_for_level() -> float:
	return max(CATCH_RX_MIN, CATCH_RX_BASE - (level - 1) * 0.5)

func _rand_drift() -> float:
	return randf_range(-1.0, 1.0) * _drift_for_level()

func _generate_bananas() -> void:
	for child in _banana_pool.get_children():
		child.queue_free()
	bananas = []
	var count := BANANA_BASE + BANANA_PER_LEVEL * (level - 1)
	var margin := 12.0
	for i in count:
		var b := {
			"x": margin + randf() * (WORLD_W - margin * 2.0),
			"y": BANANA_Y_MIN + randf() * (BANANA_Y_MAX - BANANA_Y_MIN),
			"wobble": randf() * TAU,
		}
		var spr := AnimatedSprite2D.new()
		spr.sprite_frames = BANANA_FRAMES
		spr.play("default")
		spr.position = Vector2(b.x, b.y - _cam_y)
		b["spr"] = spr
		_banana_pool.add_child(spr)
		bananas.append(b)

# ---------- game flow ----------
func start_game() -> void:
	phase = "playing"
	score = 0
	lives = LIVES
	level = 1
	seesaw = _make_seesaw()
	gator = _make_gator()
	_generate_bananas()
	catch_radius = _catch_radius_for_level()
	for child in _splash_pool.get_children():
		child.queue_free()
	_reset_round()

func _reset_round() -> void:
	air_index = 1
	seesaw.up_side = 1
	var dn := _down_end()
	monkeys[0].state = "ground"
	monkeys[0].x = dn.x
	monkeys[0].y = dn.y - MONKEY_R
	_launch(monkeys[1], seesaw.x, SEESAW_Y - 15.0)

func _next_level() -> void:
	level += 1
	_generate_bananas()
	catch_radius = _catch_radius_for_level()

func _launch(m: Dictionary, x: float, y: float) -> void:
	m.state = "air"
	m.x = x
	m.y = y
	m.vy = LAUNCH_VY
	m.vx = _rand_drift()
	_snd_launch.play()

func _lose_life(splash_x: float) -> void:
	lives -= 1
	_snd_life_lost.play()
	_spawn_splash(splash_x, WATER_Y)
	_gator_chomp_at(splash_x)
	if lives <= 0:
		phase = "gameover"
		if score > best:
			best = score
			_save_best()
	else:
		_reset_round()

# ---------- physics (ported verbatim from the proven web build) ----------
func step(dt: float) -> String:
	var air: Dictionary = monkeys[air_index]
	var ground: Dictionary = monkeys[1 - air_index]

	seesaw.x += (seesaw.target_x - seesaw.x) * min(1.0, dt * 14.0)

	var dn := _down_end()
	ground.state = "ground"
	ground.x = dn.x
	ground.y = dn.y - MONKEY_R

	air.vy += GRAV * dt
	air.x += air.vx * dt
	air.y += air.vy * dt

	if air.x < MONKEY_R:
		air.x = MONKEY_R
		air.vx = abs(air.vx)
	elif air.x > WORLD_W - MONKEY_R:
		air.x = WORLD_W - MONKEY_R
		air.vx = -abs(air.vx)

	_grab_bananas(air)

	if air.vy > 0.0:
		var up := _up_end()
		var within_x: bool = abs(air.x - up.x) <= catch_radius
		var within_y: bool = air.y >= up.y - 8.5 and air.y <= up.y + 8.5
		if within_x and within_y:
			_do_catch(air, ground, up)
			return "catch"

	if air.y >= WATER_Y:
		air.y = WATER_Y
		return "miss"

	return ""

func _grab_bananas(air: Dictionary) -> void:
	var reach := MONKEY_R + BANANA_R
	var reach2 := reach * reach
	for i in range(bananas.size() - 1, -1, -1):
		var b: Dictionary = bananas[i]
		var dx: float = b.x - air.x
		var dy: float = b.y - air.y
		if dx * dx + dy * dy <= reach2:
			if b.has("spr") and is_instance_valid(b.spr):
				b.spr.queue_free()
			bananas.remove_at(i)
			score += POINTS_BANANA
			_snd_banana.play()

func _do_catch(air: Dictionary, ground: Dictionary, up: Vector2) -> void:
	var old_down := _down_end()
	_launch(ground, old_down.x, old_down.y - MONKEY_R)
	air.state = "ground"
	air.x = up.x
	air.y = up.y - MONKEY_R
	air.vx = 0.0
	air.vy = 0.0
	seesaw.up_side *= -1
	air_index = 1 - air_index
	score += POINTS_CATCH
	_snd_catch.play()

# ---------- gator ----------
func _gator_chomp_at(x: float) -> void:
	gator.mode = "dash"
	gator.target_x = clamp(x, 15.0, WORLD_W - 15.0)
	_snd_chomp.play()

func _update_gator(dt: float) -> void:
	match gator.mode:
		"patrol":
			gator.x += gator.dir * GATOR_PATROL_SPEED * dt
			if gator.x < 15.0:
				gator.x = 15.0
				gator.dir = 1
			elif gator.x > WORLD_W - 15.0:
				gator.x = WORLD_W - 15.0
				gator.dir = -1
		"dash":
			var d: float = gator.target_x - gator.x
			var stepd := GATOR_DASH_SPEED * dt
			if abs(d) <= stepd:
				gator.x = gator.target_x
				gator.mode = "chomp"
				gator.chomp_timer = 0.6
			else:
				gator.x += sign(d) * stepd
		"chomp":
			gator.chomp_timer -= dt
			if gator.chomp_timer <= 0.0:
				gator.mode = "patrol"

# ---------- splashes ----------
func _spawn_splash(x: float, y: float) -> void:
	_snd_splash.play()
	var spr := AnimatedSprite2D.new()
	spr.sprite_frames = SPLASH_FRAMES
	spr.position = Vector2(x, y - _cam_y)
	spr.animation_finished.connect(_on_splash_finished.bind(spr))
	spr.play("default")
	_splash_pool.add_child(spr)


func _on_splash_finished(spr: AnimatedSprite2D) -> void:
	if is_instance_valid(spr):
		spr.queue_free()

# ---------- sprite updates ----------
func _update_camera() -> void:
	_cam_y = WORLD_H - VIEW_H
	if phase == "playing" or phase == "gameover":
		var air: Dictionary = monkeys[air_index]
		_cam_y = clamp(air.y - VIEW_H * 0.45, 0.0, WORLD_H - VIEW_H)


func _update_monkey_sprites() -> void:
	for i in range(2):
		var m: Dictionary = monkeys[i]
		var spr: AnimatedSprite2D = _mono[i]
		spr.position = Vector2(m.x, m.y - _cam_y)
		spr.visible = true
		match m.state:
			"ground":
				spr.play("idle")
			"air":
				if m.vy < 0.0:
					spr.play("ascending")
				else:
					spr.play("descending")
		spr.flip_h = (m.vx < 0.0)


func _update_gator_sprite() -> void:
	var spr: AnimatedSprite2D = _gator_spr
	spr.position = Vector2(gator.x, WATER_Y + GATOR_Y_OFFSET - _cam_y)
	spr.visible = true
	match gator.mode:
		"patrol":
			spr.play("patrol")
		"dash":
			spr.play("alert")
		"chomp":
			spr.play("chomp")
	var face_dir: int = gator.dir
	if gator.mode == "dash" or gator.mode == "chomp":
		var d: float = gator.target_x - gator.x
		if d != 0.0:
			face_dir = int(sign(d))
	spr.flip_h = (face_dir < 0)


func _update_seesaw_sprite() -> void:
	var tilt_angle: float = atan2(TILT, PLANK) * seesaw.up_side
	_seesaw_spr.position = Vector2(seesaw.x, SEESAW_Y - _cam_y)
	_seesaw_spr.rotation = tilt_angle


func _update_banana_sprites() -> void:
	for b in bananas:
		if b.has("spr") and is_instance_valid(b.spr):
			var y: float = b.y + sin(time * 2.0 + b.wobble) * 0.75
			b.spr.position = Vector2(b.x, y - _cam_y)

# ---------- loop ----------
func _physics_process(delta: float) -> void:
	if _selftest and phase == "playing":
		# Autopilot: snap the raised end under the falling monkey.
		var a: Dictionary = monkeys[air_index]
		seesaw.target_x = clamp(a.x - seesaw.up_side * PLANK, PLANK, WORLD_W - PLANK)
		seesaw.x = seesaw.target_x
	if phase == "playing":
		var sub := 3
		var dt := delta / sub
		for i in sub:
			var ev := step(dt)
			_update_gator(dt)
			if ev == "catch":
				_selftest_catches += 1
			if ev == "miss":
				_lose_life(monkeys[air_index].x)
			if phase == "playing" and bananas.is_empty():
				_next_level()
			if phase != "playing":
				break
	else:
		_update_gator(delta)
	if _selftest:
		_selftest_frames += 1
		if _selftest_frames >= 1200:
			print("SELFTEST catches=%d score=%d lives=%d level=%d phase=%s bananas_left=%d"
				% [_selftest_catches, score, lives, level, phase, bananas.size()])
			get_tree().quit()

func _process(delta: float) -> void:
	time += delta
	_update_camera()
	_update_monkey_sprites()
	_update_gator_sprite()
	_update_seesaw_sprite()
	_update_banana_sprites()
	queue_redraw()

func _input(event: InputEvent) -> void:
	if event is InputEventScreenTouch:
		if event.pressed:
			_on_tap()
			_on_drag(event.position.x)
	elif event is InputEventScreenDrag:
		_on_drag(event.position.x)
	elif event is InputEventMouseButton:
		if event.pressed:
			_on_tap()
			_on_drag(event.position.x)
	elif event is InputEventMouseMotion:
		if event.button_mask & MOUSE_BUTTON_MASK_LEFT:
			_on_drag(event.position.x)

func _on_tap() -> void:
	if phase == "menu" or phase == "gameover":
		start_game()

func _on_drag(world_x: float) -> void:
	if phase == "playing":
		seesaw.target_x = clamp(world_x, PLANK, WORLD_W - PLANK)

# ---------- rendering ----------
func _draw() -> void:
	_draw_sky()
	_draw_tree()
	_draw_water()
	_draw_seesaw_base()
	_draw_hud()
	_draw_offscreen_indicator()
	if phase != "playing":
		_draw_overlay()

# world helpers (apply camera offset)
func _wy(y: float) -> float:
	return y - _cam_y

func _rect(x: float, y: float, w: float, h: float, c: Color) -> void:
	draw_rect(Rect2(Vector2(x, _wy(y)), Vector2(w, h)), c)

func _circ(x: float, y: float, r: float, c: Color) -> void:
	draw_circle(Vector2(x, _wy(y)), r, c)

func _ln(x1: float, y1: float, x2: float, y2: float, w: float, c: Color) -> void:
	draw_line(Vector2(x1, _wy(y1)), Vector2(x2, _wy(y2)), c, w)

func _draw_sky() -> void:
	# vertical gradient sampled across the visible slice, as a few flat bands
	var bands := 12
	for i in bands:
		var t0 := (_cam_y + VIEW_H * i / bands) / WORLD_H
		draw_rect(Rect2(Vector2(0, VIEW_H * i / bands), Vector2(VIEW_W, VIEW_H / bands + 1)),
			SKY_TOP.lerp(SKY_BOT, clamp(t0, 0.0, 1.0)))

func _draw_tree() -> void:
	var cx := WORLD_W / 2.0
	var top := 27.5
	var bottom := WATER_Y
	_rect(cx - 4.25, top, 8.5, bottom - top, TRUNK)
	_rect(cx - 4.25, top, 2.0, bottom - top, TRUNK_HI)
	var wy := 220.0 / 4.0
	var k := 0
	while wy < (WATER_Y - 45.0):
		var sidev := -1.0 if (k % 2 == 0) else 1.0
		_circ(cx + sidev * 22.5, wy, 13.0, LEAF)
		_circ(cx + sidev * 22.5 - 3.5, wy - 2.0, 6.0, LEAF_HI)
		wy += 90.0
		k += 1
	_circ(cx, 25.0, 22.0, LEAF)
	_circ(cx - 7.0, 21.0, 10.0, LEAF_HI)

func _draw_water() -> void:
	if WATER_Y - _cam_y > VIEW_H + 10.0:
		return
	var wy := WATER_Y
	var bottom := WORLD_H + 1.0
	_rect(0, wy, VIEW_W, bottom - wy, WATER)
	# chunky dither
	var y := int(wy)
	while y < int(bottom):
		var x := 0 if (y % 4 == 0) else 1
		while x < int(VIEW_W):
			_rect(x, y, 1.0, 1.0, WATER_HI)
			x += 2
		y += 2
	_rect(0, wy, VIEW_W, 1.0, Color("#bfe9ff"))

func _draw_seesaw_base() -> void:
	_rect(seesaw.x - 5.5, SEESAW_Y + 0.5, 11.0, 4.0, WOOD_DK)

func _draw_hud() -> void:
	draw_string(_font, Vector2(4, 12), str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, INK)
	draw_string(_font, Vector2(4, 22), "BEST " + str(best), HORIZONTAL_ALIGNMENT_LEFT, -1, 7, INK)
	for i in lives:
		_rect_screen(WORLD_W - 8.0 - i * 7.0, 5.0, 5.0, 5.0, M_BODY)
	draw_string(_font, Vector2(WORLD_W - 22, 22), "LV " + str(level), HORIZONTAL_ALIGNMENT_LEFT, -1, 7, INK)


func _draw_offscreen_indicator() -> void:
	if phase != "playing":
		return
	if SEESAW_Y - _cam_y <= VIEW_H - 2.5:
		return
	var x: float = seesaw.x
	var col := Color(BANANA.r, BANANA.g, BANANA.b, 0.95)
	draw_colored_polygon(PackedVector2Array([
		Vector2(x - 3.5, VIEW_H - 6.5),
		Vector2(x + 3.5, VIEW_H - 6.5),
		Vector2(x,       VIEW_H - 2.0),
	]), col)

func _rect_screen(x: float, y: float, w: float, h: float, c: Color) -> void:
	draw_rect(Rect2(Vector2(x, y), Vector2(w, h)), c)

func _draw_overlay() -> void:
	draw_rect(Rect2(Vector2(0, 0), Vector2(VIEW_W, VIEW_H)), Color(0.03, 0.10, 0.07, 0.55))
	if phase == "menu":
		draw_string(_font, Vector2(0, VIEW_H * 0.34), "MONKEY", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 18, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.34 + 18), "OVERBOARD", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 18, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.55), "Catch the monkey.", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 8, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.55 + 11), "Grab bananas. Mind the gator.", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 7, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.70), "Tap to start", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 11, Color.WHITE)
	else:
		draw_string(_font, Vector2(0, VIEW_H * 0.38), "GAME OVER", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 16, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.50), "Score " + str(score), HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 10, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.50 + 13), "Best " + str(best), HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 10, Color.WHITE)
		draw_string(_font, Vector2(0, VIEW_H * 0.66), "Tap to play again", HORIZONTAL_ALIGNMENT_CENTER, VIEW_W, 9, Color.WHITE)

# ---------- persistence ----------
func _save_best() -> void:
	var f := FileAccess.open(SAVE_PATH, FileAccess.WRITE)
	if f:
		f.store_32(best)
		f.close()

func _load_best() -> void:
	if FileAccess.file_exists(SAVE_PATH):
		var f := FileAccess.open(SAVE_PATH, FileAccess.READ)
		if f:
			best = f.get_32()
			f.close()
