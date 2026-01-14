import 'package:flutter/material.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:provider/provider.dart';

class MediaScreen extends StatelessWidget {
  const MediaScreen({Key? key}) : super(key: key);
  @override
  Widget build(BuildContext context) {
    final network = Provider.of<NetworkService>(context, listen: false);
    return Scaffold(
      appBar: AppBar(title: const Text('Media Controller')),
      body: Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            IconButton(
              icon: const Icon(Icons.skip_previous, size: 64),
              onPressed: () => network.sendCommand('media_prev'),
            ),
            const SizedBox(height: 20),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  icon: const Icon(Icons.fast_rewind, size: 48),
                  onPressed: () {},
                ),
                const SizedBox(width: 20),
                IconButton(
                  icon: const Icon(Icons.play_arrow, size: 72),
                  onPressed: () => network.sendCommand('media_play_pause'),
                ),
                const SizedBox(width: 20),
                IconButton(
                  icon: const Icon(Icons.fast_forward, size: 48),
                  onPressed: () {},
                ),
              ],
            ),
            const SizedBox(height: 20),
            IconButton(
              icon: const Icon(Icons.skip_next, size: 64),
              onPressed: () => network.sendCommand('media_next'),
            ),
            const SizedBox(height: 40),
            Row(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                IconButton(
                  icon: const Icon(Icons.volume_down, size: 48),
                  onPressed: () =>
                      network.sendCommand('media_volume', {'value': -10}),
                ),
                const Icon(Icons.volume_up, size: 32),
                IconButton(
                  icon: const Icon(Icons.volume_up, size: 48),
                  onPressed: () =>
                      network.sendCommand('media_volume', {'value': 10}),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
