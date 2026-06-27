extends Node2D

@export var main_path: NodePath = NodePath("..")

func _draw() -> void:
	var main := get_node_or_null(main_path)
	if main and main.has_method("_draw_overlay_on") and main.phase != "playing":
		main._draw_overlay_on(self)
