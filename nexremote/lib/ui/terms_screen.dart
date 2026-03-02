import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:shared_preferences/shared_preferences.dart';

/// First-launch Terms & Privacy gate.
///
/// Shows a tabbed view with Terms of Service and Privacy Policy.
/// The user must tick the checkbox and press Accept to continue.
/// Returns `true` if accepted, `false` if declined.
class TermsScreen extends StatefulWidget {
  const TermsScreen({super.key});

  /// Check whether terms have already been accepted.
  static Future<bool> hasAccepted() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool('terms_accepted') ?? false;
  }

  /// Record acceptance.
  static Future<void> recordAcceptance() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool('terms_accepted', true);
    await prefs.setString(
      'terms_accepted_at',
      DateTime.now().toIso8601String(),
    );
  }

  @override
  State<TermsScreen> createState() => _TermsScreenState();
}

class _TermsScreenState extends State<TermsScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabCtrl;
  bool _agreed = false;
  String _terms = 'Loading...';
  String _privacy = 'Loading...';

  @override
  void initState() {
    super.initState();
    _tabCtrl = TabController(length: 2, vsync: this);
    _loadDocs();
  }

  Future<void> _loadDocs() async {
    final terms = await rootBundle.loadString('assets/legal/TERMS.md');
    final privacy = await rootBundle.loadString('assets/legal/PRIVACY.md');
    if (mounted) {
      setState(() {
        _terms = terms;
        _privacy = privacy;
      });
    }
  }

  @override
  void dispose() {
    _tabCtrl.dispose();
    super.dispose();
  }

  void _accept() async {
    await TermsScreen.recordAcceptance();
    if (mounted) Navigator.of(context).pop(true);
  }

  void _decline() {
    Navigator.of(context).pop(false);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF111827),
      appBar: AppBar(
        backgroundColor: const Color(0xFF1F2937),
        automaticallyImplyLeading: false,
        title: const Text(
          'Welcome to NexRemote',
          style: TextStyle(
            fontWeight: FontWeight.bold,
            fontSize: 18,
            color: Colors.white,
          ),
        ),
        centerTitle: true,
        bottom: TabBar(
          controller: _tabCtrl,
          indicatorColor: Colors.blueAccent,
          labelColor: Colors.blueAccent,
          unselectedLabelColor: Colors.white54,
          tabs: const [
            Tab(text: 'Terms of Service'),
            Tab(text: 'Privacy Policy'),
          ],
        ),
      ),
      body: Column(
        children: [
          Expanded(
            child: TabBarView(
              controller: _tabCtrl,
              children: [_docView(_terms), _docView(_privacy)],
            ),
          ),
          // Checkbox + buttons
          Container(
            color: const Color(0xFF1F2937),
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
            child: SafeArea(
              top: false,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Row(
                    children: [
                      Checkbox(
                        value: _agreed,
                        activeColor: Colors.blueAccent,
                        onChanged: (v) => setState(() => _agreed = v ?? false),
                      ),
                      const Expanded(
                        child: Text(
                          'I have read and agree to the Terms of Service and Privacy Policy',
                          style: TextStyle(color: Colors.white70, fontSize: 13),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.end,
                    children: [
                      TextButton(
                        onPressed: _decline,
                        child: const Text(
                          'Decline & Exit',
                          style: TextStyle(color: Colors.redAccent),
                        ),
                      ),
                      const SizedBox(width: 12),
                      ElevatedButton(
                        onPressed: _agreed ? _accept : null,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.blueAccent,
                          foregroundColor: Colors.white,
                          disabledBackgroundColor: Colors.blueAccent.withAlpha(
                            80,
                          ),
                        ),
                        child: const Text('I Accept'),
                      ),
                    ],
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _docView(String markdown) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(16),
      child: Text(
        markdown,
        style: const TextStyle(
          color: Colors.white70,
          fontSize: 13,
          height: 1.5,
        ),
      ),
    );
  }
}
