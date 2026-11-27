import 'json_helpers.dart';

class IncidentResponse {
  const IncidentResponse({
    required this.incidentId,
    required this.subjectUserId,
    required this.demoRunId,
    required this.runGeneration,
    required this.status,
    required this.createdAt,
    required this.updatedAt,
    required this.verificationDeadlineAt,
    required this.resolvedAt,
  });

  final String incidentId;
  final String subjectUserId;
  final String? demoRunId;
  final int? runGeneration;

  /// Kept as a string because the backend response schema exposes `status`
  /// as a string and the backend remains authoritative for its vocabulary.
  final String status;
  final DateTime createdAt;
  final DateTime updatedAt;
  final DateTime? verificationDeadlineAt;
  final DateTime? resolvedAt;

  factory IncidentResponse.fromJson(Map<String, dynamic> json) {
    return IncidentResponse(
      incidentId: requiredString(json, 'incident_id'),
      subjectUserId: requiredString(json, 'subject_user_id'),
      demoRunId: optionalString(json, 'demo_run_id'),
      runGeneration: optionalInt(json, 'run_generation'),
      status: requiredString(json, 'status'),
      createdAt: requiredDateTime(json, 'created_at'),
      updatedAt: requiredDateTime(json, 'updated_at'),
      verificationDeadlineAt: optionalDateTime(
        json,
        'verification_deadline_at',
      ),
      resolvedAt: optionalDateTime(json, 'resolved_at'),
    );
  }

  Map<String, dynamic> toJson() => {
    'incident_id': incidentId,
    'subject_user_id': subjectUserId,
    'demo_run_id': demoRunId,
    'run_generation': runGeneration,
    'status': status,
    'created_at': createdAt.toIso8601String(),
    'updated_at': updatedAt.toIso8601String(),
    'verification_deadline_at': verificationDeadlineAt?.toIso8601String(),
    'resolved_at': resolvedAt?.toIso8601String(),
  };
}

class IncidentListResponse {
  const IncidentListResponse(this.incidents);

  final List<IncidentResponse> incidents;

  factory IncidentListResponse.fromJson(Object? json) {
    if (json is! List) {
      throw const FormatException('Incident response is not a JSON list.');
    }
    return IncidentListResponse(
      json
          .map((item) {
            if (item is! Map<String, dynamic>) {
              throw const FormatException(
                'Incident list item is not an object.',
              );
            }
            return IncidentResponse.fromJson(item);
          })
          .toList(growable: false),
    );
  }

  List<Map<String, dynamic>> toJson() =>
      incidents.map((incident) => incident.toJson()).toList(growable: false);
}
