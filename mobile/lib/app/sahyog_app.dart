import 'package:flutter/material.dart';
import '../features/monitoring/presentation/monitoring_screen.dart';
import '../features/monitoring/presentation/preview_session_controller.dart';
import '../features/verification/presentation/verification_screen.dart';
import '../features/incident/presentation/incident_screen.dart';

class SahyogApp extends StatefulWidget {
  const SahyogApp({super.key});

  @override
  State<SahyogApp> createState() => _SahyogAppState();
}

class _SahyogAppState extends State<SahyogApp> {
  int _currentIndex = 0;
  late final PreviewSessionController _previewController;
  bool _verificationAcknowledged = false;

  @override
  void initState() {
    super.initState();
    _previewController = PreviewSessionController(
      duration: const Duration(seconds: 60),
    );
  }

  @override
  void dispose() {
    _previewController.dispose();
    super.dispose();
  }

  void _onAcknowledgeVerification() {
    setState(() {
      _verificationAcknowledged = true;
    });
  }

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SAHYOG',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF006688),
          brightness: Brightness.light,
        ),
      ),
      home: Scaffold(
        appBar: AppBar(
          title: const Text('SAHYOG'),
          elevation: 1,
        ),
        body: switch (_currentIndex) {
          0 => MonitoringScreen(controller: _previewController),
          1 => VerificationScreen(
              acknowledged: _verificationAcknowledged,
              onAcknowledge: _onAcknowledgeVerification,
            ),
          _ => const IncidentScreen(),
        },
        bottomNavigationBar: NavigationBar(
          selectedIndex: _currentIndex,
          onDestinationSelected: (index) {
            setState(() {
              _currentIndex = index;
            });
          },
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.monitor_heart_outlined),
              selectedIcon: Icon(Icons.monitor_heart),
              label: 'Monitor',
            ),
            NavigationDestination(
              icon: Icon(Icons.verified_outlined),
              selectedIcon: Icon(Icons.verified),
              label: 'Verify',
            ),
            NavigationDestination(
              icon: Icon(Icons.warning_amber_outlined),
              selectedIcon: Icon(Icons.warning_amber),
              label: 'Incident',
            ),
          ],
        ),
      ),
    );
  }
}
