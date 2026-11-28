/// SimulatorHeartRateSource — deterministic simulated heart-rate source.
///
/// Generates reproducible reading sequences per [SimScenario]. The simulator
/// does not perform anomaly detection; it merely produces deterministic
/// [HrSample] sequences that the Flutter app submits to the backend via
/// `POST /api/v1/readings`. Anomaly detection is exclusively the backend's
/// responsibility per SYSTEM_DESIGN.md D3.
library;

import 'dart:async';

import 'heart_rate_source.dart';
import 'hr_sample.dart';
import 'sim_scenario.dart';

class SimulatorHeartRateSource implements HeartRateSource {
  /// The generated sample sequence for the current scenario.
  /// Populated on [generateSamples] and replayed on each [start].
  final List<HrSample> _samples = [];

  /// Index into [_samples] for the next emission.
  int _index = 0;

  /// The selected demo scenario. Set via [setScenario] before [start].
  SimScenario? _scenario;

  /// Approximate interval between successive readings.
  Duration sampleInterval;

  /// Whether the simulator is currently running.
  bool _isRunning = false;

  /// Controller for the samples stream. Using a broadcast controller so that
  /// multiple listeners can observe the same sequence without each getting its
  /// own copy. The controller is not closed on stop; the instance is
  /// restartable.
  final StreamController<HrSample> _controller = StreamController<HrSample>.broadcast();

  /// Create a [SimulatorHeartRateSource].
  ///
  /// The scenario must be set via [setScenario] before calling [start].
  /// [sampleInterval] defaults to 3 seconds if not provided.
  SimulatorHeartRateSource({this.sampleInterval = const Duration(seconds: 3)});

  /// Stream of [HrSample] readings emitted by this simulator.
  ///
  /// Emits one sample immediately after [start], then at intervals of
  /// [sampleInterval]. The stream is a broadcast stream; it may be listened
  /// to by multiple subscribers.
  @override
  Stream<HrSample> get samples => _controller.stream;

  /// The current [SimScenario], if set. Returns `null` if no scenario has
  /// been set yet via [setScenario].
  SimScenario? get scenario => _scenario;

  /// Whether the simulator is currently running.
  bool get isRunning => _isRunning;

  /// The generated sample sequence for the current scenario (populated on
  /// [generateSamples]). Read-only after generation.
  List<HrSample> get samplesList => List.unmodifiable(_samples);

  /// Index into [_samples] for the next emission.
  int get currentIndex => _index;

  /// Generate the deterministic sample sequence for the current scenario.
  ///
  /// This method does NOT submit readings to the backend; it merely produces
  /// the [HrSample] values. The Flutter app is responsible for submitting
  /// each sample via `POST /api/v1/readings`.
  ///
  /// An optional [baseTime] can be supplied for deterministic testing or
  /// replay; if omitted, the current UTC time is used.
  List<HrSample> generateSamples([DateTime? baseTime]) {
    final scenario = _scenario;
    final now = (baseTime ?? DateTime.now()).toUtc();

    _samples.clear();
    _index = 0;

    if (scenario == null) {
      // No scenario set; generate normal sequence as default.
      return _generateNormal(now);
    }

    // Normal scenario: stable readings around 72 BPM.
    if (scenario == SimScenario.normal) {
      return _generateNormal(now);
    }

    // TRUE_ANOMALY and FALSE_ALARM share the same abnormal pattern.
    // The difference is the subsequent verification flow, not the reading
    // sequence. Per the approved contract, both scenarios use the same
    // abnormal pattern: start normal, then sustained spike/drop.
    return _generateAnomaly(now, isSpike: true);
  }

  /// Generate normal readings around 72 BPM.
  List<HrSample> _generateNormal(DateTime baseTime) {
    final samples = <HrSample>[];
    const int count = 30;
    const offsets = [0, -1, 1];

    for (int i = 0; i < count; i++) {
      // Deterministic oscillation around 72 BPM: 72, 71, 73, 72, 71, 73, ...
      final hr = 72 + offsets[i % 3];
      final ts = baseTime.add(Duration(milliseconds: i * sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: hr));
    }
    return samples;
  }

  /// Generate the anomalous reading pattern.
  ///
  /// Pattern (per backend validated fixture):
  /// - Start with normal readings (first 5 samples at 72 BPM).
  /// - Then 5 abnormal samples at 3-second offsets.
  /// - This satisfies the backend's persistence duration check (>= 10 seconds with 5+ consecutive abnormal samples).
  /// - For TRUE_ANOMALY and FALSE_ALARM, the readings are identical.
  List<HrSample> _generateAnomaly(DateTime baseTime, {required bool isSpike}) {
    final samples = <HrSample>[];

    // Phase 1: baseline normal readings (first 5 samples, ~15 seconds).
    const int baselineCount = 5;
    for (int i = 0; i < baselineCount; i++) {
      final hr = 72;
      final ts = baseTime.add(Duration(milliseconds: i * sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: hr));
    }

    // Phase 2: sustained abnormal readings.
    final abnormalBpm = isSpike ? 88 : 57;

    for (int i = 0; i < 5; i++) {
      final ts = baseTime.add(Duration(milliseconds: (baselineCount + i) * sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: abnormalBpm));
    }

    // After the abnormal period, return to normal for the remainder of the demo.
    const int totalTarget = 40;
    while (samples.length < totalTarget) {
      final hr = 72;
      final lastTs = samples.last.ts;
      final ts = lastTs.add(Duration(milliseconds: sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: hr));
    }

    return samples;
  }

  /// Start the simulator.
  ///
  /// - Generates the sample sequence for the current scenario (set via [setScenario]).
  /// - Emits the first sample immediately.
  @override
  Future<void> start() async {
    if (_isRunning) {
      throw StateError('A scenario is already running on this simulator instance.');
    }

    _isRunning = true;

    // Generate the sample sequence for the current scenario.
    final newSamples = generateSamples();
    _samples.clear();
    _samples.addAll(newSamples);
    _index = 0;

    // Emit the first sample immediately by adding to the controller.
    if (_samples.isNotEmpty && _index < _samples.length) {
      _controller.add(_samples[_index]);
      _index++;
    }
  }

  /// Stop the simulator.
  @override
  Future<void> stop() async {
    if (!_isRunning) {
      return;
    }

    _isRunning = false;
    _samples.clear();
    _index = 0;
  }

  /// Set a new scenario.
  ///
  /// May only be called when the simulator is not running. Throws [StateError]
  /// if called while running.
  void setScenario(SimScenario newScenario) {
    if (_isRunning) {
      throw StateError(
        'Cannot change scenario while the simulator is running. Stop the '
        'simulator first, then set a new scenario.',
      );
    }
    _scenario = newScenario;
  }

  /// Advance the internal index and return the next [HrSample], or `null`
  /// if the sequence is exhausted.
  HrSample? nextSample() {
    if (!_isRunning || _index >= _samples.length) {
      return null;
    }
    final sample = _samples[_index];
    _index++;
    return sample;
  }

  /// Forward the next sample to the stream controller.
  void forwardNext() {
    final sample = nextSample();
    if (sample != null) {
      _controller.add(sample);
    }
  }
}
