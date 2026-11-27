import 'dart:async';

import 'package:flutter/foundation.dart';

import '../../../core/api/api_session.dart';
import '../../../core/api/models/demo_models.dart';
import '../../../core/api/models/reading_models.dart';
import '../../../core/api/repositories/demo_repository.dart';
import '../../../core/api/repositories/reading_repository.dart';

enum DemoScenario {
  normal('Normal', 'NORMAL'),
  trueAnomaly('True anomaly', 'TRUE_ANOMALY'),
  falseAlarm('False alarm', 'FALSE_ALARM');

  const DemoScenario(this.title, this.wireLabel);

  final String title;
  final String wireLabel;
}

class PreviewSessionController extends ChangeNotifier {
  PreviewSessionController({
    Duration duration = const Duration(seconds: 60),
    this.demoRepository,
    this.readingRepository,
    this.session,
  }) : _duration = duration,
       _remainingSeconds = duration.inSeconds;

  final Duration _duration;
  final DemoRepository? demoRepository;
  final ReadingRepository? readingRepository;
  final ApiSession? session;

  Timer? _timer;

  bool _isRunning = false;
  bool _isEnded = false;
  DemoScenario? _scenario;
  int _remainingSeconds;

  int? _currentBpm;
  String? _latestTimestampLabel;
  bool _hasAnomalyAlert = false;
  String? _anomalyAlertMessage;
  String? _activeDemoRunId;
  String? _activeIncidentId;
  String? _backendDetectionStatus;

  Duration get duration => _duration;
  bool get isRunning => _isRunning;
  bool get isEnded => _isEnded;
  DemoScenario? get scenario => _scenario;
  int get remainingSeconds => _remainingSeconds;
  int? get currentBpm => _currentBpm;
  String? get latestTimestampLabel => _latestTimestampLabel;
  bool get hasAnomalyAlert => _hasAnomalyAlert;
  String? get anomalyAlertMessage => _anomalyAlertMessage;
  String? get activeDemoRunId => _activeDemoRunId;
  String? get activeIncidentId => _activeIncidentId;
  String? get backendDetectionStatus => _backendDetectionStatus;

  int get elapsedPercentage {
    if (_duration.inSeconds == 0) return 100;
    final elapsed = _duration.inSeconds - _remainingSeconds;
    return ((elapsed / _duration.inSeconds) * 100).clamp(0, 100).toInt();
  }

  bool start(DemoScenario scenario) {
    if (_isRunning) {
      return false;
    }
    _scenario = scenario;
    _isRunning = true;
    _isEnded = false;
    _remainingSeconds = _duration.inSeconds;
    _hasAnomalyAlert = false;
    _anomalyAlertMessage = null;
    _currentBpm = 72;
    _latestTimestampLabel =
        '${DateTime.now().toUtc().toIso8601String().substring(0, 19).replaceAll('T', ' ')} UTC';

    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), _tick);

    // If connected to backend with valid session, initiate demo run
    _initiateBackendDemoRun(scenario);

    notifyListeners();
    return true;
  }

  Future<void> _initiateBackendDemoRun(DemoScenario scenario) async {
    if (demoRepository == null ||
        session == null ||
        !session!.isAuthenticated) {
      return;
    }
    try {
      final key =
          'demo_${scenario.wireLabel}_${DateTime.now().millisecondsSinceEpoch}';
      final run = await demoRepository!.start(
        DemoRunCreateRequest(
          scenario: scenario.wireLabel,
          startIdempotencyKey: key,
        ),
      );
      _activeDemoRunId = run.demoRunId;
      notifyListeners();
    } catch (_) {
      // Backend may be offline or unreachable; preview continues locally
    }
  }

  void _tick(Timer timer) {
    if (_remainingSeconds > 1) {
      _remainingSeconds--;

      // Calculate deterministic simulated heart rate based on scenario
      final elapsed = _duration.inSeconds - _remainingSeconds;
      _calculateSimulatedReading(elapsed);

      // Submit reading to backend if demo run is active
      if (_remainingSeconds % 3 == 0) {
        _submitReadingToBackend();
      }

      notifyListeners();
    } else {
      _remainingSeconds = 0;
      _isRunning = false;
      _isEnded = true;
      _timer?.cancel();
      _timer = null;
      notifyListeners();
    }
  }

  void _calculateSimulatedReading(int elapsed) {
    final now = DateTime.now().toUtc();
    _latestTimestampLabel =
        '${now.toIso8601String().substring(0, 19).replaceAll('T', ' ')} UTC';

    if (_scenario == DemoScenario.normal) {
      // Normal: stable 71-74 BPM
      _currentBpm = 72 + (elapsed % 3 == 0 ? 1 : (elapsed % 2 == 0 ? -1 : 0));
      _hasAnomalyAlert = false;
    } else {
      // TRUE_ANOMALY or FALSE_ALARM:
      // 0-15s: normal baseline (72 BPM)
      // 16-35s: sustained spike (142-148 BPM)
      // >35s: recovery / return to baseline
      if (elapsed >= 15 && elapsed <= 35) {
        _currentBpm = 145 + (elapsed % 4);
        _hasAnomalyAlert = true;
        _anomalyAlertMessage =
            'Spike Detected: Heart rate reached $_currentBpm BPM (exceeds threshold 120 BPM). Verification pending.';
      } else {
        _currentBpm = 72 + (elapsed % 2 == 0 ? 1 : 0);
      }
    }
  }

  Future<void> _submitReadingToBackend() async {
    final runId = _activeDemoRunId;
    if (runId == null ||
        readingRepository == null ||
        session == null ||
        !session!.isAuthenticated) {
      return;
    }
    try {
      final key =
          'read_${runId}_${_remainingSeconds}_${DateTime.now().millisecondsSinceEpoch}';
      final response = await readingRepository!.submit(
        ReadingSubmissionRequest(
          demoRunId: runId,
          heartRateBpm: _currentBpm ?? 72,
          observedAt: DateTime.now().toUtc(),
          ingestionIdempotencyKey: key,
        ),
      );
      _backendDetectionStatus = response.detectionStatus;
      if (response.incidentId != null) {
        _activeIncidentId = response.incidentId;
      }
      if (response.detectionStatus != 'NORMAL') {
        _hasAnomalyAlert = true;
        _anomalyAlertMessage =
            'Backend Anomaly Detected: status ${response.detectionStatus}.';
      }
      notifyListeners();
    } catch (_) {
      // Non-blocking in demo mode
    }
  }

  void replay() {
    if (_scenario != null) {
      final current = _scenario!;
      reset();
      start(current);
    }
  }

  void reset() {
    _timer?.cancel();
    _timer = null;
    _isRunning = false;
    _isEnded = false;
    _scenario = null;
    _currentBpm = null;
    _hasAnomalyAlert = false;
    _anomalyAlertMessage = null;
    _activeDemoRunId = null;
    _activeIncidentId = null;
    _backendDetectionStatus = null;
    _remainingSeconds = _duration.inSeconds;
    notifyListeners();
  }

  @override
  void dispose() {
    _timer?.cancel();
    _timer = null;
    super.dispose();
  }
}
