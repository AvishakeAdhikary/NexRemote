class DefaultLayouts {
  static const String standardGamepad = '''
{
  "id": "standard_gamepad",
  "name": "Standard Gamepad",
  "version": "1.0",
  "orientation": "landscape",
  "elements": [
    {
      "id": "dpad",
      "type": "dpad",
      "position": {"x": 0.1, "y": 0.5},
      "size": 120
    },
    {
      "id": "left_stick",
      "type": "joystick",
      "position": {"x": 0.25, "y": 0.7},
      "size": 100,
      "stick": "left"
    },
    {
      "id": "right_stick",
      "type": "joystick",
      "position": {"x": 0.75, "y": 0.7},
      "size": 100,
      "stick": "right"
    },
    {
      "id": "face_buttons",
      "type": "face_buttons",
      "position": {"x": 0.9, "y": 0.5},
      "size": 120
    },
    {
      "id": "l1",
      "type": "button",
      "position": {"x": 0.1, "y": 0.05},
      "size": {"width": 60, "height": 30},
      "label": "L1",
      "action": "L1"
    },
    {
      "id": "r1",
      "type": "button",
      "position": {"x": 0.9, "y": 0.05},
      "size": {"width": 60, "height": 30},
      "label": "R1",
      "action": "R1"
    },
    {
      "id": "l2",
      "type": "trigger",
      "position": {"x": 0.15, "y": 0.05},
      "size": {"width": 60, "height": 30},
      "label": "L2",
      "trigger": "LT"
    },
    {
      "id": "r2",
      "type": "trigger",
      "position": {"x": 0.85, "y": 0.05},
      "size": {"width": 60, "height": 30},
      "label": "R2",
      "trigger": "RT"
    },
    {
      "id": "select",
      "type": "button",
      "position": {"x": 0.4, "y": 0.9},
      "size": {"width": 80, "height": 30},
      "label": "SELECT",
      "action": "SELECT"
    },
    {
      "id": "start",
      "type": "button",
      "position": {"x": 0.6, "y": 0.9},
      "size": {"width": 80, "height": 30},
      "label": "START",
      "action": "START"
    }
  ]
}
''';

  static const String fpsLayout = '''
{
  "id": "fps_layout",
  "name": "FPS Gaming",
  "version": "1.0",
  "orientation": "landscape",
  "gyro_enabled": true,
  "elements": [
    {
      "id": "left_stick",
      "type": "joystick",
      "position": {"x": 0.15, "y": 0.7},
      "size": 100,
      "stick": "left"
    },
    {
      "id": "shoot",
      "type": "button",
      "position": {"x": 0.85, "y": 0.6},
      "size": {"width": 80, "height": 80},
      "label": "FIRE",
      "action": "mouse_left"
    },
    {
      "id": "aim",
      "type": "button",
      "position": {"x": 0.75, "y": 0.6},
      "size": {"width": 60, "height": 60},
      "label": "AIM",
      "action": "mouse_right"
    },
    {
      "id": "reload",
      "type": "button",
      "position": {"x": 0.85, "y": 0.8},
      "size": {"width": 60, "height": 40},
      "label": "R",
      "action": "keyboard_r"
    },
    {
      "id": "jump",
      "type": "button",
      "position": {"x": 0.15, "y": 0.5},
      "size": {"width": 60, "height": 60},
      "label": "JUMP",
      "action": "keyboard_space"
    },
    {
      "id": "crouch",
      "type": "button",
      "position": {"x": 0.25, "y": 0.5},
      "size": {"width": 60, "height": 60},
      "label": "CROUCH",
      "action": "keyboard_ctrl"
    }
  ]
}
''';

  static const String racingLayout = '''
{
  "id": "racing_layout",
  "name": "Racing",
  "version": "1.0",
  "orientation": "landscape",
  "accel_enabled": true,
  "elements": [
    {
      "id": "gas",
      "type": "button",
      "position": {"x": 0.9, "y": 0.6},
      "size": {"width": 80, "height": 100},
      "label": "GAS",
      "action": "keyboard_w"
    },
    {
      "id": "brake",
      "type": "button",
      "position": {"x": 0.8, "y": 0.6},
      "size": {"width": 80, "height": 100},
      "label": "BRAKE",
      "action": "keyboard_s"
    },
    {
      "id": "handbrake",
      "type": "button",
      "position": {"x": 0.9, "y": 0.8},
      "size": {"width": 80, "height": 60},
      "label": "HAND",
      "action": "keyboard_space"
    },
    {
      "id": "nitro",
      "type": "button",
      "position": {"x": 0.1, "y": 0.6},
      "size": {"width": 80, "height": 80},
      "label": "NITRO",
      "action": "keyboard_shift"
    },
    {
      "id": "gear_up",
      "type": "button",
      "position": {"x": 0.5, "y": 0.1},
      "size": {"width": 60, "height": 40},
      "label": "↑",
      "action": "keyboard_e"
    },
    {
      "id": "gear_down",
      "type": "button",
      "position": {"x": 0.5, "y": 0.9},
      "size": {"width": 60, "height": 40},
      "label": "↓",
      "action": "keyboard_q"
    }
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
        'description': 'Optimized for first-person shooters with gyro aiming',
        'data': fpsLayout,
      },
      {
        'id': 'racing_layout',
        'name': 'Racing',
        'description': 'Racing game controls with tilt steering',
        'data': racingLayout,
      },
    ];
  }
}