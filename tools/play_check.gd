extends SceneTree
## Headless play check. Runs a game's main scene and drives it with scripted
## InputMap actions, asserting that the core loop completes.
##
## Usage:
##   godot --headless --path <project> -s res://tools/play_check.gd -- --path qa/playpaths/core.json
##
## Options (after the "--" separator):
##   --path <file>   play-path JSON, relative to the project (or res:// / absolute)
##   --capture       only works with a rendering driver, for CI under a virtual
##                   display. Is a no-op with a warning when running headless.
##
## Exit codes: 0 PASS, 1 FAIL (a step failed or timeout), 2 ERROR (bad input).
## Self-contained: depends on nothing outside this file.

var _steps: Array = []
var _timeout_ms: int = 30000
var _start_ms: int = 0
var _capture: bool = false
var _scene_path: String = ""
var _booted: bool = false
var _finished: bool = false
var _idx: int = 0
var _step_frame: int = 0
var _step_started: bool = false
var _signal_hits: Dictionary = {}
var _signal_conns: Dictionary = {}


func _initialize() -> void:
	var path_arg: String = ""
	var args: PackedStringArray = OS.get_cmdline_user_args()
	var i: int = 0
	while i < args.size():
		if args[i] == "--path" and i + 1 < args.size():
			path_arg = args[i + 1]
			i += 1
		elif args[i] == "--capture":
			_capture = true
		i += 1
	if path_arg == "":
		_error("missing --path <playpath.json>")
		return
	if not path_arg.begins_with("res://") and not path_arg.is_absolute_path():
		path_arg = "res://" + path_arg
	if not FileAccess.file_exists(path_arg):
		_error("play-path file not found: %s" % path_arg)
		return
	var parsed: Variant = JSON.parse_string(FileAccess.get_file_as_string(path_arg))
	if typeof(parsed) != TYPE_DICTIONARY:
		_error("play-path is not a valid JSON object: %s" % path_arg)
		return
	var d: Dictionary = parsed
	if typeof(d.get("steps", null)) != TYPE_ARRAY:
		_error("play-path has no \"steps\" array")
		return
	_steps = d["steps"]
	for n in range(_steps.size()):
		var msg: String = _validate_step(_steps[n])
		if msg != "":
			_error("step %d: %s" % [n, msg])
			return
	_timeout_ms = int(float(d.get("timeout_s", 30)) * 1000.0)
	_scene_path = str(d.get("main_scene", ""))
	if _scene_path == "":
		_scene_path = str(ProjectSettings.get_setting("application/run/main_scene", ""))
	if _scene_path == "" or not ResourceLoader.exists(_scene_path):
		_error("main scene missing: '%s'" % _scene_path)
		return
	if _capture:
		if DisplayServer.get_name() == "headless":
			push_warning("--capture ignored: headless mode has no rendering driver")
			print("PLAY_CHECK: WARN --capture is a no-op when headless")
		else:
			print("PLAY_CHECK: WARN --capture screenshots are not implemented yet")


func _validate_step(s: Variant) -> String:
	if typeof(s) != TYPE_DICTIONARY:
		return "not an object"
	var d: Dictionary = s
	if d.has("press") and not InputMap.has_action(str(d["press"])):
		return "unknown input action '%s'" % str(d["press"])
	for k in ["wait_frames", "press", "expect_node", "expect_signal", "expect_scene"]:
		if d.has(k):
			return ""
	return "unknown step kind"


func _error(reason: String) -> void:
	_finished = true
	print("PLAY_CHECK: ERROR %s" % reason)
	quit(2)


func _fail(reason: String) -> void:
	_finished = true
	print("PLAY_CHECK: FAIL %s" % reason)
	quit(1)


func _process(_delta: float) -> bool:
	if _finished:
		return false
	if not _booted:
		# Wait one frame so autoloads are ready before loading the main scene.
		_booted = true
		_start_ms = Time.get_ticks_msec()
		var packed: PackedScene = load(_scene_path) as PackedScene
		if packed == null:
			_error("could not load main scene: %s" % _scene_path)
			return false
		var inst: Node = packed.instantiate()
		root.add_child(inst)
		current_scene = inst
		_connect_signals()
		return false
	if Time.get_ticks_msec() - _start_ms > _timeout_ms:
		_fail("timeout after %d s at step %d" % [_timeout_ms / 1000, _idx])
		return false
	if _idx >= _steps.size():
		_finished = true
		print("PLAY_CHECK: PASS")
		quit(0)
		return false
	_run_step()
	return false


func _connect_signals() -> void:
	# Connect every expect_signal up front so a signal fired earlier is not missed.
	for s in _steps:
		if not s.has("expect_signal"):
			continue
		var key: String = str(s["expect_signal"])
		if _signal_conns.has(key):
			continue
		var parts: PackedStringArray = key.split(".")
		if parts.size() != 2:
			continue
		var node: Node = root.get_node_or_null(parts[0])
		if node == null or not node.has_signal(parts[1]):
			continue
		var argc: int = 0
		for sig in node.get_signal_list():
			if sig["name"] == parts[1]:
				argc = (sig["args"] as Array).size()
		var cb: Callable = Callable(self, "_on_signal").bind(key)
		if argc > 0:
			cb = cb.unbind(argc)
		node.connect(parts[1], cb)
		_signal_conns[key] = true
		_signal_hits[key] = 0


func _on_signal(key: String) -> void:
	_signal_hits[key] = int(_signal_hits.get(key, 0)) + 1


func _pass_step(kind: String, detail: String) -> void:
	print("STEP %d %s PASS %s" % [_idx, kind, detail])
	_idx += 1
	_step_frame = 0
	_step_started = false


func _fail_step(kind: String, detail: String) -> void:
	print("STEP %d %s FAIL %s" % [_idx, kind, detail])
	_fail("step %d %s: %s" % [_idx, kind, detail])


func _run_step() -> void:
	var s: Dictionary = _steps[_idx]
	if s.has("wait_frames"):
		if _step_frame >= int(s["wait_frames"]):
			_pass_step("wait_frames", "%d frames" % int(s["wait_frames"]))
		else:
			_step_frame += 1
	elif s.has("press"):
		var action: String = str(s["press"])
		var frames: int = int(s.get("frames", 1))
		if not _step_started:
			Input.action_press(action)
			_step_started = true
		if _step_frame >= frames:
			Input.action_release(action)
			_pass_step("press", "%s for %d frames" % [action, frames])
		else:
			_step_frame += 1
	elif s.has("expect_node"):
		var spec: String = str(s["expect_node"])
		var within: int = int(s.get("within_frames", 0))
		var found: Node = null
		if spec.begins_with("group:"):
			found = get_first_node_in_group(spec.substr(6))
		else:
			found = root.get_node_or_null(NodePath(spec))
		if found != null:
			_pass_step("expect_node", "%s found at frame +%d" % [spec, _step_frame])
		elif _step_frame >= within:
			_fail_step("expect_node", "%s not found within %d frames" % [spec, within])
		else:
			_step_frame += 1
	elif s.has("expect_signal"):
		var key: String = str(s["expect_signal"])
		var within2: int = int(s.get("within_frames", 0))
		if not _signal_conns.has(key):
			_fail_step("expect_signal", "%s cannot be connected (autoload or signal missing)" % key)
		elif int(_signal_hits[key]) > 0:
			_signal_hits[key] = int(_signal_hits[key]) - 1
			_pass_step("expect_signal", "%s emitted" % key)
		elif _step_frame >= within2:
			_fail_step("expect_signal", "%s not emitted within %d frames" % [key, within2])
		else:
			_step_frame += 1
	elif s.has("expect_scene"):
		var want: String = str(s["expect_scene"])
		var within3: int = int(s.get("within_frames", 0))
		var cs: Node = current_scene
		var have: String = cs.scene_file_path if cs != null else ""
		if have == want:
			_pass_step("expect_scene", "%s active" % want)
		elif _step_frame >= within3:
			_fail_step("expect_scene", "wanted %s, have '%s' after %d frames" % [want, have, within3])
		else:
			_step_frame += 1
