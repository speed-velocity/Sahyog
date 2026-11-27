import '../api_client.dart';
import '../api_exception.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/incident_models.dart';

class IncidentRepository {
  IncidentRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<IncidentListResponse> list({
    String? subjectUserId,
    String? statusFilter,
    int limit = 50,
  }) async {
    if (limit < 1 || limit > 100) {
      throw ArgumentError.value(limit, 'limit', 'Must be between 1 and 100.');
    }
    final query = <String, String>{'limit': '$limit'};
    if (subjectUserId != null) query['subject_user_id'] = subjectUserId;
    if (statusFilter != null) query['status_filter'] = statusFilter;
    final response = await client.get(
      'incidents?${Uri(queryParameters: query).query}',
      bearerToken: session.requireAccessToken(),
    );
    try {
      return IncidentListResponse.fromJson(response);
    } on FormatException catch (error) {
      throw ApiException(
        type: ApiExceptionType.invalidResponse,
        message: 'The backend incident list response is missing valid fields.',
        details: error.message,
      );
    }
  }

  Future<IncidentResponse> get(String incidentId) async {
    final response = await client.get(
      'incidents/${Uri.encodeComponent(incidentId)}',
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(response, 'incident', IncidentResponse.fromJson);
  }
}
