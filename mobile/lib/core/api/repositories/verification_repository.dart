import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/incident_models.dart';
import '../models/verification_model.dart';

class VerificationRepository {
  VerificationRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  /// Call again with the same request and key only to retry that same action.
  /// The repository never creates keys or retries automatically.
  Future<IncidentResponse> submit({
    required String incidentId,
    required VerificationRequest request,
  }) async {
    if (request.idempotencyKey.trim().isEmpty) {
      throw ArgumentError.value(
        request.idempotencyKey,
        'idempotencyKey',
        'An idempotency key is required.',
      );
    }
    final response = await client.postJson(
      'incidents/${Uri.encodeComponent(incidentId)}/verification',
      body: request.toJson(),
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(response, 'verification', IncidentResponse.fromJson);
  }
}
