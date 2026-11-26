import 'location_models.dart';

abstract class LocationProvider {
  Future<LocationPermissionStatus> checkPermission();

  Future<LocationPermissionStatus> requestPermission();

  Future<LocationReading> getCurrentLocation();
}
