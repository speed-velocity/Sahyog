import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/dashboard_models.dart';

class DashboardRepository {
  DashboardRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<DashboardOverviewResponse> getOverview({String? subjectUserId}) async {
    final query = subjectUserId == null
        ? ''
        : '?${Uri(queryParameters: {'subject_user_id': subjectUserId}).query}';
    final response = await client.get(
      'dashboard/overview$query',
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(
      response,
      'dashboard overview',
      DashboardOverviewResponse.fromJson,
    );
  }
}
