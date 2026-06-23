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
var splashes := []
var _font: Font
var _cam_y := 0.0

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
	bananas = []
	var count := BANANA_BASE + BANANA_PER_LEVEL * (level - 1)
	var margin := 12.0
	for i in count:
		bananas.append({
			"x": margin + randf() * (WORLD_W - margin * 2.0),
			"y": BANANA_Y_MIN + randf() * (BANANA_Y_MAX - BANANA_Y_MIN),
			"wobble": randf() * TAU,
		})

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
	splashes.clear()
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

func _lose_life(splash_x: float) -> void:
	lives -= 1
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
			bananas.remove_at(i)
			score += POINTS_BANANA

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

# ---------- gator ----------
func _gator_chomp_at(x: float) -> void:
	gator.mode = "dash"
	gator.target_x = clamp(x, 15.0, WORLD_W - 15.0)

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
	var parts := []
	for i in 10:
		parts.append({
			"x": x, "y": y,
			"vx": randf_range(-1.0, 1.0) * 30.0,
			"vy": -randf() * 55.0 - 15.0,
			"r": 1.0 + randf() * 1.3,
		})
	splashes.append({"parts": parts, "life": 1.0})

func _update_splashes(dt: float) -> void:
	for i in range(splashes.size() - 1, -1, -1):
		var s: Dictionary = splashes[i]
		s.life -= dt * 1.6
		for p in s.parts:
			p.vy += 150.0 * dt
			p.x += p.vx * dt
			p.y += p.vy * dt
		if s.life <= 0.0:
			splashes.remove_at(i)

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
	_update_splashes(delta)
	if _selftest:
		_selftest_frames += 1
		if _selftest_frames >= 1200:
			print("SELFTEST catches=%d score=%d lives=%d level=%d phase=%s bananas_left=%d"
				% [_selftest_catches, score, lives, level, phase, bananas.size()])
			get_tree().quit()

func _process(delta: float) -> void:
	time += delta
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
	_cam_y = WORLD_H - VIEW_H
	if phase == "playing" or phase == "gameover":
		var air: Dictionary = monkeys[air_index]
		_cam_y = clamp(air.y - VIEW_H * 0.45, 0.0, WORLD_H - VIEW_H)

	_draw_sky()
	_draw_tree()
	_draw_bananas()
	_draw_water()
	_draw_gator()
	_draw_splashes()
	_draw_seesaw()
	_draw_monkeys()
	_draw_hud()
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

func _draw_bananas() -> void:
	for b in bananas:
		var x: float = b.x
		var y: float = b.y + sin(time * 2.0 + b.wobble) * 0.75
		_rect(x - 2.0, y - 3.0, 2.0, 1.0, BANANA)
		_rect(x - 3.0, y - 1.0, 5.0, 2.0, BANANA)
		_rect(x - 2.0, y + 1.0, 4.0, 1.0, BANANA_DK)

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

func _draw_gator() -> void:
	var x: float = gator.x
	var y := WATER_Y + GATOR_Y_OFFSET
	var chomp: bool = gator.mode == "chomp"
	_circ(x, y, 11.0, GATOR if chomp else GATOR_HI)
	_circ(x + (8.0 if gator.dir >= 0 else -8.0), y - 1.0, 5.5, GATOR)
	_rect(x - 4.0, y - 5.0, 1.5, 1.5, GATOR_DK)
	_rect(x + 3.0, y - 5.0, 1.5, 1.5, GATOR_DK)
	if chomp:
		var tx := x + (2.0 if gator.dir >= 0 else -10.0)
		for i in 4:
			_rect(tx + i * 3.0, y - 2.0, 1.0, 1.0, Color.WHITE)

func _draw_seesaw() -> void:
	var up := _up_end()
	var dn := _down_end()
	_rect(seesaw.x - 5.5, SEESAW_Y + 0.5, 11.0, 4.0, WOOD_DK)
	_ln(dn.x, dn.y, up.x, up.y, 3.0, WOOD)
	_ln(dn.x, dn.y - 0.5, up.x, up.y - 0.5, 1.0, Color("#d68f43"))

func _draw_monkeys() -> void:
	for m in monkeys:
		_draw_monkey(m.x, m.y, m.state == "air")

func _draw_monkey(x: float, y: float, airborne: bool) -> void:
	var u := MONKEY_R
	# tail
	_ln(x - u * 0.3, y + u * 1.05, x - u * 1.3, y + u * 0.4, u * 0.32, M_DARK)
	# legs
	if airborne:
		_ln(x - u * 0.25, y + u * 1.0, x - u * 0.7, y + u * 0.35, u * 0.42, M_BODY)
		_ln(x + u * 0.25, y + u * 1.0, x + u * 0.7, y + u * 0.35, u * 0.42, M_BODY)
	else:
		_ln(x - u * 0.3, y + u * 1.0, x - u * 0.4, y + u * 1.7, u * 0.42, M_BODY)
		_ln(x + u * 0.3, y + u * 1.0, x + u * 0.4, y + u * 1.7, u * 0.42, M_BODY)
	# arms + hands
	if airborne:
		_ln(x - u * 0.5, y + u * 0.05, x - u * 0.95, y - u * 1.25, u * 0.36, M_BODY)
		_ln(x + u * 0.5, y + u * 0.05, x + u * 0.95, y - u * 1.25, u * 0.36, M_BODY)
		_circ(x - u * 0.95, y - u * 1.25, u * 0.22, M_DARK)
		_circ(x + u * 0.95, y - u * 1.25, u * 0.22, M_DARK)
	else:
		_ln(x - u * 0.5, y + u * 0.1, x - u * 0.95, y + u * 0.8, u * 0.36, M_BODY)
		_ln(x + u * 0.5, y + u * 0.1, x + u * 0.95, y + u * 0.8, u * 0.36, M_BODY)
		_circ(x - u * 0.95, y + u * 0.8, u * 0.22, M_DARK)
		_circ(x + u * 0.95, y + u * 0.8, u * 0.22, M_DARK)
	# body
	_circ(x, y + u * 0.5, u * 0.8, M_BODY)
	# ears
	_circ(x - u * 0.85, y - u * 0.5, u * 0.42, M_DARK)
	_circ(x + u * 0.85, y - u * 0.5, u * 0.42, M_DARK)
	_circ(x - u * 0.85, y - u * 0.5, u * 0.22, M_FACE)
	_circ(x + u * 0.85, y - u * 0.5, u * 0.22, M_FACE)
	# head + face
	_circ(x, y - u * 0.55, u * 0.85, M_BODY)
	_circ(x, y - u * 0.4, u * 0.52, M_FACE)
	# eyes
	_rect(x - u * 0.32, y - u * 0.62, 1.0, 1.0, M_EYE)
	_rect(x + u * 0.22, y - u * 0.62, 1.0, 1.0, M_EYE)

func _draw_splashes() -> void:
	for s in splashes:
		for p in s.parts:
			_rect(p.x, p.y, 1.0, 1.0, Color("#cdefff"))

func _draw_hud() -> void:
	draw_string(_font, Vector2(4, 12), str(score), HORIZONTAL_ALIGNMENT_LEFT, -1, 11, INK)
	draw_string(_font, Vector2(4, 22), "BEST " + str(best), HORIZONTAL_ALIGNMENT_LEFT, -1, 7, INK)
	for i in lives:
		_rect_screen(WORLD_W - 8.0 - i * 7.0, 5.0, 5.0, 5.0, M_BODY)
	draw_string(_font, Vector2(WORLD_W - 22, 22), "LV " + str(level), HORIZONTAL_ALIGNMENT_LEFT, -1, 7, INK)

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
