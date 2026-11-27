import '../api_client.dart';
import '../api_response_parser.dart';
import '../models/hospital_models.dart';

class HospitalRepository {
  HospitalRepository({required this.client});

  final ApiClient client;

  Future<NearbyHospitalsResponse> getNearbyHospitals({
    required double latitude,
    required double longitude,
    int limit = 5,
  }) async {
    final query = <String, String>{
      'latitude': latitude.toString(),
      'longitude': longitude.toString(),
      'limit': limit.toString(),
    };
    final response = await client.get(
      'hospitals/nearby?${Uri(queryParameters: query).query}',
    );
    return parseApiObject(
      response,
      'nearby hospitals',
      NearbyHospitalsResponse.fromJson,
    );
  }
}
