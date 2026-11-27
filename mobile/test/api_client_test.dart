import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_exception.dart';

class _CapturedRequest {
  const _CapturedRequest({
    required this.method,
    required this.uri,
    required this.headers,
    required this.bodyBytes,
  });

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final List<int> bodyBytes;
}

class _FakeTransport implements ApiTransport {
  ApiTransportResponse response = const ApiTransportResponse(
    statusCode: 200,
    body: '{"ok":true}',
  );
  Object? error;
  Future<ApiTransportResponse>? pending;
  _CapturedRequest? lastRequest;
  final requests = <_CapturedRequest>[];
  bool closed = false;

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) async {
    lastRequest = _CapturedRequest(
      method: method,
      uri: uri,
      headers: Map.of(headers),
      bodyBytes: List.of(bodyBytes),
    );
    requests.add(lastRequest!);
    if (pending case final response?) return response;
    if (error case final failure?) throw failure;
    return response;
  }

  @override
  void close() => closed = true;
}

void main() {
  group('ApiClient', () {
    late _FakeTransport transport;
    late ApiClient client;

    setUp(() {
      transport = _FakeTransport();
      client = ApiClient(
        config: ApiConfig.fromBaseUrl('https://backend.example.test/api/v1'),
        transport: transport,
      );
    });

    tearDown(() => client.close());

    test('GET resolves paths relative to the API root', () async {
      final result = await client.get('incidents?limit=25');

      expect(result, {'ok': true});
      expect(transport.lastRequest?.method, 'GET');
      expect(
        transport.lastRequest?.uri.toString(),
        'https://backend.example.test/api/v1/incidents?limit=25',
      );
      expect(transport.lastRequest?.headers['Accept'], 'application/json');
      expect(
        transport.lastRequest?.headers.containsKey('Authorization'),
        isFalse,
      );
    });

    test('adds Bearer authorization to protected requests', () async {
      await client.get('incidents', bearerToken: '  test-access-token  ');

      expect(
        transport.lastRequest?.headers['Authorization'],
        'Bearer test-access-token',
      );
    });

    test('JSON POST serializes its body and can add a Bearer token', () async {
      await client.postJson(
        'demo/runs',
        body: {'scenario': 'NORMAL'},
        bearerToken: 'access-token',
      );

      expect(transport.lastRequest?.method, 'POST');
      expect(
        transport.lastRequest?.headers['Content-Type'],
        'application/json; charset=utf-8',
      );
      expect(jsonDecode(utf8.decode(transport.lastRequest!.bodyBytes)), {
        'scenario': 'NORMAL',
      });
      expect(
        transport.lastRequest?.headers['Authorization'],
        'Bearer access-token',
      );
    });

    test('form POST uses OAuth2 form encoding rather than JSON', () async {
      await client.postForm(
        'auth/token',
        fields: {'username': 'subject demo', 'password': 'test&pass'},
      );

      final request = transport.lastRequest!;
      expect(
        request.headers['Content-Type'],
        'application/x-www-form-urlencoded; charset=utf-8',
      );
      expect(Uri.splitQueryString(utf8.decode(request.bodyBytes)), {
        'username': 'subject demo',
        'password': 'test&pass',
      });
      expect(request.headers.containsKey('Authorization'), isFalse);
    });

    test(
      'maps backend error statuses and messages to typed exceptions',
      () async {
        final cases = <int, ApiExceptionType>{
          400: ApiExceptionType.validation,
          401: ApiExceptionType.unauthorized,
          403: ApiExceptionType.forbidden,
          404: ApiExceptionType.notFound,
          422: ApiExceptionType.validation,
          500: ApiExceptionType.server,
        };

        for (final entry in cases.entries) {
          transport.response = ApiTransportResponse(
            statusCode: entry.key,
            body: '{"detail":"backend message"}',
          );
          await expectLater(
            client.get('incidents'),
            throwsA(
              isA<ApiException>()
                  .having((error) => error.type, 'type', entry.value)
                  .having((error) => error.statusCode, 'status', entry.key)
                  .having(
                    (error) => error.message,
                    'message',
                    'backend message',
                  ),
            ),
          );
        }
      },
    );

    test('maps an idempotency payload conflict to a typed conflict', () async {
      transport.response = const ApiTransportResponse(
        statusCode: 409,
        body: '{"detail":"Idempotency key was already used with another payload"}',
      );

      await expectLater(
        client.postJson(
          'demo/runs',
          body: {
            'scenario': 'TRUE_ANOMALY',
            'start_idempotency_key': 'run-key-1',
          },
        ),
        throwsA(
          isA<ApiException>()
              .having((error) => error.type, 'type', ApiExceptionType.conflict)
              .having((error) => error.statusCode, 'status', 409)
              .having(
                (error) => error.message,
                'message',
                'Idempotency key was already used with another payload',
              ),
        ),
      );
    });

    test(
      'returns backend reading replay response for an identical retry',
      () async {
        const replayBody =
            '{"reading_id":"reading-1","demo_run_id":"run-1",'
            '"accepted":true,"detection_status":"ANOMALY_DETECTED",'
            '"anomaly_event_id":"event-1","incident_id":"incident-1"}';
        transport.response = const ApiTransportResponse(
          statusCode: 202,
          body: replayBody,
        );
        const readingPayload = {
          'demo_run_id': 'run-1',
          'source_kind': 'SIMULATED',
          'heart_rate_bpm': 164,
          'observed_at': '2026-11-28T10:00:00Z',
          'activity_context': null,
          'source_record_id': 'sample-1',
          'ingestion_idempotency_key': 'reading-key-1',
        };

        final first = await client.postJson(
          'readings',
          body: readingPayload,
          bearerToken: 'access-token',
        );
        final retry = await client.postJson(
          'readings',
          body: readingPayload,
          bearerToken: 'access-token',
        );

        expect(transport.requests, hasLength(2));
        expect(
          transport.requests[0].bodyBytes,
          orderedEquals(transport.requests[1].bodyBytes),
        );
        expect(first, retry);
        final replayedReading = retry! as Map<String, dynamic>;
        expect(replayedReading['anomaly_event_id'], 'event-1');
        expect(replayedReading['incident_id'], 'incident-1');
      },
    );

    test(
      'parses FastAPI validation details and location error envelopes',
      () async {
        transport.response = const ApiTransportResponse(
          statusCode: 422,
          body: '{"detail":[{"msg":"field required"}]}',
        );
        await expectLater(
          client.get('readings'),
          throwsA(
            isA<ApiException>().having(
              (error) => error.message,
              'message',
              'field required',
            ),
          ),
        );

        transport.response = const ApiTransportResponse(
          statusCode: 404,
          body: '{"error":{"code":"NOT_FOUND","message":"No location"}}',
        );
        await expectLater(
          client.get('location/latest'),
          throwsA(
            isA<ApiException>().having(
              (error) => error.message,
              'message',
              'No location',
            ),
          ),
        );
      },
    );

    test('maps network failures and request timeouts', () async {
      transport.error = const SocketException('connection failed');
      await expectLater(
        client.get('health'),
        throwsA(
          isA<ApiException>().having(
            (error) => error.type,
            'type',
            ApiExceptionType.network,
          ),
        ),
      );

      final slowTransport = _FakeTransport()
        ..pending = Completer<ApiTransportResponse>().future;
      final shortClient = ApiClient(
        config: ApiConfig.fromBaseUrl('https://backend.example.test/api/v1'),
        transport: slowTransport,
        timeout: const Duration(milliseconds: 5),
      );
      addTearDown(shortClient.close);

      await expectLater(
        shortClient.get('health'),
        throwsA(
          isA<ApiException>().having(
            (error) => error.type,
            'type',
            ApiExceptionType.timeout,
          ),
        ),
      );
    });

    test('rejects a successful response that is not JSON', () async {
      transport.response = const ApiTransportResponse(
        statusCode: 200,
        body: 'not json',
      );

      await expectLater(
        client.get('health'),
        throwsA(
          isA<ApiException>().having(
            (error) => error.type,
            'type',
            ApiExceptionType.invalidResponse,
          ),
        ),
      );
    });
  });
}
