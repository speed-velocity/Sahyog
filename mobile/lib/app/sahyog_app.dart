import 'package:flutter/material.dart';

import '../core/api/api_client.dart';
import '../core/api/api_config.dart';
import '../core/api/api_exception.dart';
import '../core/api/api_session.dart';
import '../core/api/repositories/authentication_repository.dart';
import '../core/api/repositories/authorization_repository.dart';
import '../core/api/repositories/dashboard_repository.dart';
import '../core/api/repositories/demo_repository.dart';
import '../core/api/repositories/hospital_repository.dart';
import '../core/api/repositories/incident_repository.dart';
import '../core/api/repositories/location_repository.dart';
import '../core/api/repositories/reading_repository.dart';
import '../core/api/repositories/verification_repository.dart';
import '../features/auth/presentation/auth_screen.dart';
import '../features/incident/presentation/incident_screen.dart';
import '../features/location/presentation/location_screen.dart';
import '../features/monitoring/presentation/dashboard_overview_controller.dart';
import '../features/monitoring/presentation/dashboard_overview_panel.dart';
import '../features/monitoring/presentation/monitoring_screen.dart';
import '../features/monitoring/presentation/preview_session_controller.dart';
import '../features/verification/presentation/verification_screen.dart';

class SahyogApp extends StatefulWidget {
  const SahyogApp({
    super.key,
    this.apiSession,
    this.dashboardRepository,
    this.authenticationRepository,
    this.demoRepository,
    this.readingRepository,
    this.incidentRepository,
    this.verificationRepository,
    this.hospitalRepository,
    this.locationRepository,
    this.authorizationRepository,
  });

  /// Optional seams for the host's in-memory authentication setup and tests.
  final ApiSession? apiSession;
  final DashboardRepository? dashboardRepository;
  final AuthenticationRepository? authenticationRepository;
  final DemoRepository? demoRepository;
  final ReadingRepository? readingRepository;
  final IncidentRepository? incidentRepository;
  final VerificationRepository? verificationRepository;
  final HospitalRepository? hospitalRepository;
  final LocationRepository? locationRepository;
  final AuthorizationRepository? authorizationRepository;

  @override
  State<SahyogApp> createState() => _SahyogAppState();
}

class _SahyogAppState extends State<SahyogApp> {
  int _currentIndex = 0;
  late final PreviewSessionController _previewController;
  late final ApiSession _apiSession;
  late final DashboardOverviewController _dashboardController;

  ApiClient? _ownedApiClient;
  AuthenticationRepository? _authRepository;
  DemoRepository? _demoRepository;
  ReadingRepository? _readingRepository;
  IncidentRepository? _incidentRepository;
  VerificationRepository? _verificationRepository;
  HospitalRepository? _hospitalRepository;
  LocationRepository? _locationRepository;
  AuthorizationRepository? _authorizationRepository;
  AuthorizationRepository? get authorizationRepository =>
      _authorizationRepository;

  bool _verificationAcknowledged = false;

  @override
  void initState() {
    super.initState();
    _apiSession =
        widget.apiSession ??
        widget.dashboardRepository?.session ??
        ApiSession();

    var dashboardRepository = widget.dashboardRepository;
    String? configurationError;

    if (dashboardRepository == null) {
      try {
        _ownedApiClient = ApiClient(config: ApiConfig.fromEnvironment());
        dashboardRepository = DashboardRepository(
          client: _ownedApiClient!,
          session: _apiSession,
        );
        _authRepository =
            widget.authenticationRepository ??
            AuthenticationRepository(
              client: _ownedApiClient!,
              session: _apiSession,
            );
        _demoRepository =
            widget.demoRepository ??
            DemoRepository(client: _ownedApiClient!, session: _apiSession);
        _readingRepository =
            widget.readingRepository ??
            ReadingRepository(client: _ownedApiClient!, session: _apiSession);
        _incidentRepository =
            widget.incidentRepository ??
            IncidentRepository(client: _ownedApiClient!, session: _apiSession);
        _verificationRepository =
            widget.verificationRepository ??
            VerificationRepository(
              client: _ownedApiClient!,
              session: _apiSession,
            );
        _hospitalRepository =
            widget.hospitalRepository ??
            HospitalRepository(client: _ownedApiClient!);
        _locationRepository =
            widget.locationRepository ??
            LocationRepository(client: _ownedApiClient!, session: _apiSession);
        _authorizationRepository =
            widget.authorizationRepository ??
            AuthorizationRepository(
              client: _ownedApiClient!,
              session: _apiSession,
            );
      } on ApiException catch (error) {
        configurationError = error.message;
      }
    } else {
      _authRepository = widget.authenticationRepository;
      _demoRepository = widget.demoRepository;
      _readingRepository = widget.readingRepository;
      _incidentRepository = widget.incidentRepository;
      _verificationRepository = widget.verificationRepository;
      _hospitalRepository = widget.hospitalRepository;
      _locationRepository = widget.locationRepository;
      _authorizationRepository = widget.authorizationRepository;
    }

    _previewController = PreviewSessionController(
      duration: const Duration(seconds: 60),
      demoRepository: _demoRepository,
      readingRepository: _readingRepository,
      session: _apiSession,
    );

    _dashboardController = DashboardOverviewController(
      session: _apiSession,
      repository: dashboardRepository,
      configurationError: configurationError,
    )..load();
  }

  @override
  void dispose() {
    _previewController.dispose();
    _dashboardController.dispose();
    _ownedApiClient?.close();
    super.dispose();
  }

  void _onAcknowledgeVerification() {
    setState(() {
      _verificationAcknowledged = true;
    });
  }

  void _openDashboardOverview(BuildContext context) {
    showModalBottomSheet<void>(
      context: context,
      isScrollControlled: true,
      builder: (context) => SafeArea(
        child: FractionallySizedBox(
          heightFactor: 0.8,
          child: SingleChildScrollView(
            padding: const EdgeInsets.symmetric(vertical: 16),
            child: DashboardOverviewPanel(controller: _dashboardController),
          ),
        ),
      ),
    );
  }

  void _openAuthScreen(BuildContext context) {
    if (_authRepository == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'API configuration unavailable. Provide SAHYOG_API_BASE_URL to authenticate.',
          ),
        ),
      );
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => AuthScreen(
          authRepository: _authRepository!,
          session: _apiSession,
          onAuthenticated: () {
            setState(() {});
            _dashboardController.load();
          },
        ),
      ),
    );
  }

  void _openLocationScreen(BuildContext context) {
    final client = _ownedApiClient ?? widget.dashboardRepository?.client;

    final hospitalRepo =
        _hospitalRepository ??
        (client != null ? HospitalRepository(client: client) : null);

    if (hospitalRepo == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text(
            'API configuration unavailable. Provide SAHYOG_API_BASE_URL to view hospitals.',
          ),
        ),
      );
      return;
    }

    Navigator.of(context).push(
      MaterialPageRoute<void>(
        builder: (context) => LocationHospitalsScreen(
          hospitalRepository: hospitalRepo,
          locationRepository: _locationRepository,
        ),
      ),
    );
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
          actions: [
            IconButton(
              tooltip: 'Location & Hospitals',
              onPressed: () => _openLocationScreen(context),
              icon: const Icon(Icons.local_hospital_outlined),
            ),
            IconButton(
              tooltip: 'Account session',
              onPressed: () => _openAuthScreen(context),
              icon: Icon(
                _apiSession.isAuthenticated
                    ? Icons.account_circle
                    : Icons.account_circle_outlined,
                color: _apiSession.isAuthenticated ? Colors.green : null,
              ),
            ),
            Builder(
              builder: (context) => IconButton(
                tooltip: 'Backend dashboard',
                onPressed: () => _openDashboardOverview(context),
                icon: const Icon(Icons.dashboard_outlined),
              ),
            ),
          ],
        ),
        body: switch (_currentIndex) {
          0 => MonitoringScreen(controller: _previewController),
          1 => VerificationScreen(
            acknowledged: _verificationAcknowledged,
            onAcknowledge: _onAcknowledgeVerification,
            verificationRepository: _verificationRepository,
            activeIncidentId: _previewController.activeIncidentId,
          ),
          _ => IncidentScreen(
            incidentRepository: _incidentRepository,
            activeIncidentId: _previewController.activeIncidentId,
          ),
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
