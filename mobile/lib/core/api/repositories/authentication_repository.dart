import '../api_client.dart';
import '../api_exception.dart';
import '../api_response_parser.dart';
import '../api_session.dart';
import '../models/auth_models.dart';

class AuthenticationRepository {
  AuthenticationRepository({required this.client, required this.session});

  final ApiClient client;
  final ApiSession session;

  Future<RegistrationResponse> register(RegistrationRequest request) async {
    final response = await client.postJson(
      'auth/register',
      body: request.toJson(),
    );
    return parseApiObject(
      response,
      'registration',
      RegistrationResponse.fromJson,
    );
  }

  Future<LoginTokenResponse> login({
    required String username,
    required String password,
  }) async {
    final response = await client.postForm(
      'auth/token',
      fields: {'username': username, 'password': password},
    );
    final token = parseApiObject(
      response,
      'login',
      LoginTokenResponse.fromJson,
    );
    if (token.tokenType.toLowerCase() != 'bearer') {
      throw const ApiException(
        type: ApiExceptionType.invalidResponse,
        message: 'The backend returned an unsupported token type.',
      );
    }
    session.setAccessToken(token.accessToken);
    return token;
  }

  void logout() => session.clear();
}
