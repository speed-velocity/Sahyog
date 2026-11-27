import 'api_exception.dart';

/// Holds authentication state for the lifetime of the Flutter process only.
class ApiSession {
  String? _accessToken;

  bool get isAuthenticated => _accessToken != null;

  String requireAccessToken() {
    final token = _accessToken;
    if (token == null || token.isEmpty) {
      throw const ApiException(
        type: ApiExceptionType.unauthorized,
        message: 'Sign in before requesting protected Sahyog data.',
      );
    }
    return token;
  }

  void setAccessToken(String token) {
    final normalized = token.trim();
    if (normalized.isEmpty) {
      throw ArgumentError.value(
        token,
        'token',
        'Access token cannot be empty.',
      );
    }
    _accessToken = normalized;
  }

  void clear() => _accessToken = null;
}
