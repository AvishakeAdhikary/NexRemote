import 'package:flutter/material.dart';
import 'package:nexremote/screens/home_screen.dart';
import 'package:nexremote/services/network_service.dart';
import 'package:provider/provider.dart';

void main() {
  runApp(const NexRemoteApp());
}

class NexRemoteApp extends StatelessWidget {
  const NexRemoteApp({Key? key}) : super(key: key);

  @override
  Widget build(BuildContext context) {
    return ChangeNotifierProvider(
      create: (_) => NetworkService(),
      child: MaterialApp(
        title: 'NexRemote',
        theme: ThemeData(
          primarySwatch: Colors.blue,
          brightness: Brightness.dark,
          scaffoldBackgroundColor: const Color(0xFF1E1E1E),
        ),
        home: const HomeScreen(),
        debugShowCheckedModeBanner: false,
      ),
    );
  }
}