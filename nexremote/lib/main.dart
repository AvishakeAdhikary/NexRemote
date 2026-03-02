import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'ui/home_screen.dart';
import 'ui/terms_screen.dart';
import 'utils/logger.dart';

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Set preferred orientations
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.landscapeLeft,
    DeviceOrientation.landscapeRight,
  ]);

  // Initialize logger
  Logger.init();

  runApp(const NexRemoteApp());
}

class NexRemoteApp extends StatelessWidget {
  const NexRemoteApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'NexRemote',
      theme: ThemeData(
        primarySwatch: Colors.blue,
        useMaterial3: true,
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF1A1A1A),
        cardTheme: CardThemeData(
          elevation: 4,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          elevation: 0,
          centerTitle: true,
          backgroundColor: Color(0xFF2A2A2A),
        ),
      ),
      home: const _GateScreen(),
      debugShowCheckedModeBanner: false,
    );
  }
}

/// Shows the Terms screen on first launch, then HomeScreen.
class _GateScreen extends StatefulWidget {
  const _GateScreen();

  @override
  State<_GateScreen> createState() => _GateScreenState();
}

class _GateScreenState extends State<_GateScreen> {
  bool _loading = true;
  bool _accepted = false;

  @override
  void initState() {
    super.initState();
    _checkTerms();
  }

  Future<void> _checkTerms() async {
    final accepted = await TermsScreen.hasAccepted();
    if (mounted) {
      setState(() {
        _accepted = accepted;
        _loading = false;
      });

      if (!accepted) {
        _showTerms();
      }
    }
  }

  Future<void> _showTerms() async {
    final result = await Navigator.of(context).push<bool>(
      MaterialPageRoute(
        builder: (_) => const TermsScreen(),
        fullscreenDialog: true,
      ),
    );

    if (result == true) {
      if (mounted) setState(() => _accepted = true);
    } else {
      // User declined — exit app
      SystemNavigator.pop();
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Scaffold(
        backgroundColor: Color(0xFF111827),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    if (!_accepted) {
      return const Scaffold(
        backgroundColor: Color(0xFF111827),
        body: Center(child: CircularProgressIndicator()),
      );
    }

    return const HomeScreen();
  }
}
