import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_session.dart';
import 'package:sahyog_mobile/core/api/repositories/authentication_repository.dart';
import 'package:sahyog_mobile/features/auth/presentation/auth_screen.dart';

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

void main() {
  late _MockTransport transport;
  late ApiClient client;
  late ApiSession session;
  late AuthenticationRepository authRepo;

  setUp(() {
    transport = _MockTransport();
    client = ApiClient(
      config: ApiConfig.fromBaseUrl('https://example.test/api/v1'),
      transport: transport,
    );
    session = ApiSession();
    authRepo = AuthenticationRepository(client: client, session: session);
  });

  testWidgets('validates required fields on sign in', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: AuthScreen(authRepository: authRepo, session: session),
      ),
    );

    await tester.tap(find.widgetWithText(FilledButton, 'Sign In'));
    await tester.pumpAndSettle();

    expect(find.text('Please enter your username'), findsOneWidget);
    expect(find.text('Please enter your password'), findsOneWidget);
  });

  testWidgets('successful sign in sets token in ApiSession', (tester) async {
    transport.responses.add(
      const ApiTransportResponse(
        statusCode: 200,
        body: '{"access_token":"token-abc","token_type":"bearer"}',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: AuthScreen(authRepository: authRepo, session: session),
      ),
    );

    await tester.enterText(find.byType(TextFormField).first, 'caregiver1');
    await tester.enterText(find.byType(TextFormField).last, 'secret123');
    await tester.tap(find.widgetWithText(FilledButton, 'Sign In'));
    await tester.pumpAndSettle();

    expect(session.isAuthenticated, isTrue);
    expect(session.requireAccessToken(), 'token-abc');
  });

  testWidgets('renders active session view when authenticated', (tester) async {
    session.setAccessToken('existing-token');

    await tester.pumpWidget(
      MaterialApp(
        home: AuthScreen(authRepository: authRepo, session: session),
      ),
    );

    expect(find.text('Active Session Authenticated'), findsOneWidget);
    expect(find.text('Sign Out'), findsOneWidget);

    await tester.tap(find.text('Sign Out'));
    await tester.pumpAndSettle();

    expect(session.isAuthenticated, isFalse);
  });
}
