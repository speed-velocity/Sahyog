import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/ml/backend_detection_result.dart';

void main() {
  group('BackendDetectionResult', () {
    const normalResponse = {
      'accepted': true,
      'detection_status': 'NORMAL',
      'reading_id': 'reading_001',
      'demo_run_id': 'run_001',
      'anomaly_event_id': null,
      'incident_id': null,
    };

    const anomalyResponse = {
      'accepted': true,
      'detection_status': 'ANOMALY_DETECTED',
      'reading_id': 'reading_002',
      'demo_run_id': 'run_002',
      'anomaly_event_id': 'event_001',
      'incident_id': 'incident_001',
    };

    const malformedResponse = {
      'accepted': true,
      // missing detection_status
    };

    test('parse NORMAL response', () {
      final result = BackendDetectionResult.fromJson(normalResponse);
      expect(result, isNotNull);
      final parsed = result!;
      expect(parsed.accepted, isTrue);
      expect(parsed.detectionStatus, equals('NORMAL'));
      expect(parsed.readingId, equals('reading_001'));
      expect(parsed.demoRunId, equals('run_001'));
      expect(parsed.anomalyEventId, isNull);
      expect(parsed.incidentId, isNull);
    });

    test('parse ANOMALY_DETECTED response', () {
      final result = BackendDetectionResult.fromJson(anomalyResponse);
      expect(result, isNotNull);
      final parsed = result!;
      expect(parsed.accepted, isTrue);
      expect(parsed.detectionStatus, equals('ANOMALY_DETECTED'));
      expect(parsed.readingId, equals('reading_002'));
      expect(parsed.demoRunId, equals('run_002'));
      expect(parsed.anomalyEventId, equals('event_001'));
      expect(parsed.incidentId, equals('incident_001'));
    });

    test('handle missing required fields returns null', () {
      final result = BackendDetectionResult.fromJson(malformedResponse);
      expect(result, isNull);
    });

    test('handle null values gracefully', () {
      final responseWithNulls = {
        'accepted': true,
        'detection_status': 'NORMAL',
        'reading_id': null,
        'demo_run_id': null,
        'anomaly_event_id': null,
        'incident_id': null,
      };
      final result = BackendDetectionResult.fromJson(responseWithNulls);
      expect(result, isNotNull);
      final parsed = result!;
      expect(parsed.readingId, isNull);
      expect(parsed.demoRunId, isNull);
      expect(parsed.anomalyEventId, isNull);
      expect(parsed.incidentId, isNull);
    });

    test('malformed detection_status is accepted but noted as unknown', () {
      // Response with unexpected detection_status value
      final response = {
        'accepted': true,
        'detection_status': 'UNKNOWN',
        'reading_id': null,
        'demo_run_id': null,
        'anomaly_event_id': null,
        'incident_id': null,
      };
      final result = BackendDetectionResult.fromJson(response);
      expect(result, isNotNull);
      final parsed = result!;
      expect(parsed.detectionStatus, equals('UNKNOWN'));
    });

    test('toJson round-trip', () {
      final original = BackendDetectionResult.fromJson(normalResponse);
      final json = original!.toJson();
      expect(json['accepted'], isTrue);
      expect(json['detection_status'], equals('NORMAL'));
      expect(json['reading_id'], equals('reading_001'));
      expect(json['demo_run_id'], equals('run_001'));
    });

    test('equality and hashCode consistency', () {
      final a = BackendDetectionResult.fromJson(normalResponse)!;
      final b = BackendDetectionResult.fromJson(normalResponse)!;
      expect(a, equals(b));
      expect(a.hashCode, equals(b.hashCode));
    });
  });
}
