import 'json_helpers.dart';

const demoScenarioValues = {'NORMAL', 'TRUE_ANOMALY', 'FALSE_ALARM'};

class DemoRunCreateRequest {
  DemoRunCreateRequest({
    required this.scenario,
    required this.startIdempotencyKey,
  }) {
    if (!demoScenarioValues.contains(scenario)) {
      throw ArgumentError.value(scenario, 'scenario', 'Unknown demo scenario.');
    }
    if (startIdempotencyKey.isEmpty || startIdempotencyKey.length > 256) {
      throw ArgumentError.value(
        startIdempotencyKey,
        'startIdempotencyKey',
        'Must contain 1 to 256 characters.',
      );
    }
  }

  final String scenario;
  final String startIdempotencyKey;

  Map<String, dynamic> toJson() => {
    'scenario': scenario,
    'start_idempotency_key': startIdempotencyKey,
  };
}

class DemoRunResponse {
  const DemoRunResponse({
    required this.demoRunId,
    required this.subjectUserId,
    required this.scenario,
    required this.status,
    required this.outcome,
    required this.currentGeneration,
    required this.startedAt,
    required this.completedAt,
    required this.resetAt,
  });

  final String demoRunId;
  final String subjectUserId;
  final String scenario;
  final String status;
  final String? outcome;
  final int currentGeneration;
  final DateTime startedAt;
  final DateTime? completedAt;
  final DateTime? resetAt;

  factory DemoRunResponse.fromJson(Map<String, dynamic> json) {
    return DemoRunResponse(
      demoRunId: requiredString(json, 'demo_run_id'),
      subjectUserId: requiredString(json, 'subject_user_id'),
      scenario: requiredString(json, 'scenario'),
      status: requiredString(json, 'status'),
      outcome: optionalString(json, 'outcome'),
      currentGeneration: requiredInt(json, 'current_generation'),
      startedAt: requiredDateTime(json, 'started_at'),
      completedAt: optionalDateTime(json, 'completed_at'),
      resetAt: optionalDateTime(json, 'reset_at'),
    );
  }

  Map<String, dynamic> toJson() => {
    'demo_run_id': demoRunId,
    'subject_user_id': subjectUserId,
    'scenario': scenario,
    'status': status,
    'outcome': outcome,
    'current_generation': currentGeneration,
    'started_at': startedAt.toIso8601String(),
    'completed_at': completedAt?.toIso8601String(),
    'reset_at': resetAt?.toIso8601String(),
  };
}

/// Reset returns the same response schema as demo-run creation/status.
typedef DemoRunResetResponse = DemoRunResponse;
