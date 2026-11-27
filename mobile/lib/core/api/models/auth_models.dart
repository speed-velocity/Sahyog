import 'json_helpers.dart';

class RegistrationRequest {
  const RegistrationRequest({
    required this.loginIdentifier,
    required this.password,
    required this.role,
  });

  final String loginIdentifier;
  final String password;
  final String role;

  Map<String, dynamic> toJson() => {
    'login_identifier': loginIdentifier,
    'password': password,
    'role': role,
  };
}

class RegistrationResponse {
  const RegistrationResponse({required this.userId, required this.role});

  final String userId;
  final String role;

  factory RegistrationResponse.fromJson(Map<String, dynamic> json) {
    return RegistrationResponse(
      userId: requiredString(json, 'user_id'),
      role: requiredString(json, 'role'),
    );
  }

  Map<String, dynamic> toJson() => {'user_id': userId, 'role': role};
}

class LoginTokenResponse {
  const LoginTokenResponse({
    required this.accessToken,
    required this.tokenType,
  });

  final String accessToken;
  final String tokenType;

  factory LoginTokenResponse.fromJson(Map<String, dynamic> json) {
    return LoginTokenResponse(
      accessToken: requiredString(json, 'access_token'),
      tokenType: requiredString(json, 'token_type'),
    );
  }

  Map<String, dynamic> toJson() => {
    'access_token': accessToken,
    'token_type': tokenType,
  };
}
