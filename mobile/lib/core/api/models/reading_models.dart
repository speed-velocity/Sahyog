import 'json_helpers.dart';

const simulatedReadingSourceKind = 'SIMULATED';

class ReadingSubmissionRequest {
  ReadingSubmissionRequest({
    required this.demoRunId,
    required this.heartRateBpm,
    required this.observedAt,
    required this.ingestionIdempotencyKey,
    this.sourceKind = simulatedReadingSourceKind,
    this.activityContext,
    this.sourceRecordId,
  }) {
    if (sourceKind != simulatedReadingSourceKind) {
      throw ArgumentError.value(
        sourceKind,
        'sourceKind',
        'Only SIMULATED readings are supported.',
      );
    }
    if (ingestionIdempotencyKey.isEmpty ||
        ingestionIdempotencyKey.length > 256) {
      throw ArgumentError.value(
        ingestionIdempotencyKey,
        'ingestionIdempotencyKey',
        'Must contain 1 to 256 characters.',
      );
    }
  }

  final String demoRunId;
  final String sourceKind;
  final int heartRateBpm;
  final DateTime observedAt;
  final String? activityContext;
  final String? sourceRecordId;
  final String ingestionIdempotencyKey;

  Map<String, dynamic> toJson() => {
    'demo_run_id': demoRunId,
    'source_kind': sourceKind,
    'heart_rate_bpm': heartRateBpm,
    // Normalize local DateTime instances so the wire value always carries
    // an explicit UTC designator accepted by the backend.
    'observed_at': observedAt.toUtc().toIso8601String(),
    'activity_context': activityContext,
    'source_record_id': sourceRecordId,
    'ingestion_idempotency_key': ingestionIdempotencyKey,
  };
}

class ReadingSubmissionResponse {
  const ReadingSubmissionResponse({
    required this.readingId,
    required this.demoRunId,
    required this.accepted,
    required this.detectionStatus,
    required this.anomalyEventId,
    required this.incidentId,
  });

  final String readingId;
  final String demoRunId;
  final bool accepted;
  final String detectionStatus;
  final String? anomalyEventId;
  final String? incidentId;

  factory ReadingSubmissionResponse.fromJson(Map<String, dynamic> json) {
    return ReadingSubmissionResponse(
      readingId: requiredString(json, 'reading_id'),
      demoRunId: requiredString(json, 'demo_run_id'),
      accepted: requiredBool(json, 'accepted'),
      detectionStatus: requiredString(json, 'detection_status'),
      anomalyEventId: optionalString(json, 'anomaly_event_id'),
      incidentId: optionalString(json, 'incident_id'),
    );
  }

  Map<String, dynamic> toJson() => {
    'reading_id': readingId,
    'demo_run_id': demoRunId,
    'accepted': accepted,
    'detection_status': detectionStatus,
    'anomaly_event_id': anomalyEventId,
    'incident_id': incidentId,
  };
}
