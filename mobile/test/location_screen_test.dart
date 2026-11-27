import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/repositories/hospital_repository.dart';
import 'package:sahyog_mobile/features/location/presentation/location_screen.dart';

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
  testWidgets(
    'renders location and nearby seeded hospital list with disclaimer',
    (tester) async {
      final transport = _MockTransport()
        ..responses.add(
          const ApiTransportResponse(statusCode: 200, body: _hospitalJson),
        );
      final client = ApiClient(
        config: ApiConfig.fromBaseUrl('https://example.test/api/v1'),
        transport: transport,
      );
      final repo = HospitalRepository(client: client);

      await tester.pumpWidget(
        MaterialApp(home: LocationHospitalsScreen(hospitalRepository: repo)),
      );
      await tester.pumpAndSettle();

      expect(find.text('Device Location'), findsOneWidget);
      expect(find.text('SIMULATED'), findsOneWidget);
      expect(find.text('Hospital Directory Disclaimer'), findsOneWidget);
      expect(
        find.text('Seeded demonstration hospital data only.'),
        findsOneWidget,
      );
      expect(find.text('Sahyog General Hospital'), findsOneWidget);
      expect(find.textContaining('1.25 km · [SEEDED_DEMO]'), findsOneWidget);
    },
  );
}
