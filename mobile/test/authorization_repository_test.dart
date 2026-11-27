import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_session.dart';
import 'package:sahyog_mobile/core/api/repositories/authorization_repository.dart';

class _MockTransport implements ApiTransport {
  final responses = <ApiTransportResponse>[];
  final requests = <Uri>[];

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) {
    requests.add(uri);
    return Future.value(responses.removeAt(0));
  }

  @override
  void close() {}
}

const _authJson = '''
{
  "authorized_subjects": [
    {
      "subject_user_id": "subject-uuid-999",
      "granted_at": "2026-11-28T09:00:00Z",
      "revoked_at": null
    }
  ]
}
''';

void main() {
  test('AuthorizationRepository parses authorized subjects response', () async {
    final transport = _MockTransport()
      ..responses.add(
        const ApiTransportResponse(statusCode: 200, body: _authJson),
      );
    final client = ApiClient(
      config: ApiConfig.fromBaseUrl('https://example.test/api/v1'),
      transport: transport,
    );
    final session = ApiSession()..setAccessToken('valid-token');
    final repo = AuthorizationRepository(client: client, session: session);

    final result = await repo.listMySubjects();

    expect(result.authorizedSubjects.length, 1);
    expect(result.authorizedSubjects.first.subjectUserId, 'subject-uuid-999');
    expect(result.authorizedSubjects.first.revokedAt, isNull);
  });
}
