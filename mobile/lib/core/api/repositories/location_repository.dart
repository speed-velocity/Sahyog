import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';

class LocationSnapshotResponse {
  const LocationSnapshotResponse({
    required this.locationSnapshotId,
    required this.subjectUserId,
    this.incidentId,
    this.demoRunId,
    required this.latitude,
    required this.longitude,
    this.accuracyMeters,
    required this.capturedAt,
    required this.receivedAt,
    required this.sourceKind,
    required this.isStale,
    required this.staleAfterSeconds,
  });

  final String locationSnapshotId;
  final String subjectUserId;
  final String? incidentId;
  final String? demoRunId;
  final double latitude;
  final double longitude;
  final double? accuracyMeters;
  final DateTime capturedAt;
  final DateTime receivedAt;
  final String sourceKind;
  final bool isStale;
  final int staleAfterSeconds;

  factory LocationSnapshotResponse.fromJson(Map<String, dynamic> json) {
    return LocationSnapshotResponse(
      locationSnapshotId: json['location_snapshot_id'] as String,
      subjectUserId: json['subject_user_id'] as String,
      incidentId: json['incident_id'] as String?,
      demoRunId: json['demo_run_id'] as String?,
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      accuracyMeters: (json['accuracy_meters'] as num?)?.toDouble(),
      capturedAt: DateTime.parse(json['captured_at'] as String),
      receivedAt: DateTime.parse(json['received_at'] as String),
      sourceKind: json['source_kind'] as String,
      isStale: json['is_stale'] as bool,
      staleAfterSeconds: json['stale_after_seconds'] as int,
    );
  }

  Map<String, dynamic> toJson() => {
    'location_snapshot_id': locationSnapshotId,
    'subject_user_id': subjectUserId,
    if (incidentId != null) 'incident_id': incidentId,
    if (demoRunId != null) 'demo_run_id': demoRunId,
    'latitude': latitude,
    'longitude': longitude,
    if (accuracyMeters != null) 'accuracy_meters': accuracyMeters,
    'captured_at': capturedAt.toIso8601String(),
    'received_at': receivedAt.toIso8601String(),
    'source_kind': sourceKind,
    'is_stale': isStale,
    'stale_after_seconds': staleAfterSeconds,
  };
}

class LocationRepository {
  LocationRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<LocationSnapshotResponse> submitUpdate({
    required String subjectUserId,
    required double latitude,
    required double longitude,
    double? accuracyMeters,
    String? incidentId,
    String? demoRunId,
    String sourceKind = 'SIMULATED',
    DateTime? capturedAt,
  }) async {
    final payload = <String, dynamic>{
      'subject_user_id': subjectUserId,
      if (incidentId != null) 'incident_id': incidentId,
      if (demoRunId != null) 'demo_run_id': demoRunId,
      'latitude': latitude,
      'longitude': longitude,
      if (accuracyMeters != null) 'accuracy_meters': accuracyMeters,
      'captured_at': (capturedAt ?? DateTime.now().toUtc()).toIso8601String(),
      'source_kind': sourceKind,
    };

    final response = await client.postJson('location/updates', body: payload);
    return parseApiObject(
      response,
      'location snapshot',
      LocationSnapshotResponse.fromJson,
    );
  }

  Future<LocationSnapshotResponse> getLatest({
    String? subjectUserId,
    String? incidentId,
  }) async {
    final query = <String, String>{};
    if (subjectUserId != null) query['subject_user_id'] = subjectUserId;
    if (incidentId != null) query['incident_id'] = incidentId;

    final response = await client.get(
      'location/latest?${Uri(queryParameters: query).query}',
    );
    return parseApiObject(
      response,
      'location snapshot',
      LocationSnapshotResponse.fromJson,
    );
  }
}
