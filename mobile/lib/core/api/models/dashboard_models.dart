import 'json_helpers.dart';

class LatestReadingSummary {
  const LatestReadingSummary({
    required this.readingId,
    required this.heartRateBpm,
    required this.observedAt,
    required this.sourceKind,
  });

  final String readingId;
  final int heartRateBpm;
  final DateTime observedAt;
  final String sourceKind;

  factory LatestReadingSummary.fromJson(Map<String, dynamic> json) {
    return LatestReadingSummary(
      readingId: requiredString(json, 'reading_id'),
      heartRateBpm: requiredInt(json, 'heart_rate_bpm'),
      observedAt: requiredDateTime(json, 'observed_at'),
      sourceKind: requiredString(json, 'source_kind'),
    );
  }

  Map<String, dynamic> toJson() => {
    'reading_id': readingId,
    'heart_rate_bpm': heartRateBpm,
    'observed_at': observedAt.toIso8601String(),
    'source_kind': sourceKind,
  };
}

/// Matches the backend's flat dashboard overview response.
class DashboardOverviewResponse {
  const DashboardOverviewResponse({
    required this.subjectUserId,
    required this.monitoringStatus,
    required this.latestReading,
    required this.activeIncident,
    required this.incidentStatus,
    required this.latestUpdateAt,
  });

  final String subjectUserId;
  final String monitoringStatus;
  final LatestReadingSummary? latestReading;
  final String? activeIncident;
  final String? incidentStatus;
  final DateTime? latestUpdateAt;

  factory DashboardOverviewResponse.fromJson(Map<String, dynamic> json) {
    final reading = json['latest_reading'];
    if (reading != null && reading is! Map<String, dynamic>) {
      throw const FormatException('latest_reading is not an object or null.');
    }
    return DashboardOverviewResponse(
      subjectUserId: requiredString(json, 'subject_user_id'),
      monitoringStatus: requiredString(json, 'monitoring_status'),
      latestReading: reading == null
          ? null
          : LatestReadingSummary.fromJson(reading as Map<String, dynamic>),
      activeIncident: optionalString(json, 'active_incident'),
      incidentStatus: optionalString(json, 'incident_status'),
      latestUpdateAt: optionalDateTime(json, 'latest_update_at'),
    );
  }

  Map<String, dynamic> toJson() => {
    'subject_user_id': subjectUserId,
    'monitoring_status': monitoringStatus,
    'latest_reading': latestReading?.toJson(),
    'active_incident': activeIncident,
    'incident_status': incidentStatus,
    'latest_update_at': latestUpdateAt?.toIso8601String(),
  };
}
