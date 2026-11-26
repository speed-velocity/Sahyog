const String simulatedLocationSource = 'SIMULATED';
const String deviceLocationSource = 'DEVICE';

enum LocationPermissionStatus {
  granted,
  denied,
  deniedForever,
  restricted,
  serviceDisabled,
}

enum LocationFailureCode {
  permissionDenied,
  permissionDeniedForever,
  permissionRestricted,
  serviceDisabled,
  unavailable,
  timeout,
  staleLocation,
  invalidLocation,
  invalidResponse,
  networkError,
  httpError,
  reportInProgress,
}

class LocationFailure {
  const LocationFailure(this.code, this.message);

  final LocationFailureCode code;
  final String message;
}

class LocationTransportException implements Exception {
  const LocationTransportException(this.code, this.message, {this.statusCode});

  final LocationFailureCode code;
  final String message;
  final int? statusCode;

  @override
  String toString() => message;
}

class LocationReading {
  const LocationReading({
    required this.latitude,
    required this.longitude,
    required this.capturedAt,
    required this.sourceKind,
    this.accuracyMeters,
  });

  final double latitude;
  final double longitude;
  final DateTime capturedAt;
  final String sourceKind;
  final double? accuracyMeters;

  bool get isSimulated => sourceKind.toUpperCase() == simulatedLocationSource;
}

class LocationUpdatePayload {
  const LocationUpdatePayload({
    required this.subjectUserId,
    required this.latitude,
    required this.longitude,
    required this.capturedAt,
    required this.sourceKind,
    this.incidentId,
    this.demoRunId,
    this.accuracyMeters,
  });

  final String subjectUserId;
  final String? incidentId;
  final String? demoRunId;
  final double latitude;
  final double longitude;
  final double? accuracyMeters;
  final DateTime capturedAt;
  final String sourceKind;

  Map<String, Object?> toJson() {
    final payload = <String, Object?>{
      'subject_user_id': subjectUserId,
      'latitude': latitude,
      'longitude': longitude,
      'captured_at': capturedAt.toUtc().toIso8601String(),
      'source_kind': sourceKind,
    };
    if (incidentId != null && incidentId!.isNotEmpty) {
      payload['incident_id'] = incidentId;
    }
    if (demoRunId != null && demoRunId!.isNotEmpty) {
      payload['demo_run_id'] = demoRunId;
    }
    if (accuracyMeters != null) {
      payload['accuracy_meters'] = accuracyMeters;
    }
    return payload;
  }
}

class LocationSnapshot {
  const LocationSnapshot({
    required this.locationSnapshotId,
    required this.subjectUserId,
    required this.latitude,
    required this.longitude,
    required this.capturedAt,
    required this.receivedAt,
    required this.sourceKind,
    required this.isStale,
    required this.staleAfterSeconds,
    this.incidentId,
    this.demoRunId,
    this.accuracyMeters,
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

  factory LocationSnapshot.fromJson(Map<String, dynamic> json) {
    final snapshotId = json['location_snapshot_id'];
    final subjectUserId = json['subject_user_id'];
    if (snapshotId is! String || snapshotId.isEmpty) {
      throw const FormatException('location_snapshot_id is missing');
    }
    if (subjectUserId is! String || subjectUserId.isEmpty) {
      throw const FormatException('subject_user_id is missing');
    }

    final isStale = json['is_stale'];
    if (isStale is! bool) {
      throw const FormatException('is_stale is missing');
    }

    final staleAfterSeconds = json['stale_after_seconds'];
    if (staleAfterSeconds is! num) {
      throw const FormatException('stale_after_seconds is missing');
    }

    return LocationSnapshot(
      locationSnapshotId: snapshotId,
      subjectUserId: subjectUserId,
      incidentId: _optionalString(json['incident_id']),
      demoRunId: _optionalString(json['demo_run_id']),
      latitude: _readDouble(json['latitude'], 'latitude'),
      longitude: _readDouble(json['longitude'], 'longitude'),
      accuracyMeters: _optionalDouble(json['accuracy_meters']),
      capturedAt: _readDateTime(json['captured_at'], 'captured_at'),
      receivedAt: _readDateTime(json['received_at'], 'received_at'),
      sourceKind: _readString(json['source_kind'], 'source_kind'),
      isStale: isStale,
      staleAfterSeconds: staleAfterSeconds.toInt(),
    );
  }
}

double _readDouble(Object? value, String field) {
  if (value is num && value.isFinite) {
    return value.toDouble();
  }
  throw FormatException('$field is missing or invalid');
}

double? _optionalDouble(Object? value) {
  if (value == null) {
    return null;
  }
  if (value is num && value.isFinite) {
    return value.toDouble();
  }
  throw const FormatException('accuracy_meters is invalid');
}

String _readString(Object? value, String field) {
  if (value is String && value.isNotEmpty) {
    return value;
  }
  throw FormatException('$field is missing or invalid');
}

String? _optionalString(Object? value) {
  return value is String && value.isNotEmpty ? value : null;
}

DateTime _readDateTime(Object? value, String field) {
  if (value is String) {
    final parsed = DateTime.tryParse(value);
    if (parsed != null) {
      return parsed;
    }
  }
  throw FormatException('$field is missing or invalid');
}
