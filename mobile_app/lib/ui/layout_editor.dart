import 'package:flutter/material.dart';
import '../layouts/layout_manager.dart';
import '../utils/logger.dart';

class LayoutEditor extends StatefulWidget {
  final GamepadLayout? initialLayout;
  
  const LayoutEditor({
    Key? key,
    this.initialLayout,
  }) : super(key: key);
  
  @override
  State<LayoutEditor> createState() => _LayoutEditorState();
}

class _LayoutEditorState extends State<LayoutEditor> {
  late TextEditingController _nameController;
  late GamepadLayout _layout;
  LayoutElement? _selectedElement;
  
  @override
  void initState() {
    super.initState();
    
    // Initialize layout
    if (widget.initialLayout != null) {
      _layout = widget.initialLayout!;
    } else {
      _layout = GamepadLayout(
        id: 'custom_${DateTime.now().millisecondsSinceEpoch}',
        name: 'New Layout',
        version: '1.0',
        orientation: 'landscape',
        elements: [],
      );
    }
    
    _nameController = TextEditingController(text: _layout.name);
  }
  
  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Layout Editor'),
        actions: [
          IconButton(
            icon: const Icon(Icons.save),
            onPressed: _saveLayout,
          ),
        ],
      ),
      body: Column(
        children: [
          // Layout info
          Padding(
            padding: const EdgeInsets.all(16),
            child: TextField(
              controller: _nameController,
              decoration: const InputDecoration(
                labelText: 'Layout Name',
                border: OutlineInputBorder(),
              ),
            ),
          ),
          
          // Canvas
          Expanded(
            child: Container(
              color: Colors.grey[900],
              child: Stack(
                children: _layout.elements.map((element) {
                  return _buildDraggableElement(element);
                }).toList(),
              ),
            ),
          ),
          
          // Toolbar
          Container(
            height: 80,
            color: Colors.grey[850],
            child: ListView(
              scrollDirection: Axis.horizontal,
              padding: const EdgeInsets.all(8),
              children: [
                _buildToolbarButton('Button', Icons.radio_button_unchecked, () {
                  _addElement('button');
                }),
                _buildToolbarButton('Joystick', Icons.gamepad, () {
                  _addElement('joystick');
                }),
                _buildToolbarButton('D-Pad', Icons.control_camera, () {
                  _addElement('dpad');
                }),
                _buildToolbarButton('Face Buttons', Icons.games, () {
                  _addElement('face_buttons');
                }),
              ],
            ),
          ),
        ],
      ),
      floatingActionButton: _selectedElement != null
          ? FloatingActionButton(
              onPressed: _deleteSelectedElement,
              backgroundColor: Colors.red,
              child: const Icon(Icons.delete),
            )
          : null,
    );
  }
  
  Widget _buildDraggableElement(LayoutElement element) {
    final size = MediaQuery.of(context).size;
    final isSelected = _selectedElement?.id == element.id;
    
    return Positioned(
      left: element.position['x']! * size.width,
      top: element.position['y']! * size.height,
      child: Draggable(
        feedback: _buildElementWidget(element, isSelected: true),
        childWhenDragging: Container(),
        onDragEnd: (details) {
          setState(() {
            // Update element position
            final newX = details.offset.dx / size.width;
            final newY = details.offset.dy / size.height;
            
            element.position['x'] = newX.clamp(0.0, 1.0);
            element.position['y'] = newY.clamp(0.0, 1.0);
          });
        },
        child: GestureDetector(
          onTap: () {
            setState(() {
              _selectedElement = element;
            });
          },
          child: _buildElementWidget(element, isSelected: isSelected),
        ),
      ),
    );
  }
  
  Widget _buildElementWidget(LayoutElement element, {bool isSelected = false}) {
    double width = 60;
    double height = 60;
    
    if (element.size is Map) {
      width = (element.size['width'] ?? 60).toDouble();
      height = (element.size['height'] ?? 60).toDouble();
    } else if (element.size is int) {
      width = height = (element.size as int).toDouble();
    }
    
    return Container(
      width: width,
      height: height,
      decoration: BoxDecoration(
        color: isSelected ? Colors.blue.withOpacity(0.5) : Colors.grey[800],
        borderRadius: element.type == 'joystick' ? null : BorderRadius.circular(8),
        shape: element.type == 'joystick' ? BoxShape.circle : BoxShape.rectangle,
        border: Border.all(
          color: isSelected ? Colors.yellow : Colors.blue,
          width: 2,
        ),
      ),
      child: Center(
        child: Text(
          element.label ?? element.type,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 12,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
  
  Widget _buildToolbarButton(String label, IconData icon, VoidCallback onPressed) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4),
      child: ElevatedButton(
        onPressed: onPressed,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon),
            const SizedBox(height: 4),
            Text(label, style: const TextStyle(fontSize: 10)),
          ],
        ),
      ),
    );
  }
  
  void _addElement(String type) {
    setState(() {
      final newElement = LayoutElement(
        id: '${type}_${DateTime.now().millisecondsSinceEpoch}',
        type: type,
        position: {'x': 0.5, 'y': 0.5},
        size: type == 'joystick' ? 100 : {'width': 60.0, 'height': 60.0},
        label: type.toUpperCase(),
      );
      
      _layout.elements.add(newElement);
    });
  }
  
  void _deleteSelectedElement() {
    if (_selectedElement != null) {
      setState(() {
        _layout.elements.removeWhere((e) => e.id == _selectedElement!.id);
        _selectedElement = null;
      });
    }
  }
  
  void _saveLayout() {
    final layoutManager = LayoutManager();
    
    // Update layout name
    _layout = GamepadLayout(
      id: _layout.id,
      name: _nameController.text,
      version: _layout.version,
      orientation: _layout.orientation,
      elements: _layout.elements,
    );
    
    layoutManager.saveLayout(_layout);
    
    Logger.info('Layout saved: ${_layout.name}');
    Navigator.pop(context, _layout);
  }
  
  @override
  void dispose() {
    _nameController.dispose();
    super.dispose();
  }
}