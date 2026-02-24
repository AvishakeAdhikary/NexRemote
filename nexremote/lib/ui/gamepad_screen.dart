import 'package:flutter/material.dart';
import 'package:sensors_plus/sensors_plus.dart';
import 'dart:async';
import '../core/connection_manager.dart';
import '../input/gamepad_controller.dart' hide GamepadLayout;
import '../layouts/layout_manager.dart';
import '../layouts/layout_widget.dart';
import 'layout_editor_screen.dart';

class GamepadScreen extends StatefulWidget {
  final ConnectionManager connectionManager;

  const GamepadScreen({super.key, required this.connectionManager});

  @override
  State<GamepadScreen> createState() => _GamepadScreenState();
}

// The three built-in default layout IDs — never deletable by the user.
const _builtinIds = {'standard_gamepad', 'fps_layout', 'racing_layout'};

class _GamepadScreenState extends State<GamepadScreen> {
  late GamepadController _ctrl;
  final LayoutManager _layoutManager = LayoutManager();

  StreamSubscription? _gyroSub;
  bool _gyroEnabled = false;
  bool _hapticEnabled = true;
  bool _loading = true;

  GamepadLayout? get _activeLayout => _layoutManager.activeLayout;

  // ── Lifecycle ─────────────────────────────────────────────────────────────

  @override
  void initState() {
    super.initState();
    _ctrl = GamepadController(widget.connectionManager);
    _init();
  }

  Future<void> _init() async {
    await Future.wait([_ctrl.loadPresets(), _layoutManager.init()]);
    if (mounted) {
      setState(() {
        _loading = false;
        _gyroEnabled = _activeLayout?.gyroEnabled ?? false;
        _hapticEnabled = _activeLayout?.hapticFeedback ?? true;
        if (_gyroEnabled) _startGyro();
      });

      // Notify server of active mode
      final mode = _activeLayout?.mode ?? 'xinput';
      if (mode != 'android') {
        widget.connectionManager.sendMessage({
          'type': 'gamepad_mode',
          'mode': mode,
        });
      }
    }
  }

  @override
  void dispose() {
    _gyroSub?.cancel();
    _ctrl.dispose();
    super.dispose();
  }

  // ── Gyro ─────────────────────────────────────────────────────────────────

  void _startGyro() {
    _gyroSub = gyroscopeEventStream().listen((e) {
      _ctrl.sendGyroData(e.x, e.y, e.z);
    });
  }

  void _stopGyro() {
    _gyroSub?.cancel();
    _gyroSub = null;
  }

  // ── Haptic ───────────────────────────────────────────────────────────────

  Future<void> _setHaptic(bool value) async {
    final layout = _activeLayout;
    if (layout == null) return;
    final updated = layout.copyWith(hapticFeedback: value);
    // Persist — save to custom layouts so the setting sticks
    await _layoutManager.saveLayout(updated);
    await _layoutManager.setActiveLayout(updated);
    _ctrl.setHapticEnabled(value); // sync controller immediately
    setState(() => _hapticEnabled = value);
  }

  // ── Layout editor ─────────────────────────────────────────────────────────

  Future<void> _openEditor() async {
    final layout = _activeLayout;
    if (layout == null) return;

    final edited = await Navigator.push<GamepadLayout>(
      context,
      MaterialPageRoute(builder: (_) => LayoutEditorScreen(layout: layout)),
    );

    if (edited != null && mounted) {
      await _layoutManager.saveLayout(edited);
      await _layoutManager.setActiveLayout(edited);
      setState(() => _hapticEnabled = edited.hapticFeedback);
    }
  }

  // ── Layout selector bottom sheet ──────────────────────────────────────────

  void _openLayoutSelector() {
    showModalBottomSheet(
      context: context,
      backgroundColor: Colors.transparent,
      isScrollControlled: true,
      builder: (_) => _LayoutSelectorSheet(
        layoutManager: _layoutManager,
        onSelected: (layout) async {
          await _layoutManager.setActiveLayout(layout);
          final mode = layout.mode;
          if (mode != 'android') {
            widget.connectionManager.sendMessage({
              'type': 'gamepad_mode',
              'mode': mode,
            });
          }
          // Sync gyro
          if (layout.gyroEnabled && !_gyroEnabled) {
            _startGyro();
          } else if (!layout.gyroEnabled && _gyroEnabled) {
            _stopGyro();
          }
          setState(() {
            _gyroEnabled = layout.gyroEnabled;
            _hapticEnabled = layout.hapticFeedback;
          });
        },
        onRename: (layout, newName) async {
          final renamed = layout.copyWith(name: newName);
          await _layoutManager.saveLayout(renamed);
          // If it was the active layout, update active too
          if (_layoutManager.activeLayout?.id == layout.id) {
            await _layoutManager.setActiveLayout(renamed);
            setState(() => _hapticEnabled = renamed.hapticFeedback);
          }
          setState(() {});
        },
        onCreateNew: () async {
          Navigator.pop(context); // dismiss sheet
          final blank = GamepadLayout(
            id: 'custom_${DateTime.now().millisecondsSinceEpoch}',
            name: 'My Layout',
            elements: const [],
          );
          final edited = await Navigator.push<GamepadLayout>(
            context,
            MaterialPageRoute(
              builder: (_) => LayoutEditorScreen(layout: blank),
            ),
          );
          if (edited != null && mounted) {
            await _layoutManager.saveLayout(edited);
            await _layoutManager.setActiveLayout(edited);
            setState(() => _hapticEnabled = edited.hapticFeedback);
          }
        },
        onEdit: (layout) async {
          Navigator.pop(context);
          final edited = await Navigator.push<GamepadLayout>(
            context,
            MaterialPageRoute(
              builder: (_) => LayoutEditorScreen(layout: layout),
            ),
          );
          if (edited != null && mounted) {
            await _layoutManager.saveLayout(edited);
            await _layoutManager.setActiveLayout(edited);
            setState(() {});
          }
        },
        onDelete: (layout) async {
          await _layoutManager.deleteLayout(layout.id);
          setState(() {});
        },
        onDuplicate: (layout) async {
          final dup = layout.copyWith(
            id: '${layout.id}_copy_${DateTime.now().millisecondsSinceEpoch}',
            name: '${layout.name} (copy)',
          );
          await _layoutManager.saveLayout(dup);
          setState(() {});
        },
      ),
    );
  }

  // ── Build ─────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Color(0xFF111827),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    final layout = _activeLayout;

    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      extendBodyBehindAppBar: true,
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        foregroundColor: Colors.white,
        title: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              layout?.name ?? 'Gamepad',
              style: const TextStyle(fontWeight: FontWeight.bold, fontSize: 14),
            ),
            if (layout != null)
              Text(
                '${layout.mode.toUpperCase()}  •  ${layout.hapticFeedback ? "Haptic" : ""}',
                style: const TextStyle(fontSize: 10, color: Colors.white54),
              ),
          ],
        ),
        actions: [
          // Haptic toggle
          IconButton(
            tooltip: _hapticEnabled ? 'Haptic ON' : 'Haptic OFF',
            icon: Icon(
              _hapticEnabled ? Icons.vibration : Icons.phonelink_erase_outlined,
              color: _hapticEnabled ? Colors.orangeAccent : Colors.white38,
              size: 20,
            ),
            onPressed: () => _setHaptic(!_hapticEnabled),
          ),
          // Gyro toggle
          IconButton(
            tooltip: _gyroEnabled ? 'Gyro ON' : 'Gyro OFF',
            icon: Icon(
              _gyroEnabled
                  ? Icons.screen_rotation_alt
                  : Icons.screen_rotation_alt_outlined,
              color: _gyroEnabled ? Colors.tealAccent : Colors.white38,
              size: 20,
            ),
            onPressed: () {
              setState(() => _gyroEnabled = !_gyroEnabled);
              if (_gyroEnabled) {
                _startGyro();
              } else {
                _stopGyro();
              }
            },
          ),
          // Edit current layout
          IconButton(
            tooltip: 'Edit Layout',
            icon: const Icon(Icons.edit_outlined, size: 20),
            onPressed: _openEditor,
          ),
          // Layout selector
          IconButton(
            tooltip: 'Layouts',
            icon: const Icon(Icons.layers_outlined, size: 20),
            onPressed: _openLayoutSelector,
          ),
        ],
      ),
      body: layout == null
          ? const Center(
              child: Text(
                'No layout loaded',
                style: TextStyle(color: Colors.white54),
              ),
            )
          : SafeArea(
              child: LayoutWidget(
                layout: layout,
                gamepadController: _ctrl,
                editMode: false,
              ),
            ),
    );
  }
}

// ── Layout selector bottom sheet ──────────────────────────────────────────────

class _LayoutSelectorSheet extends StatefulWidget {
  final LayoutManager layoutManager;
  final void Function(GamepadLayout) onSelected;
  final void Function(GamepadLayout, String newName) onRename;
  final void Function() onCreateNew;
  final void Function(GamepadLayout) onEdit;
  final void Function(GamepadLayout) onDelete;
  final void Function(GamepadLayout) onDuplicate;

  const _LayoutSelectorSheet({
    required this.layoutManager,
    required this.onSelected,
    required this.onRename,
    required this.onCreateNew,
    required this.onEdit,
    required this.onDelete,
    required this.onDuplicate,
  });

  @override
  State<_LayoutSelectorSheet> createState() => _LayoutSelectorSheetState();
}

class _LayoutSelectorSheetState extends State<_LayoutSelectorSheet> {
  @override
  Widget build(BuildContext context) {
    final layouts = widget.layoutManager.getAllLayouts();
    final activeId = widget.layoutManager.activeLayout?.id;

    return DraggableScrollableSheet(
      initialChildSize: 0.55,
      minChildSize: 0.35,
      maxChildSize: 0.85,
      builder: (_, scroll) => Container(
        decoration: const BoxDecoration(
          color: Color(0xFF1F2937),
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          children: [
            // Handle
            Center(
              child: Container(
                width: 36,
                height: 4,
                margin: const EdgeInsets.only(top: 10, bottom: 12),
                decoration: BoxDecoration(
                  color: Colors.white24,
                  borderRadius: BorderRadius.circular(2),
                ),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 8, 0),
              child: Row(
                children: [
                  const Text(
                    'Layouts',
                    style: TextStyle(
                      color: Colors.white,
                      fontSize: 16,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const Spacer(),
                  TextButton.icon(
                    onPressed: () => widget.onCreateNew(),
                    icon: const Icon(
                      Icons.add,
                      size: 16,
                      color: Colors.blueAccent,
                    ),
                    label: const Text(
                      'New',
                      style: TextStyle(color: Colors.blueAccent, fontSize: 13),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 8),
            Expanded(
              child: ListView.builder(
                controller: scroll,
                padding: const EdgeInsets.fromLTRB(12, 0, 12, 20),
                itemCount: layouts.length,
                itemBuilder: (_, i) {
                  final l = layouts[i];
                  final isActive = l.id == activeId;
                  // Only the three original built-in layouts are protected
                  final isDefault = _builtinIds.contains(l.id);

                  return Container(
                    margin: const EdgeInsets.only(bottom: 8),
                    decoration: BoxDecoration(
                      color: isActive
                          ? Colors.blueAccent.withAlpha(40)
                          : const Color(0xFF374151),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isActive ? Colors.blueAccent : Colors.white12,
                      ),
                    ),
                    child: ListTile(
                      contentPadding: const EdgeInsets.symmetric(
                        horizontal: 14,
                        vertical: 4,
                      ),
                      leading: Icon(
                        isActive
                            ? Icons.radio_button_checked
                            : Icons.radio_button_unchecked,
                        color: isActive ? Colors.blueAccent : Colors.white38,
                      ),
                      title: Text(
                        l.name,
                        style: TextStyle(
                          color: isActive ? Colors.blueAccent : Colors.white,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      subtitle: Text(
                        '${l.mode.toUpperCase()}  •  ${l.elements.length} elements',
                        style: const TextStyle(
                          color: Colors.white38,
                          fontSize: 11,
                        ),
                      ),
                      trailing: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          // Rename
                          IconButton(
                            icon: const Icon(
                              Icons.drive_file_rename_outline,
                              color: Colors.white38,
                              size: 18,
                            ),
                            tooltip: 'Rename',
                            onPressed: () => _renameLayout(context, l),
                          ),
                          // Duplicate
                          IconButton(
                            icon: const Icon(
                              Icons.copy_outlined,
                              color: Colors.white38,
                              size: 18,
                            ),
                            tooltip: 'Duplicate',
                            onPressed: () {
                              widget.onDuplicate(l);
                              setState(() {});
                            },
                          ),
                          // Edit
                          IconButton(
                            icon: const Icon(
                              Icons.edit_outlined,
                              color: Colors.white54,
                              size: 18,
                            ),
                            tooltip: 'Edit layout',
                            onPressed: () => widget.onEdit(l),
                          ),
                          // Delete (custom only)
                          if (!isDefault)
                            IconButton(
                              icon: const Icon(
                                Icons.delete_outline,
                                color: Colors.redAccent,
                                size: 18,
                              ),
                              tooltip: 'Delete',
                              onPressed: () {
                                widget.onDelete(l);
                                setState(() {});
                              },
                            ),
                        ],
                      ),
                      onTap: () {
                        widget.onSelected(l);
                        Navigator.pop(context);
                      },
                    ),
                  );
                },
              ),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _renameLayout(BuildContext ctx, GamepadLayout layout) async {
    final ctrl = TextEditingController(text: layout.name);
    final newName = await showDialog<String>(
      context: ctx,
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
            hintText: 'New name',
            hintStyle: TextStyle(color: Colors.white38),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: Colors.white24),
            ),
            focusedBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: Colors.blueAccent),
            ),
          ),
          onSubmitted: (v) => Navigator.pop(ctx, v.trim()),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(ctx),
            child: const Text(
              'Cancel',
              style: TextStyle(color: Colors.white54),
            ),
          ),
          TextButton(
            onPressed: () => Navigator.pop(ctx, ctrl.text.trim()),
            child: const Text(
              'Rename',
              style: TextStyle(color: Colors.blueAccent),
            ),
          ),
        ],
      ),
    );
    if (newName != null && newName.isNotEmpty) {
      widget.onRename(layout, newName);
      setState(() {});
    }
  }
}
