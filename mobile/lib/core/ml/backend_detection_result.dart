/// BackendDetectionResult — model for the actual backend `POST /api/v1/readings`
/// response.
///
/// Represents the JSON response body from the backend reading API. This model
/// mirrors the backend's Pydantic `DetectorResult` shape (when the backend
/// adapter is available) or the equivalent fallback types defined in
/// `detector_backend_contract.py`.
///
/// The backend is authoritative for anomaly detection. Flutter must NOT
/// independently decide whether an anomaly occurred. This model is used purely
/// for parsing and representing the backend's response; it does not trigger
/// any local detection, incident creation, or lifecycle changes.
library;
class BackendDetectionResult {
  /// Whether the reading was accepted and processed by the backend.
  final bool accepted;

  /// The backend's detection status for this reading.
  ///
  /// - `NORMAL`: no anomaly pattern detected.
  /// - `ANOMALY_DETECTED`: an unusual pattern was detected by the backend
  ///   detector. This triggers the verification workflow; it is NOT an incident
  ///   lifecycle status.
  final String detectionStatus;

  /// Unique identifier assigned by the backend for this reading.
  final String? readingId;

  /// The [SimRun] ID linking this reading to the active demo scenario.
  final String? demoRunId;

  /// Optional anomaly event ID, if an anomaly was detected and an event was
  /// created by the backend.
  final String? anomalyEventId;

  /// Optional incident ID, if an incident was created as a result of the
  /// anomaly detection and subsequent verification/escalation flow.
  final String? incidentId;

  /// Creates a [BackendDetectionResult] from the backend API response JSON.
  ///
  /// All fields are optional except [accepted] and [detectionStatus], which
  /// are required per the API contract. Unknown fields are forbidden.
  BackendDetectionResult({
    required this.accepted,
    required this.detectionStatus,
    this.readingId,
    this.demoRunId,
    this.anomalyEventId,
    this.incidentId,
  });

  /// Parse a [BackendDetectionResult] from the backend's JSON response body.
  ///
  /// Returns `null` if the JSON is malformed or missing required fields.
  static BackendDetectionResult? fromJson(Map<String, dynamic> json) {
    final accepted = json['accepted'] as bool?;
    final detectionStatus = json['detection_status'] as String?;

    if (accepted == null || detectionStatus == null) {
      return null;
    }

    // Validate detection_status value.
    if (detectionStatus != 'NORMAL' && detectionStatus != 'ANOMALY_DETECTED') {
      // If the value is unexpected, still accept it but the caller should
      // treat it as unknown. Do not throw; the backend may add new values
      // in the future.
    }

    return BackendDetectionResult(
      accepted: accepted,
      detectionStatus: detectionStatus,
      readingId: json['reading_id'] as String?,
      demoRunId: json['demo_run_id'] as String?,
      anomalyEventId: json['anomaly_event_id'] as String?,
      incidentId: json['incident_id'] as String?,
    );
  }

  /// Convert this model to a JSON map suitable for serialization or debugging.
  Map<String, dynamic> toJson() {
    return {
      'accepted': accepted,
      'detection_status': detectionStatus,
      if (readingId != null) 'reading_id': readingId,
      if (demoRunId != null) 'demo_run_id': demoRunId,
      if (anomalyEventId != null) 'anomaly_event_id': anomalyEventId,
      if (incidentId != null) 'incident_id': incidentId,
    };
  }

  @override
  bool operator ==(Object other) {
    if (identical(this, other)) return true;
    return other is BackendDetectionResult &&
        other.accepted == accepted &&
        other.detectionStatus == detectionStatus &&
        other.readingId == readingId &&
        other.demoRunId == demoRunId &&
        other.anomalyEventId == anomalyEventId &&
        other.incidentId == incidentId;
  }

  @override
  int get hashCode => Object.hash(
        accepted,
        detectionStatus,
        readingId,
        demoRunId,
        anomalyEventId,
        incidentId,
      );

  @override
  String toString() =>
      'BackendDetectionResult(accepted: $accepted, detectionStatus: $detectionStatus)';
}