import 'package:flutter/material.dart';
import 'layout_manager.dart';
import '../input/gamepad_controller.dart' hide GamepadLayout;

/// Renders a [GamepadLayout] as a [Stack] of interactive controls.
/// This widget is purely visual — it delegates all input events to
/// the [GamepadController].
class LayoutWidget extends StatefulWidget {
  final GamepadLayout layout;
  final GamepadController gamepadController;

  /// When true, elements show selection outlines but don't fire input events.
  final bool editMode;

  /// Called when an element is tapped in edit mode.
  final void Function(LayoutElement element)? onElementTap;

  const LayoutWidget({
    super.key,
    required this.layout,
    required this.gamepadController,
    this.editMode = false,
    this.onElementTap,
  });

  @override
  State<LayoutWidget> createState() => _LayoutWidgetState();
}

class _LayoutWidgetState extends State<LayoutWidget> {
  final Set<String> _pressedIds = {};

  void _press(String id) => setState(() => _pressedIds.add(id));
  void _release(String id) => setState(() => _pressedIds.remove(id));
  bool _isPressed(String id) => _pressedIds.contains(id);

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;
    return Stack(
      children: widget.layout.elements
          .map((el) => _buildPositioned(el, size))
          .toList(),
    );
  }

  Widget _buildPositioned(LayoutElement el, Size screen) {
    final left = el.x * screen.width;
    final top = el.y * screen.height;

    Widget child;
    switch (el.type) {
      case 'button':
        child = _buildButton(el);
        break;
      case 'trigger':
        child = _buildTrigger(el);
        break;
      case 'joystick':
        child = _buildJoystick(el);
        break;
      case 'dpad':
        child = _buildDPad(el);
        break;
      case 'face_buttons':
        child = _buildFaceButtons(el);
        break;
      case 'macro':
        child = _buildMacroButton(el);
        break;
      default:
        child = const SizedBox.shrink();
    }

    if (el.scale != 1.0) {
      child = Transform.scale(scale: el.scale, child: child);
    }

    if (widget.editMode) {
      child = GestureDetector(
        onTap: () => widget.onElementTap?.call(el),
        child: Stack(
          children: [
            child,
            Positioned.fill(
              child: IgnorePointer(
                child: DecoratedBox(
                  decoration: BoxDecoration(
                    border: Border.all(
                      color: Colors.lightBlueAccent.withAlpha(180),
                      width: 2,
                    ),
                    borderRadius: BorderRadius.circular(4),
                  ),
                ),
              ),
            ),
          ],
        ),
      );
    }

    return Positioned(left: left, top: top, child: child);
  }

  // ── Element builders ─────────────────────────────────────────────────────

  Color _elColor(LayoutElement el) => Color(el.colorValue);

  Widget _buildButton(LayoutElement el) {
    final pressed = _isPressed(el.id);
    final color = _elColor(el);
    return GestureDetector(
      onTapDown: widget.editMode
          ? null
          : (_) {
              _press(el.id);
              widget.gamepadController.sendButton(
                el.action ?? el.label ?? '',
                true,
              );
            },
      onTapUp: widget.editMode
          ? null
          : (_) {
              _release(el.id);
              widget.gamepadController.sendButton(
                el.action ?? el.label ?? '',
                false,
              );
            },
      onTapCancel: widget.editMode
          ? null
          : () {
              _release(el.id);
              widget.gamepadController.sendButton(
                el.action ?? el.label ?? '',
                false,
              );
            },
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        width: el.width,
        height: el.height,
        decoration: BoxDecoration(
          color: pressed ? color : color.withAlpha(120),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color.withAlpha(200), width: 1.5),
          boxShadow: pressed
              ? [BoxShadow(color: color.withAlpha(100), blurRadius: 8)]
              : [],
        ),
        child: Center(
          child: Text(
            el.label ?? '',
            style: TextStyle(
              color: pressed ? Colors.white : Colors.white70,
              fontWeight: FontWeight.bold,
              fontSize: 13,
            ),
          ),
        ),
      ),
    );
  }

  Widget _buildTrigger(LayoutElement el) => _buildButton(el); // same visual

  Widget _buildMacroButton(LayoutElement el) {
    final pressed = _isPressed(el.id);
    final color = const Color(0xFF9333EA); // purple = macro
    return GestureDetector(
      onTapDown: widget.editMode
          ? null
          : (_) {
              _press(el.id);
              _fireMacro(el);
            },
      onTapUp: widget.editMode ? null : (_) => _release(el.id),
      onTapCancel: widget.editMode ? null : () => _release(el.id),
      child: AnimatedContainer(
        duration: const Duration(milliseconds: 80),
        width: el.width,
        height: el.height,
        decoration: BoxDecoration(
          color: pressed ? color : color.withAlpha(100),
          borderRadius: BorderRadius.circular(8),
          border: Border.all(color: color, width: 2),
          boxShadow: pressed
              ? [BoxShadow(color: color.withAlpha(120), blurRadius: 10)]
              : [],
        ),
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            const Icon(Icons.auto_fix_high, color: Colors.white, size: 16),
            Text(
              el.label ?? 'MACRO',
              style: const TextStyle(
                color: Colors.white,
                fontSize: 10,
                fontWeight: FontWeight.bold,
              ),
            ),
          ],
        ),
      ),
    );
  }

  void _fireMacro(LayoutElement el) {
    if (el.macro.isEmpty) return;
    widget.gamepadController.connectionManager.sendMessage({
      'type': 'macro',
      'steps': el.macro.map((s) => s.toJson()).toList(),
    });
  }

  Widget _buildJoystick(LayoutElement el) {
    const nubSize = 32.0;
    return _JoystickWidget(
      width: el.width,
      height: el.height,
      nubSize: nubSize,
      color: _elColor(el),
      disabled: widget.editMode,
      onMove: (x, y) =>
          widget.gamepadController.sendJoystick(el.stick ?? 'left', x, -y),
    );
  }

  Widget _buildDPad(LayoutElement el) {
    final sz = el.width;
    final tile = sz / 3;
    return SizedBox(
      width: sz,
      height: sz,
      child: _DPadWidget(
        tileSize: tile,
        color: _elColor(el),
        disabled: widget.editMode,
        onDir: (dir, pressed) {
          _pressed(el.id, dir, pressed);
          widget.gamepadController.sendDPad(dir, pressed);
        },
      ),
    );
  }

  void _pressed(String id, String sub, bool p) {
    final key = '$id:$sub';
    if (p) {
      _press(key);
    } else {
      _release(key);
    }
  }

  Widget _buildFaceButtons(LayoutElement el) {
    final sz = el.width;
    final pad = sz / 3;
    final btns = [
      ('Y', pad, 0.0, Colors.amber),
      ('A', pad, pad * 2, Colors.green),
      ('X', 0.0, pad, Colors.blue),
      ('B', pad * 2, pad, Colors.red),
    ];
    return SizedBox(
      width: sz,
      height: sz,
      child: Stack(
        children: btns.map((b) {
          final (lbl, left, top, color) = b;
          final pressed = _isPressed('${el.id}:$lbl');
          return Positioned(
            left: left,
            top: top,
            child: GestureDetector(
              onTapDown: widget.editMode
                  ? null
                  : (_) {
                      _press('${el.id}:$lbl');
                      widget.gamepadController.sendButton(lbl, true);
                    },
              onTapUp: widget.editMode
                  ? null
                  : (_) {
                      _release('${el.id}:$lbl');
                      widget.gamepadController.sendButton(lbl, false);
                    },
              onTapCancel: widget.editMode
                  ? null
                  : () {
                      _release('${el.id}:$lbl');
                      widget.gamepadController.sendButton(lbl, false);
                    },
              child: AnimatedContainer(
                duration: const Duration(milliseconds: 70),
                width: pad,
                height: pad,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  color: pressed ? color : color.withAlpha(70),
                  border: Border.all(color: color, width: 2),
                ),
                child: Center(
                  child: Text(
                    lbl,
                    style: TextStyle(
                      color: pressed ? Colors.white : color,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

// ── Joystick sub-widget ────────────────────────────────────────────────────────

class _JoystickWidget extends StatefulWidget {
  final double width, height, nubSize;
  final Color color;
  final bool disabled;
  final void Function(double x, double y) onMove;

  const _JoystickWidget({
    required this.width,
    required this.height,
    required this.nubSize,
    required this.color,
    required this.disabled,
    required this.onMove,
  });

  @override
  State<_JoystickWidget> createState() => _JoystickWidgetState();
}

class _JoystickWidgetState extends State<_JoystickWidget> {
  Offset _nub = Offset.zero;

  @override
  Widget build(BuildContext context) {
    final radius = (widget.width - widget.nubSize) / 2;
    return GestureDetector(
      onPanUpdate: widget.disabled
          ? null
          : (d) {
              final center = Offset(widget.width / 2, widget.height / 2);
              var delta = d.localPosition - center;
              final dist = delta.distance;
              if (dist > radius) delta = delta * (radius / dist);
              setState(
                () => _nub = Offset(delta.dx / radius, delta.dy / radius),
              );
              widget.onMove(_nub.dx, _nub.dy);
            },
      onPanEnd: widget.disabled
          ? null
          : (_) {
              setState(() => _nub = Offset.zero);
              widget.onMove(0, 0);
            },
      child: Container(
        width: widget.width,
        height: widget.height,
        decoration: BoxDecoration(
          color: const Color(0xFF1F2937),
          shape: BoxShape.circle,
          border: Border.all(color: widget.color.withAlpha(100), width: 1.5),
        ),
        child: Stack(
          children: [
            Center(
              child: Container(
                width: widget.width - 20,
                height: widget.height - 20,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  border: Border.all(color: Colors.white10),
                ),
              ),
            ),
            Positioned(
              left: widget.width / 2 + _nub.dx * radius - widget.nubSize / 2,
              top: widget.height / 2 + _nub.dy * radius - widget.nubSize / 2,
              child: Container(
                width: widget.nubSize,
                height: widget.nubSize,
                decoration: BoxDecoration(
                  shape: BoxShape.circle,
                  gradient: LinearGradient(
                    colors: [widget.color.withAlpha(220), widget.color],
                    begin: Alignment.topLeft,
                    end: Alignment.bottomRight,
                  ),
                  boxShadow: [
                    BoxShadow(
                      color: widget.color.withAlpha(120),
                      blurRadius: 8,
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

// ── DPad sub-widget ────────────────────────────────────────────────────────────

class _DPadWidget extends StatelessWidget {
  final double tileSize;
  final Color color;
  final bool disabled;
  final void Function(String dir, bool pressed) onDir;

  const _DPadWidget({
    required this.tileSize,
    required this.color,
    required this.disabled,
    required this.onDir,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        Positioned(
          left: tileSize,
          top: 0,
          child: _tile('UP', Icons.arrow_drop_up),
        ),
        Positioned(
          left: tileSize,
          top: tileSize * 2,
          child: _tile('DOWN', Icons.arrow_drop_down),
        ),
        Positioned(
          left: 0,
          top: tileSize,
          child: _tile('LEFT', Icons.arrow_left),
        ),
        Positioned(
          left: tileSize * 2,
          top: tileSize,
          child: _tile('RIGHT', Icons.arrow_right),
        ),
        Positioned(
          left: tileSize,
          top: tileSize,
          child: Container(
            width: tileSize,
            height: tileSize,
            color: const Color(0xFF374151),
          ),
        ),
      ],
    );
  }

  Widget _tile(String dir, IconData icon) {
    return GestureDetector(
      onTapDown: disabled ? null : (_) => onDir(dir, true),
      onTapUp: disabled ? null : (_) => onDir(dir, false),
      onTapCancel: disabled ? null : () => onDir(dir, false),
      child: Container(
        width: tileSize,
        height: tileSize,
        color: const Color(0xFF374151),
        child: Icon(icon, color: color, size: tileSize * 0.8),
      ),
    );
  }
}
