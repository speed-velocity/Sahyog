import 'dart:convert';

import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/models/auth_models.dart';
import 'package:sahyog_mobile/core/api/models/demo_models.dart';
import 'package:sahyog_mobile/core/api/models/incident_models.dart';
import 'package:sahyog_mobile/core/api/models/reading_models.dart';
import 'package:sahyog_mobile/core/api/models/verification_model.dart';

void main() {
  group('API wire models', () {
    test('round-trips registration and login responses', () {
      final registrationJson = <String, dynamic>{
        'user_id': 'user-uuid',
        'role': 'SUBJECT',
      };
      final registration = RegistrationResponse.fromJson(registrationJson);
      expect(registration.userId, 'user-uuid');
      expect(registration.toJson(), registrationJson);

      final tokenJson = <String, dynamic>{
        'access_token': 'jwt-value',
        'token_type': 'bearer',
      };
      final token = LoginTokenResponse.fromJson(tokenJson);
      expect(token.accessToken, 'jwt-value');
      expect(token.toJson(), tokenJson);
    });

    test('serializes demo creation idempotency and parses response/reset', () {
      final request = DemoRunCreateRequest(
        scenario: 'FALSE_ALARM',
        startIdempotencyKey: 'run-key-1',
      );
      expect(request.toJson(), {
        'scenario': 'FALSE_ALARM',
        'start_idempotency_key': 'run-key-1',
      });

      final responseJson = <String, dynamic>{
        'demo_run_id': 'run-uuid',
        'subject_user_id': 'subject-uuid',
        'scenario': 'FALSE_ALARM',
        'status': 'RUNNING',
        'outcome': null,
        'current_generation': 1,
        'started_at': '2026-11-28T10:00:00Z',
        'completed_at': null,
        'reset_at': null,
      };
      final response = DemoRunResponse.fromJson(responseJson);
      final resetResponse = DemoRunResetResponse.fromJson(responseJson);
      expect(response.scenario, 'FALSE_ALARM');
      expect(response.currentGeneration, 1);
      expect(response.startedAt.isUtc, isTrue);
      expect(resetResponse.demoRunId, 'run-uuid');
      final roundTrip = DemoRunResponse.fromJson(response.toJson());
      expect(roundTrip.startedAt, response.startedAt);
      expect(roundTrip.scenario, response.scenario);
    });

    test('serializes the exact simulated-reading fields and UTC timestamp', () {
      final request = ReadingSubmissionRequest(
        demoRunId: 'run-uuid',
        heartRateBpm: 72,
        observedAt: DateTime(2026, 11, 28, 10),
        activityContext: 'RESTING',
        sourceRecordId: 'sample-1',
        ingestionIdempotencyKey: 'reading-key-1',
      );
      final wire = request.toJson();

      expect(wire.keys.toSet(), {
        'demo_run_id',
        'source_kind',
        'heart_rate_bpm',
        'observed_at',
        'activity_context',
        'source_record_id',
        'ingestion_idempotency_key',
      });
      expect(wire['source_kind'], 'SIMULATED');
      expect(wire['ingestion_idempotency_key'], 'reading-key-1');
      expect((wire['observed_at'] as String).endsWith('Z'), isTrue);

      final responseJson = <String, dynamic>{
        'reading_id': 'reading-uuid',
        'demo_run_id': 'run-uuid',
        'accepted': true,
        'detection_status': 'NORMAL',
        'anomaly_event_id': null,
        'incident_id': null,
      };
      final response = ReadingSubmissionResponse.fromJson(
        jsonDecode(jsonEncode(responseJson)) as Map<String, dynamic>,
      );
      expect(response.toJson(), responseJson);
    });

    test(
      'reconstructs an identical reading retry and parses replayed results',
      () {
        ReadingSubmissionRequest request() => ReadingSubmissionRequest(
          demoRunId: 'run-uuid',
          heartRateBpm: 164,
          observedAt: DateTime.utc(2026, 11, 28, 10),
          activityContext: 'WALKING',
          sourceRecordId: 'sample-1',
          ingestionIdempotencyKey: 'reading-key-1',
        );

        final firstPayload = request().toJson();
        final retryPayload = request().toJson();
        expect(retryPayload, firstPayload);

        final replayJson = <String, dynamic>{
          'reading_id': 'reading-uuid',
          'demo_run_id': 'run-uuid',
          'accepted': true,
          'detection_status': 'ANOMALY_DETECTED',
          'anomaly_event_id': 'event-uuid',
          'incident_id': 'incident-uuid',
        };
        final firstResponse = ReadingSubmissionResponse.fromJson(replayJson);
        final replayResponse = ReadingSubmissionResponse.fromJson(replayJson);

        expect(replayResponse.toJson(), firstResponse.toJson());
        expect(replayResponse.anomalyEventId, 'event-uuid');
        expect(replayResponse.incidentId, 'incident-uuid');
      },
    );

    test('rejects unsupported reading source and invalid idempotency keys', () {
      expect(
        () => ReadingSubmissionRequest(
          demoRunId: 'run-uuid',
          sourceKind: 'DEVICE',
          heartRateBpm: 72,
          observedAt: DateTime.now(),
          ingestionIdempotencyKey: 'key',
        ),
        throwsArgumentError,
      );
      expect(
        () => ReadingSubmissionRequest(
          demoRunId: 'run-uuid',
          heartRateBpm: 72,
          observedAt: DateTime.now(),
          ingestionIdempotencyKey: '',
        ),
        throwsArgumentError,
      );
      expect(
        () => DemoRunCreateRequest(
          scenario: 'UNKNOWN',
          startIdempotencyKey: 'key',
        ),
        throwsArgumentError,
      );
    });

    test('parses an incident and the backend incident-list array', () {
      final incidentJson = <String, dynamic>{
        'incident_id': 'incident-uuid',
        'subject_user_id': 'subject-uuid',
        'demo_run_id': 'run-uuid',
        'run_generation': 1,
        'status': 'PENDING_VERIFICATION',
        'created_at': '2026-11-28T10:00:00Z',
        'updated_at': '2026-11-28T10:00:00Z',
        'verification_deadline_at': '2026-11-28T10:00:15Z',
        'resolved_at': null,
      };

      final incident = IncidentResponse.fromJson(incidentJson);
      final list = IncidentListResponse.fromJson([incidentJson]);
      expect(incident.status, 'PENDING_VERIFICATION');
      expect(list.incidents, hasLength(1));
      final roundTrip = IncidentListResponse.fromJson(list.toJson());
      expect(roundTrip.incidents.single.status, incident.status);
      expect(roundTrip.incidents.single.createdAt, incident.createdAt);
    });

    test(
      'serializes verification with the required response and idempotency',
      () {
        final request = VerificationRequest(
          idempotencyKey: 'verification-key-1',
          requestReference: 'ui-request-1',
        );

        expect(request.toJson(), {
          'response': 'I_AM_OK',
          'idempotency_key': 'verification-key-1',
          'request_reference': 'ui-request-1',
        });
        expect(
          const VerificationRequest(idempotencyKey: 'verification-key-2')
              .toJson(),
          {'response': 'I_AM_OK', 'idempotency_key': 'verification-key-2'},
        );
      },
    );
  });
}
