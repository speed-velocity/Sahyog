/// HeartRateSource — abstraction for the source of heart-rate readings.
///
/// Implementations provide a [Stream<HrSample>] of simulated or device
/// readings. This interface defines the contract; concrete implementations
/// (such as [SimulatorHeartRateSource]) provide the generated sequences.
library;

import 'hr_sample.dart';

abstract class HeartRateSource {
  /// Stream of [HrSample] readings from this source.
  ///
  /// Implementations must emit samples in chronological order with UTC
  /// timestamps. The stream may be broadcast or single-subscription depending
  /// on the implementation.
  Stream<HrSample> get samples;

  /// Start generating and emitting readings.
  Future<void> start();

  /// Stop further emissions and clean up resources.
  Future<void> stop();
}