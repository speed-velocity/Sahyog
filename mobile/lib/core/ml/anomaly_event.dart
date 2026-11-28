/// AnomalyEvent — backend-confirmed anomaly information model.
///
/// This model represents anomaly data as returned by the backend. It is NOT a
/// locally generated event; it is constructed from the backend's response to
/// `POST /api/v1/readings` or retrieved from the incident service.
///
/// The backend is the sole authority for anomaly events. Flutter must NOT
/// create AnomalyEvent instances through local threshold detection. Any
/// AnomalyEvent present in the UI should originate from the backend response.
///
/// Invariants:
///   - All timestamps are UTC.
///   - [kind] is either "spike" or "drop", as mapped by the backend.
///   - This model does not contain database IDs, subject IDs, demo run IDs,
///     incident IDs, or detector versions — those are backend-owned fields.
library;
class AnomalyEvent {
  /// The UTC timestamp when the anomaly event was detected/emitted by the
  /// backend detector.
  final DateTime detectedAt;

  /// The internal kind of anomaly event, as determined by the backend
  /// threshold comparison.
  ///
  /// Mapped by the backend to `detector_result` values `HR_SPIKE`/`HR_DROP`.
  /// Flutter should not interpret this as a local classification; it is purely
  /// informational display data.
  final String kind;

  /// The heart rate of the sample that completed the anomaly persistence
  /// (the last abnormal sample in the event window).
  final int lastHr;

  /// The UTC timestamp of the first abnormal sample in the event window.
  final DateTime firstAbnormalAt;

  /// How long the abnormal pattern persisted, in milliseconds.
  final int durationMs;

  /// Create an [AnomalyEvent] from backend data.
  ///
  /// The [detectedAt] is the overall detection timestamp. The
  /// [firstAbnormalAt] is when the sustained abnormal pattern began. The
  /// [durationMs] is how long the pattern persisted. The [lastHr] is the BPM
  /// of the completing sample. The [kind] is "spike" or "drop" as determined
  /// by the backend.
  AnomalyEvent({
    required this.detectedAt,
    required this.kind,
    required this.lastHr,
    required this.firstAbnormalAt,
    required this.durationMs,
  }) : assert(kind == 'spike' || kind == 'drop',
            'kind must be "spike" or "drop"');

  /// Parse an [AnomalyEvent] from the backend's JSON response.
  ///
  /// The [json] map should contain the keys described in
  /// `detector_integration_contract.md` §8.2 Proposed backend mapping. If any
  /// required field is missing, the factory returns `null`.
  /// Parse an [AnomalyEvent] from a JSON map. Returns `null` if required fields are missing.
  static AnomalyEvent? fromJson(Map<String, dynamic> json) {
    final detectedAt =
        json['detected_at'] != null
            ? DateTime.parse(json['detected_at'] as String)
            : null;
    final firstAbnormalAt =
        json['first_abnormal_at'] != null
            ? DateTime.parse(json['first_abnormal_at'] as String)
            : null;
    final kind = json['kind'] as String?;
    final lastHr = json['last_hr'] as int?;
    final durationMs = json['duration_ms'] as int?;

    if (detectedAt == null ||
        firstAbnormalAt == null ||
        kind == null ||
        kind != 'spike' && kind != 'drop' ||
        lastHr == null ||
        durationMs == null) {
      return null;
    }

    return AnomalyEvent(
      detectedAt: detectedAt,
      kind: kind,
      lastHr: lastHr,
      firstAbnormalAt: firstAbnormalAt,
      durationMs: durationMs,
    );
  }

  /// Convert this model to a JSON map.
  Map<String, dynamic> toJson() {
    return {
      'detected_at': detectedAt.toIso8601String(),
      'first_abnormal_at': firstAbnormalAt.toIso8601String(),
      'kind': kind,
      'last_hr': lastHr,
      'duration_ms': durationMs,
    };
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is AnomalyEvent &&
        other.detectedAt == detectedAt &&
        other.kind == kind &&
        other.lastHr == lastHr &&
        other.firstAbnormalAt == firstAbnormalAt &&
        other.durationMs == durationMs;
  }

  @override
  int get hashCode => Object.hash(
        detectedAt,
        kind,
        lastHr,
        firstAbnormalAt,
        durationMs,
      );

  @override
  String toString() =>
      'AnomalyEvent(detectedAt: $detectedAt, kind: $kind, lastHr: $lastHr)';
}