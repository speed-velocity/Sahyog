import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/reading_models.dart';

class ReadingRepository {
  ReadingRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  /// Re-submit the same immutable request to retry a logical reading.
  /// This method does not generate keys or automatically retry requests.
  Future<ReadingSubmissionResponse> submit(
    ReadingSubmissionRequest request,
  ) async {
    final response = await client.postJson(
      'readings',
      body: request.toJson(),
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(
      response,
      'reading submission',
      ReadingSubmissionResponse.fromJson,
    );
  }
}
