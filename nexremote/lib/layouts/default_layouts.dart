/// Default layouts stored as JSON strings.
/// Uses the v2 flat format: x, y, width, height, scale, color at top level.
class DefaultLayouts {
  static const String standardGamepad = '''
{
  "id": "standard_gamepad",
  "name": "Standard Gamepad",
  "version": "2.0",
  "orientation": "landscape",
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"dpad",          "type":"dpad",        "x":0.08,"y":0.40,"width":120,"height":120,"color":4283585106},
    {"id":"left_stick",    "type":"joystick",    "x":0.22,"y":0.62,"width":100,"height":100,"stick":"left","color":4283585106},
    {"id":"right_stick",   "type":"joystick",    "x":0.68,"y":0.62,"width":100,"height":100,"stick":"right","color":4283585106},
    {"id":"face_buttons",  "type":"face_buttons","x":0.82,"y":0.40,"width":120,"height":120,"color":4283585106},
    {"id":"l1",  "type":"button",  "x":0.07,"y":0.04,"width":70,"height":36,"label":"L1", "action":"L1", "color":4283585106},
    {"id":"l2",  "type":"trigger", "x":0.07,"y":0.17,"width":70,"height":36,"label":"L2", "trigger":"LT","color":4283585106},
    {"id":"r1",  "type":"button",  "x":0.87,"y":0.04,"width":70,"height":36,"label":"R1", "action":"R1", "color":4283585106},
    {"id":"r2",  "type":"trigger", "x":0.87,"y":0.17,"width":70,"height":36,"label":"R2", "trigger":"RT","color":4283585106},
    {"id":"select","type":"button","x":0.38,"y":0.88,"width":80,"height":34,"label":"SELECT","action":"SELECT","color":4283585106},
    {"id":"start", "type":"button","x":0.55,"y":0.88,"width":80,"height":34,"label":"START", "action":"START","color":4283585106}
  ]
}
''';

  static const String fpsLayout = '''
{
  "id": "fps_layout",
  "name": "FPS Gaming",
  "version": "2.0",
  "orientation": "landscape",
  "gyro_enabled": true,
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"left_stick","type":"joystick","x":0.12,"y":0.60,"width":110,"height":110,"stick":"left","color":4283585106},
    {"id":"shoot",  "type":"button","x":0.82,"y":0.55,"width":90,"height":90,"label":"FIRE", "action":"mouse_left", "color":4294901760},
    {"id":"aim",    "type":"button","x":0.70,"y":0.55,"width":70,"height":70,"label":"AIM",  "action":"mouse_right","color":4288423550},
    {"id":"jump",   "type":"button","x":0.12,"y":0.40,"width":68,"height":68,"label":"JUMP", "action":"keyboard_space","color":4284453836},
    {"id":"crouch", "type":"button","x":0.24,"y":0.40,"width":68,"height":68,"label":"DUCK", "action":"keyboard_ctrl","color":4284453836},
    {"id":"reload", "type":"button","x":0.82,"y":0.78,"width":68,"height":42,"label":"RELOAD","action":"keyboard_r","color":4283585106},
    {"id":"melee",  "type":"button","x":0.70,"y":0.75,"width":68,"height":42,"label":"MELEE","action":"keyboard_v","color":4283585106}
  ]
}
''';

  static const String racingLayout = '''
{
  "id": "racing_layout",
  "name": "Racing",
  "version": "2.0",
  "orientation": "landscape",
  "accel_enabled": true,
  "mode": "xinput",
  "haptic": true,
  "elements": [
    {"id":"gas",      "type":"button","x":0.86,"y":0.50,"width":90,"height":110,"label":"GAS",   "action":"keyboard_w","color":4284453836},
    {"id":"brake",    "type":"button","x":0.75,"y":0.50,"width":90,"height":110,"label":"BRAKE", "action":"keyboard_s","color":4294901760},
    {"id":"handbrake","type":"button","x":0.86,"y":0.78,"width":90,"height":52, "label":"HAND",  "action":"keyboard_space","color":4294944000},
    {"id":"nitro",    "type":"button","x":0.08,"y":0.55,"width":90,"height":90, "label":"NITRO", "action":"keyboard_shift","color":4288512204},
    {"id":"gear_up",  "type":"button","x":0.50,"y":0.06,"width":70,"height":40, "label":"↑",     "action":"keyboard_e","color":4283585106},
    {"id":"gear_down","type":"button","x":0.50,"y":0.88,"width":70,"height":40, "label":"↓",     "action":"keyboard_q","color":4283585106}
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
