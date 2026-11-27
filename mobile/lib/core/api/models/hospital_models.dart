import 'json_helpers.dart';

class NearbyHospital {
  const NearbyHospital({
    required this.hospitalId,
    required this.name,
    required this.address,
    required this.latitude,
    required this.longitude,
    required this.distanceMeters,
    required this.sourceKind,
  });

  final String hospitalId;
  final String name;
  final String address;
  final double latitude;
  final double longitude;
  final double distanceMeters;
  final String sourceKind;

  factory NearbyHospital.fromJson(Map<String, dynamic> json) {
    return NearbyHospital(
      hospitalId: requiredString(json, 'hospital_id'),
      name: requiredString(json, 'name'),
      address: requiredString(json, 'address'),
      latitude: (json['latitude'] as num).toDouble(),
      longitude: (json['longitude'] as num).toDouble(),
      distanceMeters: (json['distance_meters'] as num).toDouble(),
      sourceKind: requiredString(json, 'source_kind'),
    );
  }

  Map<String, dynamic> toJson() => {
    'hospital_id': hospitalId,
    'name': name,
    'address': address,
    'latitude': latitude,
    'longitude': longitude,
    'distance_meters': distanceMeters,
    'source_kind': sourceKind,
  };
}

class NearbyHospitalsResponse {
  const NearbyHospitalsResponse({
    required this.hospitals,
    this.provider,
    required this.disclaimer,
    required this.generatedAt,
  });

  final List<NearbyHospital> hospitals;
  final String? provider;
  final String disclaimer;
  final DateTime generatedAt;

  factory NearbyHospitalsResponse.fromJson(Map<String, dynamic> json) {
    final rawHospitals = json['hospitals'];
    final hospitalsList = (rawHospitals is List)
        ? rawHospitals
              .map(
                (item) => NearbyHospital.fromJson(item as Map<String, dynamic>),
              )
              .toList(growable: false)
        : const <NearbyHospital>[];

    return NearbyHospitalsResponse(
      hospitals: hospitalsList,
      provider: optionalString(json, 'provider'),
      disclaimer: requiredString(json, 'disclaimer'),
      generatedAt: requiredDateTime(json, 'generated_at'),
    );
  }

  Map<String, dynamic> toJson() => {
    'hospitals': hospitals.map((h) => h.toJson()).toList(),
    if (provider != null) 'provider': provider,
    'disclaimer': disclaimer,
    'generated_at': generatedAt.toIso8601String(),
  };
}
