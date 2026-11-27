import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'api_config.dart';
import 'api_exception.dart';

class ApiTransportResponse {
  const ApiTransportResponse({required this.statusCode, required this.body});

  final int statusCode;
  final String body;
}

/// Injectable boundary used by [ApiClient] and its unit tests.
abstract interface class ApiTransport {
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  });

  void close();
}

class IoApiTransport implements ApiTransport {
  IoApiTransport({required Duration connectionTimeout})
    : _httpClient = HttpClient()..connectionTimeout = connectionTimeout;

  final HttpClient _httpClient;

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) async {
    final request = await _httpClient.openUrl(method, uri);
    headers.forEach((name, value) => request.headers.set(name, value));
    if (bodyBytes.isNotEmpty) {
      request.add(bodyBytes);
    }

    final response = await request.close();
    final responseBody = await response.transform(utf8.decoder).join();
    return ApiTransportResponse(
      statusCode: response.statusCode,
      body: responseBody,
    );
  }

  @override
  void close() => _httpClient.close(force: true);
}

/// Small JSON/form HTTP client for the versioned Sahyog backend API.
///
/// Paths are resolved relative to the API root in [ApiConfig]. Route ownership
/// and route strings remain with the caller; this client does not invent them.
class ApiClient {
  ApiClient({
    required this.config,
    ApiTransport? transport,
    this.timeout = const Duration(seconds: 10),
  }) : _transport = transport ?? IoApiTransport(connectionTimeout: timeout) {
    if (timeout <= Duration.zero) {
      throw ArgumentError.value(timeout, 'timeout', 'Must be positive.');
    }
  }

  final ApiConfig config;
  final Duration timeout;
  final ApiTransport _transport;

  Future<Object?> get(String path, {String? bearerToken}) {
    return _send(method: 'GET', path: path, bearerToken: bearerToken);
  }

  Future<Object?> postJson(
    String path, {
    required Object? body,
    String? bearerToken,
  }) {
    return _send(
      method: 'POST',
      path: path,
      bearerToken: bearerToken,
      bodyBytes: utf8.encode(jsonEncode(body)),
      contentType: 'application/json; charset=utf-8',
    );
  }

  /// Sends a POST with no request body, for endpoints such as demo reset.
  Future<Object?> postEmpty(String path, {String? bearerToken}) {
    return _send(method: 'POST', path: path, bearerToken: bearerToken);
  }

  /// Sends form fields such as the OAuth2 password-token request.
  Future<Object?> postForm(
    String path, {
    required Map<String, String> fields,
    String? bearerToken,
  }) {
    final encodedForm = Uri(queryParameters: fields).query;
    return _send(
      method: 'POST',
      path: path,
      bearerToken: bearerToken,
      bodyBytes: utf8.encode(encodedForm),
      contentType: 'application/x-www-form-urlencoded; charset=utf-8',
    );
  }

  Future<Object?> _send({
    required String method,
    required String path,
    String? bearerToken,
    List<int> bodyBytes = const [],
    String? contentType,
  }) async {
    final headers = <String, String>{'Accept': 'application/json'};
    if (contentType != null) {
      headers['Content-Type'] = contentType;
    }
    final normalizedToken = bearerToken?.trim();
    if (normalizedToken != null && normalizedToken.isNotEmpty) {
      headers['Authorization'] = 'Bearer $normalizedToken';
    }

    final ApiTransportResponse response;
    try {
      response = await _transport
          .send(
            method: method,
            uri: config.endpoint(path),
            headers: headers,
            bodyBytes: bodyBytes,
          )
          .timeout(timeout);
    } on TimeoutException {
      throw const ApiException(
        type: ApiExceptionType.timeout,
        message: 'The backend request timed out.',
      );
    } on IOException {
      throw const ApiException(
        type: ApiExceptionType.network,
        message:
            'Could not connect to the backend. Check the network and API URL.',
      );
    } on FormatException {
      throw const ApiException(
        type: ApiExceptionType.invalidResponse,
        message: 'The backend response could not be decoded.',
      );
    }

    final decoded = _decodeBody(response.body, statusCode: response.statusCode);
    if (response.statusCode < 200 || response.statusCode >= 300) {
      throw _exceptionForResponse(
        statusCode: response.statusCode,
        body: decoded,
      );
    }
    return decoded;
  }

  Object? _decodeBody(String body, {required int statusCode}) {
    if (body.trim().isEmpty) return null;
    try {
      return jsonDecode(body);
    } on FormatException {
      if (statusCode >= 200 && statusCode < 300) {
        throw const ApiException(
          type: ApiExceptionType.invalidResponse,
          message: 'The backend returned a response that was not valid JSON.',
        );
      }
      return body;
    }
  }

  ApiException _exceptionForResponse({
    required int statusCode,
    required Object? body,
  }) {
    final type = switch (statusCode) {
      401 => ApiExceptionType.unauthorized,
      403 => ApiExceptionType.forbidden,
      404 => ApiExceptionType.notFound,
      400 || 422 => ApiExceptionType.validation,
      409 => ApiExceptionType.conflict,
      >= 500 => ApiExceptionType.server,
      _ => ApiExceptionType.http,
    };
    return ApiException(
      type: type,
      statusCode: statusCode,
      message: _messageFrom(body, statusCode),
      details: body,
    );
  }

  String _messageFrom(Object? body, int statusCode) {
    if (body is Map<String, dynamic>) {
      final detail = body['detail'];
      if (detail is String && detail.trim().isNotEmpty) return detail.trim();
      if (detail is List) {
        final messages = detail
            .whereType<Map>()
            .map((item) => item['msg'])
            .whereType<String>()
            .where((message) => message.isNotEmpty)
            .toList();
        if (messages.isNotEmpty) return messages.join('; ');
        return 'The request did not pass backend validation.';
      }
      final error = body['error'];
      if (error is Map && error['message'] is String) {
        return (error['message'] as String).trim();
      }
    }
    return 'The backend returned an error (HTTP $statusCode).';
  }

  void close() => _transport.close();
}
