import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_exception.dart';

void main() {
  group('ApiConfig', () {
    test('normalizes an explicitly supplied development API root', () {
      final config = ApiConfig.fromBaseUrl('http://10.0.2.2:8000/api/v1/');

      expect(config.baseUrl, 'http://10.0.2.2:8000/api/v1');
      expect(
        config.endpoint('auth/token').toString(),
        'http://10.0.2.2:8000/api/v1/auth/token',
      );
    });

    test('accepts a build-time configuration value', () {
      final config = ApiConfig.fromEnvironment(
        value: 'https://backend.example.test/api/v1',
      );

      expect(config.endpoint('/incidents').path, '/api/v1/incidents');
    });

    test('requires an explicit API URL and rejects invalid roots', () {
      expect(
        () => ApiConfig.fromEnvironment(value: ''),
        throwsA(
          isA<ApiException>().having(
            (error) => error.type,
            'type',
            ApiExceptionType.configuration,
          ),
        ),
      );
      expect(
        () => ApiConfig.fromBaseUrl('ftp://backend.example.test/api/v1'),
        throwsA(isA<ApiException>()),
      );
      expect(
        () => ApiConfig.fromBaseUrl('https://backend.example.test/api/v1?x=1'),
        throwsA(isA<ApiException>()),
      );
    });
  });
}
