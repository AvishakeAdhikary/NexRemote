import 'package:flutter/material.dart';
import '../layouts/layout_manager.dart';

/// Dialog for creating or editing a macro sequence on a button element.
class MacroEditorDialog extends StatefulWidget {
  /// The initial list of steps to edit. Pass [] for a new macro.
  final List<MacroStep> initialSteps;
  final String elementLabel;

  const MacroEditorDialog({
    super.key,
    required this.initialSteps,
    required this.elementLabel,
  });

  @override
  State<MacroEditorDialog> createState() => _MacroEditorDialogState();
}

class _MacroEditorDialogState extends State<MacroEditorDialog> {
  late List<MacroStep> _steps;
  bool _recording = false;
  DateTime? _lastTap;

  // All available actions the user can add
  static const _actionGroups = {
    'Face Buttons': ['button:A', 'button:B', 'button:X', 'button:Y'],
    'Shoulder': ['button:L1', 'button:R1', 'button:L2', 'button:R2'],
    'System': ['button:START', 'button:SELECT'],
    'D-Pad': ['dpad:UP', 'dpad:DOWN', 'dpad:LEFT', 'dpad:RIGHT'],
    'Keyboard': [
      'keyboard:space',
      'keyboard:r',
      'keyboard:e',
      'keyboard:ctrl',
      'keyboard:shift',
      'keyboard:tab',
      'keyboard:f',
    ],
    'Mouse': ['mouse:left', 'mouse:right', 'mouse:middle'],
  };

  @override
  void initState() {
    super.initState();
    _steps = List.from(widget.initialSteps);
  }

  String _prettyAction(String action) {
    final parts = action.split(':');
    if (parts.length < 2) return action;
    return '${parts[0].toUpperCase()}  ${parts[1].toUpperCase()}';
  }

  void _addStep(String action) {
    final now = DateTime.now();
    final delay = _recording && _lastTap != null
        ? now.difference(_lastTap!).inMilliseconds.clamp(0, 5000)
        : 0;
    _lastTap = now;
    setState(() => _steps.add(MacroStep(action: action, delayMs: delay)));
  }

  void _editDelay(int index) async {
    final ctrl = TextEditingController(text: _steps[index].delayMs.toString());
    final result = await showDialog<int>(
      context: context,
      builder: (_) => AlertDialog(
        backgroundColor: const Color(0xFF1F2937),
        title: const Text(
          'Delay before step (ms)',
          style: TextStyle(color: Colors.white),
        ),
        content: TextField(
          controller: ctrl,
          keyboardType: TextInputType.number,
          style: const TextStyle(color: Colors.white),
          decoration: const InputDecoration(
            hintText: 'e.g. 150',
            hintStyle: TextStyle(color: Colors.white38),
            enabledBorder: UnderlineInputBorder(
              borderSide: BorderSide(color: Colors.white24),
            ),
          ),
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
            onPressed: () => Navigator.pop(context, int.tryParse(ctrl.text)),
            child: const Text('OK', style: TextStyle(color: Colors.blueAccent)),
          ),
        ],
      ),
    );
    if (result != null && mounted) {
      setState(
        () => _steps[index] = MacroStep(
          action: _steps[index].action,
          delayMs: result,
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    return Dialog(
      backgroundColor: const Color(0xFF111827),
      insetPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 24),
      child: Column(
        children: [
          // ── Header ──────────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.fromLTRB(16, 14, 8, 14),
            color: const Color(0xFF1F2937),
            child: Row(
              children: [
                const Icon(
                  Icons.auto_fix_high,
                  color: Color(0xFF9333EA),
                  size: 20,
                ),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Macro — ${widget.elementLabel}',
                    style: const TextStyle(
                      color: Colors.white,
                      fontWeight: FontWeight.bold,
                      fontSize: 16,
                    ),
                  ),
                ),
                // Record toggle
                TextButton.icon(
                  icon: Icon(
                    _recording ? Icons.stop : Icons.fiber_manual_record,
                    color: _recording ? Colors.redAccent : Colors.white54,
                    size: 18,
                  ),
                  label: Text(
                    _recording ? 'Recording…' : 'Record',
                    style: TextStyle(
                      color: _recording ? Colors.redAccent : Colors.white54,
                    ),
                  ),
                  onPressed: () => setState(() {
                    _recording = !_recording;
                    if (_recording) _lastTap = null;
                  }),
                ),
              ],
            ),
          ),

          // ── Step list ────────────────────────────────────────────────────
          Expanded(
            child: _steps.isEmpty
                ? const Center(
                    child: Text(
                      'No steps yet.\nTap an action below to add one.',
                      textAlign: TextAlign.center,
                      style: TextStyle(color: Colors.white38),
                    ),
                  )
                : ReorderableListView.builder(
                    itemCount: _steps.length,
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    onReorder: (old, neo) {
                      setState(() {
                        final s = _steps.removeAt(old);
                        _steps.insert(neo > old ? neo - 1 : neo, s);
                      });
                    },
                    itemBuilder: (_, i) {
                      final step = _steps[i];
                      return ListTile(
                        key: ValueKey('$i:${step.action}'),
                        contentPadding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 2,
                        ),
                        leading: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 8,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: const Color(0xFF374151),
                            borderRadius: BorderRadius.circular(6),
                          ),
                          child: Text(
                            '${i + 1}',
                            style: const TextStyle(
                              color: Colors.white70,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                        title: Text(
                          _prettyAction(step.action),
                          style: const TextStyle(
                            color: Colors.white,
                            fontSize: 13,
                          ),
                        ),
                        subtitle: step.delayMs > 0
                            ? Text(
                                '+${step.delayMs} ms',
                                style: const TextStyle(
                                  color: Colors.white38,
                                  fontSize: 11,
                                ),
                              )
                            : null,
                        trailing: Row(
                          mainAxisSize: MainAxisSize.min,
                          children: [
                            IconButton(
                              icon: const Icon(
                                Icons.timer,
                                color: Colors.white38,
                                size: 18,
                              ),
                              tooltip: 'Edit delay',
                              onPressed: () => _editDelay(i),
                            ),
                            IconButton(
                              icon: const Icon(
                                Icons.close,
                                color: Colors.redAccent,
                                size: 18,
                              ),
                              onPressed: () =>
                                  setState(() => _steps.removeAt(i)),
                            ),
                          ],
                        ),
                      );
                    },
                  ),
          ),

          // ── Action palette ───────────────────────────────────────────────
          Container(
            constraints: const BoxConstraints(maxHeight: 180),
            decoration: const BoxDecoration(
              color: Color(0xFF1F2937),
              border: Border(top: BorderSide(color: Colors.white12)),
            ),
            child: SingleChildScrollView(
              padding: const EdgeInsets.all(10),
              child: Wrap(
                spacing: 6,
                runSpacing: 6,
                children: _actionGroups.entries
                    .expand(
                      (group) => group.value.map((action) {
                        return GestureDetector(
                          onTap: () => _addStep(action),
                          child: Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 10,
                              vertical: 6,
                            ),
                            decoration: BoxDecoration(
                              color: const Color(0xFF374151),
                              borderRadius: BorderRadius.circular(8),
                              border: Border.all(color: Colors.white12),
                            ),
                            child: Text(
                              _prettyAction(action),
                              style: const TextStyle(
                                color: Colors.white70,
                                fontSize: 11,
                              ),
                            ),
                          ),
                        );
                      }),
                    )
                    .toList(),
              ),
            ),
          ),

          // ── Buttons ──────────────────────────────────────────────────────
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 10),
            color: const Color(0xFF1F2937),
            child: Row(
              children: [
                OutlinedButton(
                  onPressed: () => Navigator.pop(context),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.white54,
                  ),
                  child: const Text('Cancel'),
                ),
                const SizedBox(width: 10),
                OutlinedButton(
                  onPressed: () => setState(() {
                    _steps.clear();
                    _lastTap = null;
                  }),
                  style: OutlinedButton.styleFrom(
                    foregroundColor: Colors.redAccent,
                  ),
                  child: const Text('Clear'),
                ),
                const Spacer(),
                ElevatedButton.icon(
                  icon: const Icon(Icons.check),
                  label: const Text('Save'),
                  style: ElevatedButton.styleFrom(
                    backgroundColor: const Color(0xFF9333EA),
                  ),
                  onPressed: () => Navigator.pop(context, _steps),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
