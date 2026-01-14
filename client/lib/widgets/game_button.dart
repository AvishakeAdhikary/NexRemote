import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class GameButton extends StatefulWidget {
  final String label;
  final VoidCallback onPressed;
  final VoidCallback onReleased;
  final Color color;
  final double size;
  const GameButton({
    Key? key,
    required this.label,
    required this.onPressed,
    required this.onReleased,
    this.color = Colors.blue,
    this.size = 70,
  }) : super(key: key);
  @override
  State<GameButton> createState() => _GameButtonState();
}

class _GameButtonState extends State<GameButton> {
  bool _pressed = false;
  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTapDown: (_) {
        HapticFeedback.lightImpact();
        setState(() => _pressed = true);
        widget.onPressed();
      },
      onTapUp: (_) {
        setState(() => _pressed = false);
        widget.onReleased();
      },
      onTapCancel: () {
        setState(() => _pressed = false);
        widget.onReleased();
      },
      child: Container(
        width: widget.size,
        height: widget.size,
        decoration: BoxDecoration(
          shape: BoxShape.circle,
          color: _pressed ? widget.color : widget.color.withOpacity(0.7),
          boxShadow: [
            BoxShadow(
              color: widget.color.withOpacity(0.5),
              blurRadius: _pressed ? 10 : 15,
              spreadRadius: _pressed ? 2 : 5,
            ),
          ],
        ),
        child: Center(
          child: Text(
            widget.label,
            style: const TextStyle(
              color: Colors.white,
              fontWeight: FontWeight.bold,
              fontSize: 18,
            ),
          ),
        ),
      ),
    );
  }
}
