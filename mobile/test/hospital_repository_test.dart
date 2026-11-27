import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/repositories/hospital_repository.dart';

class _MockTransport implements ApiTransport {
  final responses = <ApiTransportResponse>[];
  final requests = <Uri>[];

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) {
    requests.add(uri);
    return Future.value(responses.removeAt(0));
  }

  @override
  void close() {}
}

const _hospitalJson = '''
{
  "hospitals": [
    {
      "hospital_id": "hosp-001",
      "name": "Sahyog General Hospital",
      "address": "123 Health Ave, Pune",
      "latitude": 18.5204,
      "longitude": 73.8567,
      "distance_meters": 1250.5,
      "source_kind": "SEEDED_DEMO"
    }
  ],
  "provider": "SEEDED_DEMO_DIRECTORY",
  "disclaimer": "Seeded demonstration hospital data only.",
  "generated_at": "2026-11-28T10:00:00Z"
}
''';

void main() {
  test(
    'HospitalRepository parses nearby hospital response correctly',
    () async {
      final transport = _MockTransport()
        ..responses.add(
          const ApiTransportResponse(statusCode: 200, body: _hospitalJson),
        );
      final client = ApiClient(
        config: ApiConfig.fromBaseUrl('https://example.test/api/v1'),
        transport: transport,
      );
      final repo = HospitalRepository(client: client);

      final result = await repo.getNearbyHospitals(
        latitude: 18.5204,
        longitude: 73.8567,
      );

      expect(result.hospitals.length, 1);
      expect(result.hospitals.first.name, 'Sahyog General Hospital');
      expect(result.hospitals.first.distanceMeters, 1250.5);
      expect(result.hospitals.first.sourceKind, 'SEEDED_DEMO');
      expect(result.provider, 'SEEDED_DEMO_DIRECTORY');
      expect(result.disclaimer, 'Seeded demonstration hospital data only.');
    },
  );
}
