import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_exception.dart';
import 'package:sahyog_mobile/core/api/api_session.dart';
import 'package:sahyog_mobile/core/api/models/auth_models.dart';
import 'package:sahyog_mobile/core/api/models/demo_models.dart';
import 'package:sahyog_mobile/core/api/models/reading_models.dart';
import 'package:sahyog_mobile/core/api/models/verification_model.dart';
import 'package:sahyog_mobile/core/api/repositories/authentication_repository.dart';
import 'package:sahyog_mobile/core/api/repositories/dashboard_repository.dart';
import 'package:sahyog_mobile/core/api/repositories/demo_repository.dart';
import 'package:sahyog_mobile/core/api/repositories/incident_repository.dart';
import 'package:sahyog_mobile/core/api/repositories/reading_repository.dart';
import 'package:sahyog_mobile/core/api/repositories/verification_repository.dart';

class _RequestRecord {
  const _RequestRecord(this.method, this.uri, this.headers, this.body);

  final String method;
  final Uri uri;
  final Map<String, String> headers;
  final String body;
}

class _MockTransport implements ApiTransport {
  final requests = <_RequestRecord>[];
  ApiTransportResponse response = const ApiTransportResponse(
    statusCode: 200,
    body: '{}',
  );
  Object? failure;
  Completer<ApiTransportResponse>? pending;

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) async {
    requests.add(
      _RequestRecord(method, uri, Map.of(headers), utf8.decode(bodyBytes)),
    );
    if (pending != null) return pending!.future;
    if (failure != null) throw failure!;
    return response;
  }

  @override
  void close() {}
}

Map<String, dynamic> _demoJson({String scenario = 'NORMAL'}) => {
  'demo_run_id': 'run-1',
  'subject_user_id': 'subject-1',
  'scenario': scenario,
  'status': 'RUNNING',
  'outcome': null,
  'current_generation': 1,
  'started_at': '2026-11-28T10:00:00Z',
  'completed_at': null,
  'reset_at': null,
};

Map<String, dynamic> _incidentJson({String? status = 'PENDING_VERIFICATION'}) =>
    {
      'incident_id': 'incident-1',
      'subject_user_id': 'subject-1',
      'demo_run_id': 'run-1',
      'run_generation': 1,
      'status': status,
      'created_at': '2026-11-28T10:00:00Z',
      'updated_at': '2026-11-28T10:00:00Z',
      'verification_deadline_at': null,
      'resolved_at': null,
    };

void main() {
  group('endpoint repositories', () {
    late _MockTransport transport;
    late ApiClient client;
    late ApiSession session;

    setUp(() {
      transport = _MockTransport();
      client = ApiClient(
        config: ApiConfig.fromBaseUrl('https://api.example.test/api/v1'),
        transport: transport,
      );
      session = ApiSession();
    });

    tearDown(() => client.close());

    test(
      'registers with exact JSON fields and logs in with form encoding',
      () async {
        final auth = AuthenticationRepository(client: client, session: session);
        transport.response = const ApiTransportResponse(
          statusCode: 201,
          body: '{"user_id":"subject-1","role":"SUBJECT"}',
        );
        final registered = await auth.register(
          const RegistrationRequest(
            loginIdentifier: 'subject@example.test',
            password: 'long-test-password',
            role: 'SUBJECT',
          ),
        );
        expect(registered.userId, 'subject-1');
        expect(transport.requests.single.uri.path, '/api/v1/auth/register');
        expect(jsonDecode(transport.requests.single.body), {
          'login_identifier': 'subject@example.test',
          'password': 'long-test-password',
          'role': 'SUBJECT',
        });

        transport.response = const ApiTransportResponse(
          statusCode: 200,
          body: '{"access_token":"runtime-token","token_type":"bearer"}',
        );
        final token = await auth.login(
          username: 'subject@example.test',
          password: 'long-test-password',
        );
        expect(token.accessToken, 'runtime-token');
        expect(session.requireAccessToken(), 'runtime-token');
        final login = transport.requests.last;
        expect(login.uri.path, '/api/v1/auth/token');
        expect(
          login.headers['Content-Type'],
          'application/x-www-form-urlencoded; charset=utf-8',
        );
        expect(Uri.splitQueryString(login.body), {
          'username': 'subject@example.test',
          'password': 'long-test-password',
        });
        expect(login.headers.containsKey('Authorization'), isFalse);

        auth.logout();
        expect(session.isAuthenticated, isFalse);
        expect(
          () => session.requireAccessToken(),
          throwsA(isA<ApiException>()),
        );
      },
    );

    test(
      'demo start preserves scenario/key and get/reset use backend routes',
      () async {
        session.setAccessToken('runtime-token');
        transport.response = ApiTransportResponse(
          statusCode: 201,
          body: jsonEncode(_demoJson(scenario: 'TRUE_ANOMALY')),
        );
        final repository = DemoRepository(client: client, session: session);
        final request = DemoRunCreateRequest(
          scenario: 'TRUE_ANOMALY',
          startIdempotencyKey: 'start-key-1',
        );
        final started = await repository.start(request);
        expect(started.demoRunId, 'run-1');
        final create = transport.requests.single;
        expect(create.method, 'POST');
        expect(create.uri.path, '/api/v1/demo/runs');
        expect(create.headers['Authorization'], 'Bearer runtime-token');
        expect(jsonDecode(create.body), {
          'scenario': 'TRUE_ANOMALY',
          'start_idempotency_key': 'start-key-1',
        });

        transport.response = ApiTransportResponse(
          statusCode: 201,
          body: jsonEncode(_demoJson(scenario: 'TRUE_ANOMALY')),
        );
        await repository.start(request);
        expect(transport.requests[0].body, transport.requests[1].body);
        expect(
          transport.requests[1].headers['Authorization'],
          'Bearer runtime-token',
        );

        transport.response = ApiTransportResponse(
          statusCode: 200,
          body: jsonEncode(_demoJson()),
        );
        await repository.get('run-1');
        expect(transport.requests.last.uri.path, '/api/v1/demo/runs/run-1');

        transport.response = ApiTransportResponse(
          statusCode: 200,
          body: jsonEncode(_demoJson()),
        );
        await repository.reset('run-1');
        final reset = transport.requests.last;
        expect(reset.method, 'POST');
        expect(reset.uri.path, '/api/v1/demo/runs/run-1/reset');
        expect(reset.body, isEmpty);
      },
    );

    test(
      'reading retry sends identical UTC payload/key and does not auto-retry',
      () async {
        session.setAccessToken('runtime-token');
        final repository = ReadingRepository(client: client, session: session);
        final request = ReadingSubmissionRequest(
          demoRunId: 'run-1',
          heartRateBpm: 164,
          observedAt: DateTime.utc(2026, 11, 28, 9, 30),
          activityContext: 'WALKING',
          sourceRecordId: 'sample-7',
          ingestionIdempotencyKey: 'reading-key-7',
        );
        transport.response = const ApiTransportResponse(
          statusCode: 202,
          body:
              '{"reading_id":"reading-1","demo_run_id":"run-1",'
              '"accepted":true,"detection_status":"ANOMALY_DETECTED",'
              '"anomaly_event_id":"event-1","incident_id":"incident-1"}',
        );
        final first = await repository.submit(request);
        final retry = await repository.submit(request);
        expect(first.incidentId, 'incident-1');
        expect(transport.requests, hasLength(2));
        expect(transport.requests[0].body, transport.requests[1].body);
        final body =
            jsonDecode(transport.requests[0].body) as Map<String, dynamic>;
        expect(body['source_kind'], 'SIMULATED');
        expect(body['ingestion_idempotency_key'], 'reading-key-7');
        expect(body['observed_at'], '2026-11-28T09:30:00.000Z');
        expect(retry.incidentId, first.incidentId);

        transport.response = const ApiTransportResponse(
          statusCode: 409,
          body: '{"detail":"idempotency key payload conflict"}',
        );
        await expectLater(
          repository.submit(
            ReadingSubmissionRequest(
              demoRunId: request.demoRunId,
              heartRateBpm: 165,
              observedAt: request.observedAt,
              activityContext: request.activityContext,
              sourceRecordId: request.sourceRecordId,
              ingestionIdempotencyKey: request.ingestionIdempotencyKey,
            ),
          ),
          throwsA(
            isA<ApiException>().having(
              (error) => error.type,
              'type',
              ApiExceptionType.conflict,
            ),
          ),
        );
        expect(transport.requests, hasLength(3));
      },
    );

    test('parses base incident list and detail responses only', () async {
      session.setAccessToken('runtime-token');
      final repository = IncidentRepository(client: client, session: session);
      transport.response = ApiTransportResponse(
        statusCode: 200,
        body: jsonEncode([_incidentJson()]),
      );
      final incidents = await repository.list(
        subjectUserId: 'subject-1',
        statusFilter: 'PENDING_VERIFICATION',
        limit: 20,
      );
      expect(incidents.incidents.single.status, 'PENDING_VERIFICATION');
      expect(transport.requests.single.uri.path, '/api/v1/incidents');
      expect(transport.requests.single.uri.queryParameters, {
        'limit': '20',
        'subject_user_id': 'subject-1',
        'status_filter': 'PENDING_VERIFICATION',
      });

      transport.response = ApiTransportResponse(
        statusCode: 200,
        body: jsonEncode(_incidentJson()),
      );
      final detail = await repository.get('incident-1');
      expect(detail.incidentId, 'incident-1');
      expect(transport.requests.last.uri.path, '/api/v1/incidents/incident-1');
    });

    test(
      'verification posts I_AM_OK with exact key and bearer token',
      () async {
        session.setAccessToken('runtime-token');
        transport.response = ApiTransportResponse(
          statusCode: 200,
          body: jsonEncode(_incidentJson(status: 'RESOLVED_FALSE_ALARM')),
        );
        final repository = VerificationRepository(
          client: client,
          session: session,
        );
        const request = VerificationRequest(
          idempotencyKey: 'verification-action-1',
          requestReference: 'ui-reference-1',
        );
        final response = await repository.submit(
          incidentId: 'incident-1',
          request: request,
        );
        expect(response.status, 'RESOLVED_FALSE_ALARM');
        final sent = transport.requests.single;
        expect(sent.uri.path, '/api/v1/incidents/incident-1/verification');
        expect(sent.headers['Authorization'], 'Bearer runtime-token');
        expect(jsonDecode(sent.body), {
          'response': 'I_AM_OK',
          'idempotency_key': 'verification-action-1',
          'request_reference': 'ui-reference-1',
        });

        transport.response = ApiTransportResponse(
          statusCode: 200,
          body: jsonEncode(_incidentJson(status: 'RESOLVED_FALSE_ALARM')),
        );
        await repository.submit(incidentId: 'incident-1', request: request);
        expect(transport.requests[0].body, transport.requests[1].body);
        expect(
          transport.requests[1].headers['Authorization'],
          'Bearer runtime-token',
        );
      },
    );

    test(
      'protected calls require a token and verification requires a key',
      () async {
        final demos = DemoRepository(client: client, session: session);
        await expectLater(
          demos.get('run-1'),
          throwsA(
            isA<ApiException>().having(
              (error) => error.type,
              'type',
              ApiExceptionType.unauthorized,
            ),
          ),
        );
        expect(transport.requests, isEmpty);

        session.setAccessToken('runtime-token');
        await expectLater(
          VerificationRepository(client: client, session: session).submit(
            incidentId: 'incident-1',
            request: const VerificationRequest(idempotencyKey: ''),
          ),
          throwsArgumentError,
        );
        expect(transport.requests, isEmpty);
      },
    );

    test('dashboard parses flat contract and null optional data', () async {
      session.setAccessToken('runtime-token');
      final repository = DashboardRepository(client: client, session: session);
      transport.response = const ApiTransportResponse(
        statusCode: 200,
        body:
            '{"subject_user_id":"subject-1",'
            '"monitoring_status":"NORMAL","latest_reading":null,'
            '"active_incident":null,"incident_status":null,'
            '"latest_update_at":null}',
      );
      final overview = await repository.getOverview();
      expect(overview.monitoringStatus, 'NORMAL');
      expect(overview.latestReading, isNull);
      expect(overview.activeIncident, isNull);
      expect(overview.incidentStatus, isNull);
      expect(overview.latestUpdateAt, isNull);
      expect(transport.requests.single.uri.path, '/api/v1/dashboard/overview');
    });

    test(
      'dashboard parses populated latest reading and subject query',
      () async {
        session.setAccessToken('runtime-token');
        transport.response = const ApiTransportResponse(
          statusCode: 200,
          body:
              '{"subject_user_id":"subject-1",'
              '"monitoring_status":"INCIDENT_ACTIVE",'
              '"latest_reading":{"reading_id":"reading-1",'
              '"heart_rate_bpm":164,"observed_at":"2026-11-28T10:00:00Z",'
              '"source_kind":"SIMULATED"},'
              '"active_incident":"incident-1",'
              '"incident_status":"PENDING_VERIFICATION",'
              '"latest_update_at":"2026-11-28T10:00:01Z"}',
        );
        final overview = await DashboardRepository(
          client: client,
          session: session,
        ).getOverview(subjectUserId: 'subject-1');
        expect(overview.monitoringStatus, 'INCIDENT_ACTIVE');
        expect(overview.latestReading?.heartRateBpm, 164);
        expect(overview.latestReading?.sourceKind, 'SIMULATED');
        expect(overview.activeIncident, 'incident-1');
        expect(overview.incidentStatus, 'PENDING_VERIFICATION');
        expect(transport.requests.single.uri.queryParameters, {
          'subject_user_id': 'subject-1',
        });
      },
    );

    test('malformed endpoint JSON maps to invalid response', () async {
      session.setAccessToken('runtime-token');
      transport.response = const ApiTransportResponse(
        statusCode: 200,
        body: '{"subject_user_id":3}',
      );
      await expectLater(
        DashboardRepository(client: client, session: session).getOverview(),
        throwsA(
          isA<ApiException>().having(
            (error) => error.type,
            'type',
            ApiExceptionType.invalidResponse,
          ),
        ),
      );
    });

    test(
      'network and timeout failures are surfaced without automatic retry',
      () async {
        session.setAccessToken('runtime-token');
        final repository = ReadingRepository(client: client, session: session);
        final request = ReadingSubmissionRequest(
          demoRunId: 'run-1',
          heartRateBpm: 72,
          observedAt: DateTime.utc(2026, 11, 28),
          ingestionIdempotencyKey: 'stable-key',
        );
        transport.failure = const SocketException('network unavailable');
        await expectLater(
          repository.submit(request),
          throwsA(
            isA<ApiException>().having(
              (error) => error.type,
              'type',
              ApiExceptionType.network,
            ),
          ),
        );
        expect(transport.requests, hasLength(1));

        transport.failure = null;
        transport.pending = Completer<ApiTransportResponse>();
        client.close();
        client = ApiClient(
          config: ApiConfig.fromBaseUrl('https://api.example.test/api/v1'),
          transport: transport,
          timeout: const Duration(milliseconds: 5),
        );
        await expectLater(
          ReadingRepository(client: client, session: session).submit(request),
          throwsA(
            isA<ApiException>().having(
              (error) => error.type,
              'type',
              ApiExceptionType.timeout,
            ),
          ),
        );
        expect(transport.requests, hasLength(2));
      },
    );
  });
}
