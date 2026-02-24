/// Default layouts stored as JSON strings.
/// v2 flat format: x, y ∈ [0,1] are fractional positions of the element's
/// top-left corner relative to the screen. Width & height are logical pixels.
///
/// Safe-zone rule used here: assume a 720 × 360 landscape screen (logical).
/// Every element satisfies:
///   x + width  / 720 ≤ 0.93   (7% right margin)
///   y + height / 360 ≤ 0.88   (12% bottom margin — leaves room for navbar)
class DefaultLayouts {
  // ── Standard Gamepad ──────────────────────────────────────────────────────
  static const String standardGamepad = r'''
{
  "id": "standard_gamepad",
  "name": "Standard Gamepad",
  "version": "2.0",
  "orientation": "landscape",
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"dpad",        "type":"dpad",        "x":0.04,"y":0.32,"width":120,"height":120,"color":4283585106},
    {"id":"left_stick",  "type":"joystick",    "x":0.20,"y":0.55,"width":100,"height":100,"stick":"left","color":4283585106},
    {"id":"right_stick", "type":"joystick",    "x":0.62,"y":0.55,"width":100,"height":100,"stick":"right","color":4283585106},
    {"id":"face_buttons","type":"face_buttons","x":0.76,"y":0.32,"width":120,"height":120,"color":4283585106},
    {"id":"l1",  "type":"button", "x":0.04,"y":0.05,"width":70,"height":36,"label":"L1","action":"L1","color":4283585106},
    {"id":"l2",  "type":"trigger","x":0.04,"y":0.18,"width":70,"height":36,"label":"L2","trigger":"LT","color":4283585106},
    {"id":"r1",  "type":"button", "x":0.83,"y":0.05,"width":70,"height":36,"label":"R1","action":"R1","color":4283585106},
    {"id":"r2",  "type":"trigger","x":0.83,"y":0.18,"width":70,"height":36,"label":"R2","trigger":"RT","color":4283585106},
    {"id":"select","type":"button","x":0.37,"y":0.75,"width":76,"height":32,"label":"SELECT","action":"SELECT","color":4283585106},
    {"id":"start","type":"button","x":0.52,"y":0.75,"width":76,"height":32,"label":"START","action":"START","color":4283585106}
  ]
}
''';

  // ── FPS Layout ─────────────────────────────────────────────────────────────
  static const String fpsLayout = r'''
{
  "id": "fps_layout",
  "name": "FPS Gaming",
  "version": "2.0",
  "orientation": "landscape",
  "gyro_enabled": true,
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"left_stick","type":"joystick","x":0.06,"y":0.52,"width":110,"height":110,"stick":"left","color":4283585106},
    {"id":"shoot",  "type":"button","x":0.78,"y":0.40,"width":90,"height":90,"label":"FIRE","action":"mouse_left","color":4294901760},
    {"id":"aim",    "type":"button","x":0.65,"y":0.45,"width":70,"height":70,"label":"AIM","action":"mouse_right","color":4288423550},
    {"id":"jump",   "type":"button","x":0.23,"y":0.35,"width":68,"height":68,"label":"JUMP","action":"keyboard_space","color":4284453836},
    {"id":"crouch", "type":"button","x":0.06,"y":0.35,"width":68,"height":68,"label":"DUCK","action":"keyboard_ctrl","color":4284453836},
    {"id":"reload", "type":"button","x":0.78,"y":0.70,"width":68,"height":42,"label":"RELOAD","action":"keyboard_r","color":4283585106},
    {"id":"melee",  "type":"button","x":0.65,"y":0.70,"width":68,"height":42,"label":"MELEE","action":"keyboard_v","color":4283585106}
  ]
}
''';

  // ── Racing Layout ──────────────────────────────────────────────────────────
  static const String racingLayout = r'''
{
  "id": "racing_layout",
  "name": "Racing",
  "version": "2.0",
  "orientation": "landscape",
  "accel_enabled": true,
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"gas",      "type":"button","x":0.84,"y":0.38,"width":90,"height":100,"label":"GAS","action":"keyboard_w","color":4284453836},
    {"id":"brake",    "type":"button","x":0.72,"y":0.38,"width":90,"height":100,"label":"BRAKE","action":"keyboard_s","color":4294901760},
    {"id":"handbrake","type":"button","x":0.84,"y":0.72,"width":90,"height":48,"label":"HAND","action":"keyboard_space","color":4294944000},
    {"id":"nitro",    "type":"button","x":0.04,"y":0.45,"width":90,"height":90,"label":"NITRO","action":"keyboard_shift","color":4288512204},
    {"id":"gear_up",  "type":"button","x":0.44,"y":0.05,"width":70,"height":40,"label":"↑","action":"keyboard_e","color":4283585106},
    {"id":"gear_down","type":"button","x":0.44,"y":0.75,"width":70,"height":40,"label":"↓","action":"keyboard_q","color":4283585106}
  ]
}
''';

  static List<Map<String, dynamic>> getDefaultLayouts() {
    return [
      {
        'id': 'standard_gamepad',
        'name': 'Standard Gamepad',
        'description': 'Classic console controller layout',
        'data': standardGamepad,
      },
      {
        'id': 'fps_layout',
        'name': 'FPS Gaming',
        'description': 'FPS controls with gyro aiming',
        'data': fpsLayout,
      },
      {
        'id': 'racing_layout',
        'name': 'Racing',
        'description': 'Racing controls with tilt steering',
        'data': racingLayout,
      },
    ];
  }
}
