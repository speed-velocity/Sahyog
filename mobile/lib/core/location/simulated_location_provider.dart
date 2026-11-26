import 'dart:math' as math;

import 'location_models.dart';
import 'location_provider.dart';

class SimulatedLocationProvider implements LocationProvider {
  SimulatedLocationProvider({
    this.centerLatitude = 18.5204,
    this.centerLongitude = 73.8567,
    this.radiusMeters = 75,
    this.accuracyMeters = 15,
    this.permissionStatus = LocationPermissionStatus.granted,
    this.delay = Duration.zero,
    math.Random? random,
    DateTime Function()? clock,
  }) : _random = random ?? math.Random(),
       _clock = clock ?? _utcNow;

  final double centerLatitude;
  final double centerLongitude;
  final double radiusMeters;
  final double accuracyMeters;
  final LocationPermissionStatus permissionStatus;
  final Duration delay;
  final math.Random _random;
  final DateTime Function() _clock;

  static DateTime _utcNow() => DateTime.now().toUtc();

  @override
  Future<LocationPermissionStatus> checkPermission() async {
    return permissionStatus;
  }

  @override
  Future<LocationPermissionStatus> requestPermission() async {
    return permissionStatus;
  }

  @override
  Future<LocationReading> getCurrentLocation() async {
    if (delay > Duration.zero) {
      await Future<void>.delayed(delay);
    }

    final angle = _random.nextDouble() * math.pi * 2;
    final distance = _random.nextDouble() * radiusMeters;
    final latitudeOffset = (distance * math.cos(angle)) / 111320;
    final longitudeScale = 111320 * math.cos(centerLatitude * math.pi / 180);
    final longitudeOffset = longitudeScale.abs() < 0.0001
        ? 0.0
        : (distance * math.sin(angle)) / longitudeScale;

    return LocationReading(
      latitude: (centerLatitude + latitudeOffset).clamp(-90.0, 90.0).toDouble(),
      longitude: (centerLongitude + longitudeOffset)
          .clamp(-180.0, 180.0)
          .toDouble(),
      accuracyMeters: accuracyMeters,
      capturedAt: _clock().toUtc(),
      sourceKind: simulatedLocationSource,
    );
  }
}
