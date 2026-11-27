import 'api_exception.dart';

/// Backend API root supplied at build/run time, including `/api/v1`.
///
/// Configure with:
/// `--dart-define=SAHYOG_API_BASE_URL=https://<backend-host>/api/v1`
///
/// For local development, supply the reachable development backend URL as the
/// same define. No host is assumed by the application.
class ApiConfig {
  ApiConfig._(this.baseUri);

  factory ApiConfig.fromBaseUrl(String value) {
    final raw = value.trim();
    if (raw.isEmpty) {
      throw const ApiException(
        type: ApiExceptionType.configuration,
        message: 'Set SAHYOG_API_BASE_URL to the backend API root.',
      );
    }

    final Uri parsed;
    try {
      parsed = Uri.parse(raw);
    } on FormatException {
      throw const ApiException(
        type: ApiExceptionType.configuration,
        message: 'SAHYOG_API_BASE_URL is not a valid URL.',
      );
    }

    if (!parsed.isAbsolute ||
        parsed.host.isEmpty ||
        !const {'http', 'https'}.contains(parsed.scheme) ||
        parsed.userInfo.isNotEmpty ||
        parsed.hasQuery ||
        parsed.hasFragment) {
      throw const ApiException(
        type: ApiExceptionType.configuration,
        message: 'SAHYOG_API_BASE_URL must be an absolute HTTP or HTTPS API root without credentials, query, or fragment.',
      );
    }

    final normalizedPath = parsed.path.replaceFirst(RegExp(r'/+$'), '');
    return ApiConfig._(parsed.replace(path: '$normalizedPath/'));
  }

  factory ApiConfig.fromEnvironment({String? value}) {
    final configured =
        value ??
        const String.fromEnvironment('SAHYOG_API_BASE_URL', defaultValue: '');
    return ApiConfig.fromBaseUrl(configured);
  }

  /// The normalized API root, for example `https://host/api/v1/`.
  final Uri baseUri;

  String get baseUrl => baseUri.toString().replaceFirst(RegExp(r'/+$'), '');

  /// Resolves a route relative to the configured API root.
  Uri endpoint(String path) {
    final candidate = Uri.parse(path);
    if (candidate.hasScheme || candidate.hasAuthority) {
      throw ArgumentError.value(path, 'path', 'Expected a relative API path.');
    }
    final relativePath = path.startsWith('/') ? path.substring(1) : path;
    return baseUri.resolve(relativePath);
  }
}
