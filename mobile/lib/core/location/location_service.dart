import 'dart:async';

import 'location_models.dart';
import 'location_provider.dart';

class LocationResolution {
  const LocationResolution._({this.reading, this.failure});

  factory LocationResolution.success(LocationReading reading) {
    return LocationResolution._(reading: reading);
  }

  factory LocationResolution.failure(LocationFailure failure) {
    return LocationResolution._(failure: failure);
  }

  final LocationReading? reading;
  final LocationFailure? failure;

  bool get isSuccess => reading != null;
}

class LocationService {
  LocationService({
    required LocationProvider provider,
    this.staleAfter = const Duration(seconds: 300),
    this.timeout = const Duration(seconds: 15),
    DateTime Function()? clock,
  }) : _provider = provider,
       _clock = clock ?? DateTime.now;

  final LocationProvider _provider;
  final Duration staleAfter;
  final Duration timeout;
  final DateTime Function() _clock;

  Future<LocationResolution> resolve({bool requestPermission = true}) async {
    LocationPermissionStatus permission;

    try {
      permission = await _provider.checkPermission().timeout(timeout);
    } on TimeoutException {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.timeout,
          'Location permission check timed out.',
        ),
      );
    } catch (_) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.unavailable,
          'Location permission could not be checked.',
        ),
      );
    }

    if (permission == LocationPermissionStatus.denied && requestPermission) {
      try {
        permission = await _provider.requestPermission().timeout(timeout);
      } on TimeoutException {
        return LocationResolution.failure(
          const LocationFailure(
            LocationFailureCode.timeout,
            'Location permission request timed out.',
          ),
        );
      } catch (_) {
        return LocationResolution.failure(
          const LocationFailure(
            LocationFailureCode.unavailable,
            'Location permission could not be requested.',
          ),
        );
      }
    }

    if (permission != LocationPermissionStatus.granted) {
      return LocationResolution.failure(_permissionFailure(permission));
    }

    LocationReading reading;
    try {
      reading = await _provider.getCurrentLocation().timeout(timeout);
    } on TimeoutException {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.timeout,
          'Getting the current location timed out.',
        ),
      );
    } catch (_) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.unavailable,
          'The current location is unavailable.',
        ),
      );
    }

    return _validate(reading);
  }

  LocationResolution _validate(LocationReading reading) {
    if (!reading.latitude.isFinite ||
        !reading.longitude.isFinite ||
        reading.latitude < -90 ||
        reading.latitude > 90 ||
        reading.longitude < -180 ||
        reading.longitude > 180) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.invalidLocation,
          'The location provider returned invalid coordinates.',
        ),
      );
    }

    final accuracy = reading.accuracyMeters;
    if (accuracy != null && (!accuracy.isFinite || accuracy <= 0)) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.invalidLocation,
          'The location provider returned an invalid accuracy value.',
        ),
      );
    }

    final sourceKind = reading.sourceKind.trim().toUpperCase();
    if (sourceKind.isEmpty) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.invalidLocation,
          'The location source is not identified.',
        ),
      );
    }

    final capturedAt = reading.capturedAt.toUtc();
    final now = _clock().toUtc();
    final age = now.difference(capturedAt);

    if (age.isNegative && age.abs() > const Duration(minutes: 2)) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.invalidLocation,
          'The location timestamp is not credible.',
        ),
      );
    }

    if (age > staleAfter) {
      return LocationResolution.failure(
        const LocationFailure(
          LocationFailureCode.staleLocation,
          'The current location is too old to report.',
        ),
      );
    }

    return LocationResolution.success(
      LocationReading(
        latitude: reading.latitude,
        longitude: reading.longitude,
        accuracyMeters: accuracy,
        capturedAt: capturedAt,
        sourceKind: sourceKind,
      ),
    );
  }

  LocationFailure _permissionFailure(LocationPermissionStatus permission) {
    if (permission == LocationPermissionStatus.deniedForever) {
      return const LocationFailure(
        LocationFailureCode.permissionDeniedForever,
        'Location permission is permanently denied. Enable it in system settings.',
      );
    }
    if (permission == LocationPermissionStatus.restricted) {
      return const LocationFailure(
        LocationFailureCode.permissionRestricted,
        'Location access is restricted on this device.',
      );
    }
    if (permission == LocationPermissionStatus.serviceDisabled) {
      return const LocationFailure(
        LocationFailureCode.serviceDisabled,
        'Location services are disabled on this device.',
      );
    }
    return const LocationFailure(
      LocationFailureCode.permissionDenied,
      'Location permission was not granted.',
    );
  }
}
