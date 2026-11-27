import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/demo_models.dart';

class DemoRepository {
  DemoRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<DemoRunResponse> start(DemoRunCreateRequest request) async {
    final response = await client.postJson(
      'demo/runs',
      body: request.toJson(),
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(response, 'demo run', DemoRunResponse.fromJson);
  }

  Future<DemoRunResponse> get(String demoRunId) async {
    final response = await client.get(
      'demo/runs/${Uri.encodeComponent(demoRunId)}',
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(response, 'demo run', DemoRunResponse.fromJson);
  }

  Future<DemoRunResetResponse> reset(String demoRunId) async {
    final response = await client.postEmpty(
      'demo/runs/${Uri.encodeComponent(demoRunId)}/reset',
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(response, 'demo reset', DemoRunResponse.fromJson);
  }
}
