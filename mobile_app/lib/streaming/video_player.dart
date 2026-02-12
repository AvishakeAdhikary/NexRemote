import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:flutter/material.dart';
import '../core/connection_manager.dart';
import '../utils/logger.dart';

class RemoteVideoPlayer extends StatefulWidget {
  final ConnectionManager connectionManager;
  
  const RemoteVideoPlayer({
    Key? key,
    required this.connectionManager,
  }) : super(key: key);
  
  @override
  State<RemoteVideoPlayer> createState() => _RemoteVideoPlayerState();
}

class _RemoteVideoPlayerState extends State<RemoteVideoPlayer> {
  Uint8List? _currentFrame;
  StreamSubscription? _messageSubscription;
  
  @override
  void initState() {
    super.initState();
    _listenForFrames();
  }
  
  void _listenForFrames() {
    _messageSubscription = widget.connectionManager.messageStream.listen((message) {
      if (message['type'] == 'screen_frame') {
        try {
          final base64Data = message['data'] as String;
          final frameData = base64Decode(base64Data);
          
          setState(() {
            _currentFrame = frameData;
          });
        } catch (e) {
          Logger.error('Error decoding frame: $e');
        }
      }
    });
  }
  
  @override
  Widget build(BuildContext context) {
    if (_currentFrame == null) {
      return Container(
        color: Colors.black,
        child: const Center(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              CircularProgressIndicator(),
              SizedBox(height: 16),
              Text(
                'Waiting for video stream...',
                style: TextStyle(color: Colors.white),
              ),
            ],
          ),
        ),
      );
    }
    
    return Container(
      color: Colors.black,
      child: Image.memory(
        _currentFrame!,
        fit: BoxFit.contain,
        gaplessPlayback: true,
      ),
    );
  }
  
  @override
  void dispose() {
    _messageSubscription?.cancel();
    super.dispose();
  }
}