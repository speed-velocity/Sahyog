/// HrSample — one heart-rate reading sample.
///
/// An immutable model representing a single heart-rate measurement in beats
/// per minute (BPM). The timestamp [ts] must be UTC; callers must ensure
/// timezone-aware [DateTime] values are provided.
///
/// Invariants:
///   - [hr] is a valid integer BPM value (20-250 per demo bounds).
///   - [ts] is timezone-aware (UTC).
///
class HrSample {
  /// The UTC timestamp of this reading.
  final DateTime ts;

  /// The heart rate in beats per minute.
  final int hr;

  /// {required DateTime ts, required int hr}
  HrSample({
    required this.ts,
    required this.hr,
  }) {
    // Validate BPM range per demo thresholds.
    if (hr < 20 || hr > 250) {
      throw ArgumentError.value(
        hr,
        'hr',
        'Heart rate must be within demo valid range (20-250 BPM).',
      );
    }
  }

  /// Return a copy with a potentially different timestamp or heart rate.
  HrSample copyWith({DateTime? ts, int? hr}) {
    return HrSample(
      ts: ts ?? this.ts,
      hr: hr ?? this.hr,
    );
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is HrSample && other.ts == ts && other.hr == hr;
  }

  @override
  int get hashCode => Object.hash(ts, hr);

  @override
  String toString() => 'HrSample(ts: $ts, hr: $hr)';
}