import 'dart:async';
import 'dart:convert';
import 'dart:io';

import 'location_models.dart';
import 'location_reporter.dart';

class HttpLocationUpdateSender implements LocationUpdateSender {
  HttpLocationUpdateSender({
    required this.baseUri,
    this.timeout = const Duration(seconds: 10),
  }) : _endpoint = _endpointFor(baseUri) {
    if (baseUri.scheme != 'http' && baseUri.scheme != 'https') {
      throw ArgumentError.value(
        baseUri,
        'baseUri',
        'must use the http or https scheme',
      );
    }
    if (baseUri.hasQuery || baseUri.hasFragment) {
      throw ArgumentError.value(
        baseUri,
        'baseUri',
        'must not contain a query or fragment',
      );
    }
  }

  final Uri baseUri;
  final Duration timeout;
  final Uri _endpoint;

  static Uri _endpointFor(Uri baseUri) {
    final path = baseUri.path.endsWith('/') ? baseUri.path : '${baseUri.path}/';
    return baseUri.replace(path: path).resolve('location/updates');
  }

  @override
  Future<LocationSnapshot> send(LocationUpdatePayload payload) async {
    final client = HttpClient()..connectionTimeout = timeout;

    try {
      final request = await client.postUrl(_endpoint).timeout(timeout);
      request.headers.contentType = ContentType.json;
      request.headers.set(HttpHeaders.acceptHeader, 'application/json');
      request.add(utf8.encode(jsonEncode(payload.toJson())));

      final response = await request.close().timeout(timeout);
      final responseBody = await _readBody(response).timeout(timeout);

      if (response.statusCode < 200 || response.statusCode >= 300) {
        final message =
            _extractMessage(responseBody) ??
            'The location service rejected the update '
                '(HTTP ${response.statusCode}).';
        throw LocationTransportException(
          LocationFailureCode.httpError,
          message,
          statusCode: response.statusCode,
        );
      }

      final decoded = jsonDecode(responseBody);
      if (decoded is! Map<String, dynamic>) {
        throw const LocationTransportException(
          LocationFailureCode.invalidResponse,
          'The location service returned an unreadable response.',
        );
      }

      return LocationSnapshot.fromJson(decoded);
    } on TimeoutException {
      throw const LocationTransportException(
        LocationFailureCode.timeout,
        'The location update timed out.',
      );
    } on SocketException {
      throw const LocationTransportException(
        LocationFailureCode.networkError,
        'The location service could not be reached.',
      );
    } on HttpException {
      throw const LocationTransportException(
        LocationFailureCode.networkError,
        'The location connection failed.',
      );
    } on FormatException {
      throw const LocationTransportException(
        LocationFailureCode.invalidResponse,
        'The location service returned an unreadable response.',
      );
    } finally {
      client.close(force: true);
    }
  }

  Future<String> _readBody(HttpClientResponse response) async {
    final bytes = <int>[];

    await for (final chunk in response) {
      bytes.addAll(chunk);
      if (bytes.length > 64 * 1024) {
        throw const LocationTransportException(
          LocationFailureCode.invalidResponse,
          'The location service response was too large.',
        );
      }
    }

    return utf8.decode(bytes);
  }

  String? _extractMessage(String body) {
    try {
      final decoded = jsonDecode(body);
      if (decoded is Map) {
        final error = decoded['error'];
        if (error is Map) {
          final message = error['message'];
          if (message is String && message.trim().isNotEmpty) {
            return _truncate(message.trim());
          }
        }
        final detail = decoded['detail'];
        if (detail is String && detail.trim().isNotEmpty) {
          return _truncate(detail.trim());
        }
      }
    } on FormatException {
      return null;
    }
    return null;
  }

  String _truncate(String value) {
    return value.length <= 300 ? value : '${value.substring(0, 300)}...';
  }
}
