import '../api_client.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/authorization_models.dart';

class AuthorizationRepository {
  AuthorizationRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<AuthorizedSubjectsResponse> listMySubjects() async {
    final response = await client.get(
      'authorizations/me',
      bearerToken: session.requireAccessToken(),
    );
    return parseApiObject(
      response,
      'authorized subjects',
      AuthorizedSubjectsResponse.fromJson,
    );
  }
}
