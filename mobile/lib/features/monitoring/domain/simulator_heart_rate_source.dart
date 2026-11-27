/// SimulatorHeartRateSource — deterministic simulated heart-rate source.

/// Generates reproducible reading sequences per [SimScenario]. The simulator
/// does not perform anomaly detection; it merely produces deterministic
/// [HrSample] sequences that the Flutter app submits to the backend via
/// `POST /api/v1/readings`. Anomaly detection is exclusively the backend's
/// responsibility per SYSTEM_DESIGN.md D3.

import 'dart:async';

import '../domain/hr_sample.dart';
import '../domain/sim_scenario.dart';

/// {Duration sampleInterval = const Duration(seconds: 3)}
class SimulatorHeartRateSource {
  /// The generated sample sequence for the current scenario.
  /// Populated on [generateSamples] and replayed on each [start].
  List<HrSample> _samples = [];

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
  late final _Controller _controller;

  /// Create a [SimulatorHeartRateSource].
  ///
  /// The scenario must be set via [setScenario] before calling [start].
  /// [sampleInterval] defaults to 3 seconds if not provided.
  SimulatorHeartRateSource({Duration sampleInterval = const Duration(seconds: 3)})
      : sampleInterval = sampleInterval {
    _controller = _Controller(this);
  }

  /// Stream of [HrSample] readings emitted by this simulator.
  ///
  /// Emits one sample immediately after [start], then at intervals of
  /// [sampleInterval]. The stream is a broadcast stream; it may be listened
  /// to by multiple subscribers. Emits [null] when the scenario sequence is
  /// complete (but the stream stays open; call [start] again for a fresh
  /// sequence).
  Stream<HrSample> get samples => _controller.stream;

  /// Internal helper class to manage the stream controller.
  _Controller _Controller(SimulatorHeartRateSource source) {
    final controller = StreamController<HrSample>.broadcast(
      onListen: () {
        // Listen for pause/resume if needed; for now just let it run.
      },
      onResume: () {
        // Resume emitting after pause if needed.
      },
    );
    return _ControllerInternal(controller, source);
  }

  _ControllerInternal({
    required StreamController<HrSample> controller,
    required SimulatorHeartRateSource source,
  })  : _controller = controller,
        _samples = <HrSample>[],
        _index = 0 {
    // Bind lifecycle methods.
    _controller.stream.listen((_) {
      // No-op: the stream is driven by start()/next reading logic.
    });
  }

  _ControllerInternal._internal();

  /// The current [SimScenario], if set. Returns `null` if no scenario has
  /// been set yet via [setScenario].
  SimScenario? get scenario => _scenario;

  /// Whether the simulator is currently running.
  bool get isRunning => _isRunning;

  /// The generated sample sequence for the current scenario (populated on
  /// [generateSamples]). Read-only after generation.
  List<HrSample> get samplesList => List.unmodifiable(_samples);

  /// Index into [_samples] for the next emission.
  int get _currentIndex => _index;

  /// Generate the deterministic sample sequence for the current scenario.
  ///
  /// This method does NOT submit readings to the backend; it merely produces
  /// the [HrSample] values. The Flutter app is responsible for submitting
  /// each sample via `POST /api/v1/readings`.
  List<HrSample> generateSamples() {
    final scenario = _scenario;
    final now = DateTime.now().utc;

    _samples.clear();
    _index = 0;

    if (scenario == null) {
      // No scenario set; generate normal sequence as default.
      // This should not happen in normal usage - setScenario should be called first.
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
    // ~30 normal readings for a ~60 second demo.
    const int count = 30;

    for (int i = 0; i < count; i++) {
      // Deterministic oscillation around 72 BPM: 71, 72, 73, 72, 71, ...
      final hr = 72 + (i % 3 - 1); // oscillates 71, 72, 73
      final ts = baseTime.add(Duration(milliseconds: i * sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: hr));
    }
    return samples;
  }

  /// Generate the anomalous reading pattern.
  ///
  /// Pattern (per backend validated fixture):
  /// - Start with normal readings (first 5 samples at 72 BPM).
  /// - Then 5 abnormal samples at offsets 0, 3, 6, 9, 12 seconds,
  ///   alternating spike (88 BPM) and normal, or sustained spike.
  /// - The previously validated anomaly fixture used five abnormal readings
  ///   at 0, 3, 6, 9 and 12 seconds. This satisfies the backend's persistence
  ///   duration check (>= 10 seconds with 5+ consecutive abnormal samples).
  ///
  /// For TRUE_ANOMALY and FALSE_ALARM, the readings are identical. The
  /// distinction is the verification outcome.
  List<HrSample> _generateAnomaly(DateTime baseTime, {required bool isSpike}) {
    final samples = <HrSample>[];
    // Total ~40 readings: start normal, then sustained abnormal pattern.

    // Phase 1: baseline normal readings (first ~5 samples, ~15 seconds).
    const int baselineCount = 5;
    for (int i = 0; i < baselineCount; i++) {
      final hr = 72;
      final ts = baseTime.add(Duration(milliseconds: i * sampleInterval.inMilliseconds));
      samples.add(HrSample(ts: ts, hr: hr));
    }

    // Phase 2: sustained abnormal readings.
    // The backend detector requires min_consecutive_abnormal_samples=5 and
    // persistence_ms=10000. With samples every 3 seconds, 5 samples at
    // 0, 3, 6, 9, 12 seconds gives a duration of 12 seconds between first and last,
    // satisfying the 10-second persistence requirement.

    // Determine the abnormal BPM value.
    final abnormalBpm = isSpike ? 88 : 57; // spike or drop per thresholds.md

    // 5 abnormal samples at 0, 3, 6, 9, 12 seconds.
    for (int i = 0; i < 5; i++) {
      final ts = baseTime.add(Duration(seconds: i * 3)); // 0, 3, 6, 9, 12 seconds
      samples.add(HrSample(ts: ts, hr: abnormalBpm));
    }

    // After the abnormal period, return to normal for the remainder of the demo.
    // Fill up to ~40 total readings.
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
  /// - Emits the first sample immediately on the next stream event.
  /// - The simulator is now running; no duplicate timer is created on repeated start if already running
  ///   (handled by the StateError check).
  Future<void> start() async {
    if (_isRunning) {
      throw StateError('A scenario is already running on this simulator instance.');
    }

    _isRunning = true;
    _sampleCount = 0;

    // Generate the sample sequence for the current scenario.
    final newSamples = generateSamples();
    _samples.clear();
    _samples.addAll(newSamples);
    _index = 0;

    // Emit the first sample immediately by adding to the controller.
    // This ensures the first reading is available immediately after start().
    if (_samples.isNotEmpty && _index < _samples.length) {
      _controller.add(_samples[_index]);
      _index++;
    }
  }

  /// Stop the simulator.
  ///
  /// - Cancels any pending emissions.
  /// - Does NOT call any backend reset endpoint; the backend owns incident lifecycle.
  Future<void> stop() async {
    if (!_isRunning) {
      // No-op if not running.
      return;
    }

    _isRunning = false;
    _samples.clear();
    _index = 0;
    // Do NOT clear _scenario here; preserve the scenario so restart works with same scenario.
    // _scenario is left intact so restarting the same instance works correctly.
  }

  /// Set a new scenario.
  ///
  /// May only be called when the simulator is not running. Throws [StateError]
  /// if called while running. After calling this, call [start()] to generate
  /// the sample sequence for the new scenario.
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
  HrSample? _nextSample() {
    if (!_isRunning || _index >= _samples.length) {
      return null;
    }
    final sample = _samples[_index];
    _index++;
    return sample;
  }

  /// Internal method to forward the next sample to the stream controller.
  void _forwardNext() {
    final sample = _nextSample();
    if (sample != null) {
      _controller.add(sample);
    }
    // If null, the stream emission is exhausted; the stream stays open
    // but emits no further values until start() is called again.
  }
}