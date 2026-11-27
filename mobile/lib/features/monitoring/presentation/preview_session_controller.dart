import 'dart:async';
import 'package:flutter/foundation.dart';

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
  })  : _duration = duration,
        _remainingSeconds = duration.inSeconds;

  final Duration _duration;
  Timer? _timer;

  bool _isRunning = false;
  bool _isEnded = false;
  DemoScenario? _scenario;
  int _remainingSeconds;

  Duration get duration => _duration;
  bool get isRunning => _isRunning;
  bool get isEnded => _isEnded;
  DemoScenario? get scenario => _scenario;
  int get remainingSeconds => _remainingSeconds;

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
    _timer?.cancel();
    _timer = Timer.periodic(const Duration(seconds: 1), _tick);
    notifyListeners();
    return true;
  }

  void _tick(Timer timer) {
    if (_remainingSeconds > 1) {
      _remainingSeconds--;
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
