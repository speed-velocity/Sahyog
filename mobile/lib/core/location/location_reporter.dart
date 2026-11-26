import 'location_models.dart';
import 'location_service.dart';

abstract class LocationUpdateSender {
  Future<LocationSnapshot> send(LocationUpdatePayload payload);
}

class LocationReport {
  const LocationReport._({this.snapshot, this.failure});

  factory LocationReport.success(LocationSnapshot snapshot) {
    return LocationReport._(snapshot: snapshot);
  }

  factory LocationReport.failure(LocationFailure failure) {
    return LocationReport._(failure: failure);
  }

  final LocationSnapshot? snapshot;
  final LocationFailure? failure;

  bool get isSuccess => snapshot != null;
}

class LocationReporter {
  LocationReporter({
    required LocationService service,
    required LocationUpdateSender sender,
    required this.subjectUserId,
    this.demoRunId,
  }) : _service = service,
       _sender = sender;

  final LocationService _service;
  final LocationUpdateSender _sender;
  final String subjectUserId;
  final String? demoRunId;

  bool _isReporting = false;

  Future<LocationReport> report({
    String? incidentId,
    bool requestPermission = true,
  }) async {
    if (_isReporting) {
      return LocationReport.failure(
        const LocationFailure(
          LocationFailureCode.reportInProgress,
          'A location update is already in progress.',
        ),
      );
    }

    _isReporting = true;
    try {
      final resolution = await _service.resolve(
        requestPermission: requestPermission,
      );
      if (!resolution.isSuccess) {
        return LocationReport.failure(resolution.failure!);
      }

      final reading = resolution.reading!;
      final payload = LocationUpdatePayload(
        subjectUserId: subjectUserId,
        incidentId: incidentId,
        demoRunId: demoRunId,
        latitude: reading.latitude,
        longitude: reading.longitude,
        accuracyMeters: reading.accuracyMeters,
        capturedAt: reading.capturedAt,
        sourceKind: reading.sourceKind,
      );

      final snapshot = await _sender.send(payload);
      return LocationReport.success(snapshot);
    } on LocationTransportException catch (error) {
      return LocationReport.failure(LocationFailure(error.code, error.message));
    } catch (_) {
      return LocationReport.failure(
        const LocationFailure(
          LocationFailureCode.networkError,
          'The location update could not be sent.',
        ),
      );
    } finally {
      _isReporting = false;
    }
  }
}
