import 'dart:math';
import 'package:flutter/material.dart';
import '../layouts/layout_manager.dart';
import 'macro_editor_dialog.dart';

/// Full-screen drag-and-drop layout editor.
class LayoutEditorScreen extends StatefulWidget {
  final GamepadLayout layout;

  const LayoutEditorScreen({super.key, required this.layout});

  @override
  State<LayoutEditorScreen> createState() => _LayoutEditorScreenState();
}

class _LayoutEditorScreenState extends State<LayoutEditorScreen> {
  late GamepadLayout _layout;
  late List<LayoutElement> _elements;

  // Undo/Redo
  final List<List<LayoutElement>> _history = [];
  int _historyIndex = -1;

  // Selection
  String? _selectedId;
  LayoutElement? get _selected => _selectedId == null
      ? null
      : _elements.firstWhere(
          (e) => e.id == _selectedId,
          orElse: () => _elements.first,
        );

  // Grid snap
  bool _snapToGrid = true;
  static const double _gridSize = 8.0;

  // Drag state
  bool _dragging = false;

  // Active element being dragged
  Offset? _dragStart;
  double? _elStartX, _elStartY;

  // Resize handle tracking
  _ResizeHandle? _activeHandle;
  Offset? _resizeStart;
  double? _resizeStartW, _resizeStartH, _resizeStartX, _resizeStartY;

  // Inspector panel visibility
  bool _showInspector = true;

  // Colours for picker
  static const _swatches = [
    0xFF374151,
    0xFF1F2937,
    0xFF111827,
    0xFF3B82F6,
    0xFF60A5FA,
    0xFF2563EB,
    0xFF10B981,
    0xFF34D399,
    0xFF059669,
    0xFFEF4444,
    0xFFF87171,
    0xFFDC2626,
    0xFFF59E0B,
    0xFFFBBF24,
    0xFFD97706,
    0xFF9333EA,
    0xFFA855F7,
    0xFF7C3AED,
    0xFFEC4899,
    0xFFF472B6,
    0xFFDB2777,
    0xFFFFFFFF,
    0xFF6B7280,
    0xFF000000,
  ];

  @override
  void initState() {
    super.initState();
    _layout = widget.layout;
    _elements = List.from(widget.layout.elements);
    _pushHistory();
  }

  // ── History ──────────────────────────────────────────────────────────────

  void _pushHistory() {
    if (_historyIndex < _history.length - 1) {
      _history.removeRange(_historyIndex + 1, _history.length);
    }
    _history.add(_elements.map((e) => e).toList());
    if (_history.length > 20) _history.removeAt(0);
    _historyIndex = _history.length - 1;
  }

  void _undo() {
    if (_historyIndex > 0) {
      setState(() {
        _historyIndex--;
        _elements = List.from(_history[_historyIndex]);
        _selectedId = null;
      });
    }
  }

  void _redo() {
    if (_historyIndex < _history.length - 1) {
      setState(() {
        _historyIndex++;
        _elements = List.from(_history[_historyIndex]);
        _selectedId = null;
      });
    }
  }

  // ── Snap ─────────────────────────────────────────────────────────────────

  double _snap(double v) =>
      _snapToGrid ? (v / _gridSize).round() * _gridSize : v;

  double _snapFrac(double frac, double total) =>
      _snapToGrid ? _snap(frac * total) / total : frac;

  // ── Element editing ───────────────────────────────────────────────────────

  void _updateElement(LayoutElement updated) {
    setState(() {
      final idx = _elements.indexWhere((e) => e.id == updated.id);
      if (idx >= 0) _elements[idx] = updated;
    });
  }

  void _commitUpdate() => _pushHistory();

  void _deleteSelected() {
    if (_selectedId == null) return;
    setState(() {
      _elements.removeWhere((e) => e.id == _selectedId);
      _selectedId = null;
    });
    _pushHistory();
  }

  void _addElement(String type) {
    final id = '${type}_${DateTime.now().millisecondsSinceEpoch}';

    double w, h;
    String? label, action;
    String? stick, trigger;
    switch (type) {
      case 'joystick':
        w = h = 100;
        stick = 'left';
        break;
      case 'dpad':
        w = h = 120;
        break;
      case 'face_buttons':
        w = h = 120;
        break;
      case 'trigger':
        w = 70;
        h = 36;
        label = 'L2';
        trigger = 'LT';
        break;
      case 'macro':
        w = 80;
        h = 50;
        label = 'MACRO';
        break;
      default: // button
        w = 70;
        h = 40;
        label = 'BTN';
        action = 'button_a';
    }

    final el = LayoutElement(
      id: id,
      type: type,
      x: 0.40,
      y: 0.40,
      width: w,
      height: h,
      label: label,
      action: action,
      stick: stick,
      trigger: trigger,
    );

    setState(() {
      _elements.add(el);
      _selectedId = id;
    });
    _pushHistory();
  }

  // ── Refit all elements into view ────────────────────────────────────────

  /// Clamps every element so its right and bottom edges lie within [0, 1].
  /// Uses the canvas size (screen minus AppBar) passed from build().
  void _refitAll(Size screen) {
    setState(() {
      _elements = _elements.map((el) {
        final w = el.width * el.scale;
        final h = el.height * el.scale;
        // Maximum safe top-left so the element stays inside the canvas
        final maxX = (1.0 - w / screen.width).clamp(0.0, 1.0);
        final maxY = (1.0 - h / screen.height).clamp(0.0, 1.0);
        final nx = el.x.clamp(0.0, maxX);
        final ny = el.y.clamp(0.0, maxY);
        if (nx == el.x && ny == el.y) return el;
        return el.copyWith(x: nx, y: ny);
      }).toList();
    });
    _pushHistory();
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    final size = MediaQuery.of(context).size;

    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1F2937),
        foregroundColor: Colors.white,
        title: GestureDetector(
          onTap: _renameLayout,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Flexible(
                child: Text(
                  _layout.name,
                  style: const TextStyle(
                    fontWeight: FontWeight.bold,
                    fontSize: 15,
                  ),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              const Icon(Icons.edit, size: 14, color: Colors.white38),
            ],
          ),
        ),
        actions: [
          IconButton(
            tooltip: 'Undo',
            icon: const Icon(Icons.undo),
            onPressed: _historyIndex > 0 ? _undo : null,
          ),
          IconButton(
            tooltip: 'Redo',
            icon: const Icon(Icons.redo),
            onPressed: _historyIndex < _history.length - 1 ? _redo : null,
          ),
          IconButton(
            tooltip: _snapToGrid ? 'Grid Snap ON' : 'Grid Snap OFF',
            icon: Icon(
              _snapToGrid ? Icons.grid_on : Icons.grid_off,
              color: _snapToGrid ? Colors.tealAccent : Colors.white54,
            ),
            onPressed: () => setState(() => _snapToGrid = !_snapToGrid),
          ),
          IconButton(
            tooltip: 'Inspector',
            icon: Icon(
              Icons.tune,
              color: _showInspector ? Colors.blueAccent : Colors.white54,
            ),
            onPressed: () => setState(() => _showInspector = !_showInspector),
          ),
          IconButton(
            tooltip: 'Refit all — bring every element back into view',
            icon: const Icon(
              Icons.filter_center_focus,
              color: Colors.amberAccent,
            ),
            onPressed: () => _refitAll(size),
          ),
          TextButton(
            onPressed: _saveAndPop,
            child: const Text(
              'SAVE',
              style: TextStyle(
                color: Colors.blueAccent,
                fontWeight: FontWeight.bold,
              ),
            ),
          ),
        ],
      ),
      body: Row(
        children: [
          // ── Canvas ──────────────────────────────────────────────────────
          Expanded(
            child: GestureDetector(
              onTap: () => setState(() => _selectedId = null),
              child: Stack(
                children: [
                  // Grid background
                  if (_snapToGrid) _buildGrid(size),

                  // Elements
                  ..._elements.map((el) => _buildDraggableElement(el, size)),

                  // Resize handles for selected
                  if (_selected != null)
                    ..._buildResizeHandles(_selected!, size),

                  // Add button strip at bottom
                  _buildAddStrip(),
                ],
              ),
            ),
          ),

          // ── Inspector ────────────────────────────────────────────────────
          if (_showInspector && _selected != null) _buildInspector(_selected!),
        ],
      ),
    );
  }

  // ── Grid ─────────────────────────────────────────────────────────────────

  Widget _buildGrid(Size size) {
    return CustomPaint(size: size, painter: _GridPainter(_gridSize));
  }

  // ── Element tile ──────────────────────────────────────────────────────────

  Widget _buildDraggableElement(LayoutElement el, Size screen) {
    final left = el.x * screen.width;
    final top = el.y * screen.height;
    final w = el.width * el.scale;
    final h = el.height * el.scale;
    final isSelected = el.id == _selectedId;

    return Positioned(
      left: left,
      top: top,
      width: w,
      height: h,
      child: GestureDetector(
        onTap: () => setState(() => _selectedId = el.id),
        onPanStart: (d) {
          setState(() {
            _selectedId = el.id;
            _dragging = true;
            _dragStart = d.globalPosition;
            _elStartX = el.x;
            _elStartY = el.y;
          });
        },
        onPanUpdate: (d) {
          if (!_dragging || _dragStart == null) return;
          final dx = (d.globalPosition.dx - _dragStart!.dx) / screen.width;
          final dy = (d.globalPosition.dy - _dragStart!.dy) / screen.height;
          final nx = (_elStartX! + dx).clamp(0.0, 1.0);
          final ny = (_elStartY! + dy).clamp(0.0, 1.0);
          _updateElement(
            el.copyWith(
              x: _snapFrac(nx, screen.width),
              y: _snapFrac(ny, screen.height),
            ),
          );
        },
        onPanEnd: (_) {
          setState(() => _dragging = false);
          _commitUpdate();
        },
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 60),
          decoration: BoxDecoration(
            color: Color(el.colorValue).withAlpha(isSelected ? 220 : 160),
            borderRadius: _typeRadius(el.type),
            border: Border.all(
              color: isSelected
                  ? Colors.blueAccent
                  : Color(el.colorValue).withAlpha(200),
              width: isSelected ? 2 : 1,
            ),
          ),
          child: Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                Icon(
                  _typeIcon(el.type),
                  color: Colors.white70,
                  size: min(w, h) * 0.35,
                ),
                if (el.label != null)
                  Text(
                    el.label!,
                    style: const TextStyle(
                      color: Colors.white,
                      fontSize: 10,
                      fontWeight: FontWeight.bold,
                    ),
                    overflow: TextOverflow.ellipsis,
                    maxLines: 1,
                  ),
              ],
            ),
          ),
        ),
      ),
    );
  }

  BorderRadius _typeRadius(String type) {
    if (type == 'joystick' || type == 'face_buttons') {
      return BorderRadius.circular(999);
    }
    return BorderRadius.circular(8);
  }

  IconData _typeIcon(String type) {
    switch (type) {
      case 'joystick':
        return Icons.radio_button_unchecked;
      case 'dpad':
        return Icons.gamepad;
      case 'face_buttons':
        return Icons.circle_outlined;
      case 'trigger':
        return Icons.compress;
      case 'macro':
        return Icons.auto_fix_high;
      default:
        return Icons.crop_square;
    }
  }

  // ── Resize handles ────────────────────────────────────────────────────────

  List<Widget> _buildResizeHandles(LayoutElement el, Size screen) {
    final left = el.x * screen.width;
    final top = el.y * screen.height;
    final w = el.width * el.scale;
    final h = el.height * el.scale;
    const hs = 14.0; // handle visual size

    final handles = [
      (_ResizeHandle.topLeft, left, top),
      (_ResizeHandle.topRight, left + w, top),
      (_ResizeHandle.bottomLeft, left, top + h),
      (_ResizeHandle.bottomRight, left + w, top + h),
      (_ResizeHandle.topCenter, left + w / 2, top),
      (_ResizeHandle.bottomCenter, left + w / 2, top + h),
      (_ResizeHandle.leftCenter, left, top + h / 2),
      (_ResizeHandle.rightCenter, left + w, top + h / 2),
    ];

    return handles.map((hd) {
      final (handle, hx, hy) = hd;
      return Positioned(
        left: hx - hs / 2,
        top: hy - hs / 2,
        child: GestureDetector(
          onPanStart: (d) {
            _activeHandle = handle;
            _resizeStart = d.globalPosition;
            _resizeStartW = el.width;
            _resizeStartH = el.height;
            _resizeStartX = el.x;
            _resizeStartY = el.y;
          },
          onPanUpdate: (d) {
            if (_activeHandle == null) return;
            final dx = d.globalPosition.dx - _resizeStart!.dx;
            final dy = d.globalPosition.dy - _resizeStart!.dy;
            _applyResize(el, handle, dx, dy, screen);
          },
          onPanEnd: (_) {
            _activeHandle = null;
            _commitUpdate();
          },
          child: Container(
            width: hs,
            height: hs,
            decoration: BoxDecoration(
              color: Colors.blueAccent,
              border: Border.all(color: Colors.white, width: 1.5),
              borderRadius: BorderRadius.circular(3),
            ),
          ),
        ),
      );
    }).toList();
  }

  void _applyResize(
    LayoutElement el,
    _ResizeHandle h,
    double dx,
    double dy,
    Size screen,
  ) {
    double newW = _resizeStartW!;
    double newH = _resizeStartH!;
    double newX = _resizeStartX!;
    double newY = _resizeStartY!;
    const minSize = 30.0;

    switch (h) {
      case _ResizeHandle.rightCenter:
      case _ResizeHandle.topRight:
      case _ResizeHandle.bottomRight:
        newW = max(minSize, _resizeStartW! + dx);
        break;
      case _ResizeHandle.leftCenter:
      case _ResizeHandle.topLeft:
      case _ResizeHandle.bottomLeft:
        newW = max(minSize, _resizeStartW! - dx);
        newX = _resizeStartX! + dx / screen.width;
        break;
      default:
        break;
    }
    switch (h) {
      case _ResizeHandle.bottomCenter:
      case _ResizeHandle.bottomLeft:
      case _ResizeHandle.bottomRight:
        newH = max(minSize, _resizeStartH! + dy);
        break;
      case _ResizeHandle.topCenter:
      case _ResizeHandle.topLeft:
      case _ResizeHandle.topRight:
        newH = max(minSize, _resizeStartH! - dy);
        newY = _resizeStartY! + dy / screen.height;
        break;
      default:
        break;
    }

    _updateElement(
      el.copyWith(
        x: newX.clamp(0.0, 1.0),
        y: newY.clamp(0.0, 1.0),
        width: _snap(newW),
        height: _snap(newH),
      ),
    );
  }

  // ── Add strip ─────────────────────────────────────────────────────────────

  Widget _buildAddStrip() {
    final items = [
      ('Button', 'button', Icons.crop_square),
      ('Joystick', 'joystick', Icons.radio_button_unchecked),
      ('D-Pad', 'dpad', Icons.gamepad),
      ('Trigger', 'trigger', Icons.compress),
      ('Face', 'face_buttons', Icons.circle_outlined),
      ('Macro', 'macro', Icons.auto_fix_high),
    ];
    return Positioned(
      bottom: 0,
      left: 0,
      right: 0,
      child: Container(
        color: const Color(0xFF1F2937).withAlpha(230),
        padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.spaceEvenly,
          children: items.map((item) {
            final (label, type, icon) = item;
            return GestureDetector(
              onTap: () => _addElement(type),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Container(
                    width: 44,
                    height: 44,
                    decoration: BoxDecoration(
                      color: const Color(0xFF374151),
                      borderRadius: BorderRadius.circular(10),
                      border: Border.all(color: Colors.white24),
                    ),
                    child: Icon(icon, color: Colors.white70, size: 22),
                  ),
                  const SizedBox(height: 3),
                  Text(
                    label,
                    style: const TextStyle(color: Colors.white54, fontSize: 10),
                  ),
                ],
              ),
            );
          }).toList(),
        ),
      ),
    );
  }

  // ── Inspector ─────────────────────────────────────────────────────────────

  Widget _buildInspector(LayoutElement el) {
    return Container(
      width: 220,
      color: const Color(0xFF1F2937),
      child: ListView(
        padding: const EdgeInsets.fromLTRB(12, 12, 12, 80),
        children: [
          // Header
          Row(
            children: [
              Expanded(
                child: Text(
                  el.type.toUpperCase(),
                  style: const TextStyle(
                    color: Colors.white70,
                    fontSize: 11,
                    letterSpacing: 1.2,
                  ),
                ),
              ),
              IconButton(
                icon: const Icon(
                  Icons.delete_outline,
                  color: Colors.redAccent,
                  size: 20,
                ),
                tooltip: 'Delete element',
                onPressed: _deleteSelected,
              ),
            ],
          ),
          const Divider(color: Colors.white12),

          // Label
          if (el.type != 'joystick' && el.type != 'face_buttons') ...[
            _inspLabel('Label'),
            TextField(
              controller: TextEditingController(text: el.label ?? ''),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: _inputDec('e.g. JUMP'),
              onChanged: (v) => _updateElement(el.copyWith(label: v)),
              onEditingComplete: _commitUpdate,
            ),
            const SizedBox(height: 12),
          ],

          // Action (for buttons)
          if (el.type == 'button' || el.type == 'trigger') ...[
            _inspLabel('Action'),
            TextField(
              controller: TextEditingController(
                text: el.action ?? el.trigger ?? '',
              ),
              style: const TextStyle(color: Colors.white, fontSize: 13),
              decoration: _inputDec('e.g. keyboard_space'),
              onChanged: (v) => el.type == 'trigger'
                  ? _updateElement(el.copyWith(trigger: v))
                  : _updateElement(el.copyWith(action: v)),
              onEditingComplete: _commitUpdate,
            ),
            const SizedBox(height: 12),
          ],

          // Macro editor button
          if (el.type == 'macro') ...[
            ElevatedButton.icon(
              icon: const Icon(Icons.edit_note, size: 16),
              label: Text(
                el.macro.isEmpty
                    ? 'Define Macro'
                    : 'Edit Macro (${el.macro.length} steps)',
              ),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF9333EA),
              ),
              onPressed: () => _openMacroEditor(el),
            ),
            const SizedBox(height: 12),
          ],

          // Width
          _inspLabel('Width  ${el.width.round()}px'),
          Slider(
            value: el.width.clamp(30, 300),
            min: 30,
            max: 300,
            divisions: 54,
            activeColor: Colors.blueAccent,
            onChanged: (v) =>
                _updateElement(el.copyWith(width: v.roundToDouble())),
            onChangeEnd: (_) => _commitUpdate(),
          ),

          // Height
          _inspLabel('Height  ${el.height.round()}px'),
          Slider(
            value: el.height.clamp(30, 300),
            min: 30,
            max: 300,
            divisions: 54,
            activeColor: Colors.blueAccent,
            onChanged: (v) =>
                _updateElement(el.copyWith(height: v.roundToDouble())),
            onChangeEnd: (_) => _commitUpdate(),
          ),

          // Scale
          _inspLabel('Scale  ${el.scale.toStringAsFixed(2)}×'),
          Slider(
            value: el.scale.clamp(0.5, 3.0),
            min: 0.5,
            max: 3.0,
            divisions: 50,
            activeColor: Colors.tealAccent,
            onChanged: (v) => _updateElement(
              el.copyWith(scale: double.parse(v.toStringAsFixed(2))),
            ),
            onChangeEnd: (_) => _commitUpdate(),
          ),

          const SizedBox(height: 8),
          _inspLabel('Colour'),
          const SizedBox(height: 6),
          Wrap(
            spacing: 6,
            runSpacing: 6,
            children: _swatches.map((c) {
              final isActive = el.colorValue == c;
              return GestureDetector(
                onTap: () {
                  _updateElement(el.copyWith(colorValue: c));
                  _commitUpdate();
                },
                child: Container(
                  width: 28,
                  height: 28,
                  decoration: BoxDecoration(
                    color: Color(c),
                    borderRadius: BorderRadius.circular(6),
                    border: Border.all(
                      color: isActive ? Colors.white : Colors.white24,
                      width: isActive ? 2.5 : 1,
                    ),
                  ),
                  child: isActive
                      ? const Icon(Icons.check, color: Colors.white, size: 14)
                      : null,
                ),
              );
            }).toList(),
          ),
        ],
      ),
    );
  }

  Widget _inspLabel(String text) => Padding(
    padding: const EdgeInsets.only(bottom: 2),
    child: Text(
      text,
      style: const TextStyle(color: Colors.white54, fontSize: 11),
    ),
  );

  InputDecoration _inputDec(String hint) => InputDecoration(
    hintText: hint,
    hintStyle: const TextStyle(color: Colors.white24),
    isDense: true,
    enabledBorder: const UnderlineInputBorder(
      borderSide: BorderSide(color: Colors.white24),
    ),
    focusedBorder: const UnderlineInputBorder(
      borderSide: BorderSide(color: Colors.blueAccent),
    ),
  );

  // ── Macro editor ──────────────────────────────────────────────────────────

  Future<void> _openMacroEditor(LayoutElement el) async {
    final steps = await showDialog<List<MacroStep>>(
      context: context,
      builder: (_) => MacroEditorDialog(
        initialSteps: el.macro,
        elementLabel: el.label ?? 'Button',
      ),
    );
    if (steps != null) {
      _updateElement(el.copyWith(macro: steps));
      _commitUpdate();
    }
  }

  // ── Rename ────────────────────────────────────────────────────────────────

  Future<void> _renameLayout() async {
    final ctrl = TextEditingController(text: _layout.name);
    final newName = await showDialog<String>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF1F2937),
        title: const Text(
          'Rename Layout',
          style: TextStyle(color: Colors.white, fontSize: 15),
        ),
        content: TextField(
          controller: ctrl,
          autofocus: true,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            hintText: 'Layout name',
            hintStyle: TextStyle(color: Colors.white38),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: Colors.white24),
            ),
            focusedBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: Colors.blueAccent),
            ),
          ),
          onSubmitted: (v) => Navigator.pop(context, v.trim()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context),
            child: const Text(
              'Cancel',
              style: TextStyle(color: Colors.white54),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(context, ctrl.text.trim()),
            child: const Text(
              'Rename',
              style: TextStyle(color: Colors.blueAccent),
            ),
          ),
        ],
      ),
    );
    if (newName != null && newName.isNotEmpty && mounted) {
      setState(() => _layout = _layout.copyWith(name: newName));
    }
  }

  // ── Save ─────────────────────────────────────────────────────────────────

  void _saveAndPop() {
    final saved = _layout.copyWith(elements: _elements);
    Navigator.pop(context, saved);
  }
}

// ── Grid painter ──────────────────────────────────────────────────────────────

class _GridPainter extends CustomPainter {
  final double gridSize;
  _GridPainter(this.gridSize);

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = Colors.white.withAlpha(15)
      ..strokeWidth = 0.5;
    for (double x = 0; x <= size.width; x += gridSize) {
      canvas.drawLine(Offset(x, 0), Offset(x, size.height), paint);
    }
    for (double y = 0; y <= size.height; y += gridSize) {
      canvas.drawLine(Offset(0, y), Offset(size.width, y), paint);
    }
  }

  @override
  bool shouldRepaint(_GridPainter old) => old.gridSize != gridSize;
}

// ── Resize handle enum ────────────────────────────────────────────────────────

enum _ResizeHandle {
  topLeft,
  topCenter,
  topRight,
  leftCenter,
  rightCenter,
  bottomLeft,
  bottomCenter,
  bottomRight,
}
