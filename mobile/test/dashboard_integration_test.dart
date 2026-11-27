import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/app/sahyog_app.dart';
import 'package:sahyog_mobile/core/api/api_client.dart';
import 'package:sahyog_mobile/core/api/api_config.dart';
import 'package:sahyog_mobile/core/api/api_session.dart';
import 'package:sahyog_mobile/core/api/repositories/dashboard_repository.dart';

class _MockTransport implements ApiTransport {
  final List<ApiTransportResponse> responses = [];
  final requests = <Uri>[];
  Completer<ApiTransportResponse>? pending;

  @override
  Future<ApiTransportResponse> send({
    required String method,
    required Uri uri,
    required Map<String, String> headers,
    required List<int> bodyBytes,
  }) {
    requests.add(uri);
    if (pending != null) return pending!.future;
    if (responses.isNotEmpty) return Future.value(responses.removeAt(0));
    return Future.value(
      const ApiTransportResponse(statusCode: 200, body: '{}'),
    );
  }

  @override
  void close() {}
}

const _dashboardWithIncident = '''
{"subject_user_id":"subject-123","monitoring_status":"INCIDENT_ACTIVE",
"latest_reading":{"reading_id":"reading-1","heart_rate_bpm":86,
"observed_at":"2026-11-28T10:00:00Z","source_kind":"SIMULATED"},
"active_incident":"incident-456","incident_status":"PENDING_VERIFICATION",
"latest_update_at":"2026-11-28T10:00:01Z"}
''';

const _dashboardWithoutOptionalData = '''
{"subject_user_id":"subject-123","monitoring_status":"NORMAL",
"latest_reading":null,"active_incident":null,"incident_status":null,
"latest_update_at":null}
''';

void main() {
  late _MockTransport transport;
  late ApiClient client;
  late ApiSession session;

  setUp(() {
    transport = _MockTransport();
    client = ApiClient(
      config: ApiConfig.fromBaseUrl('https://backend.example.test/api/v1'),
      transport: transport,
      timeout: const Duration(minutes: 1),
    );
    session = ApiSession()..setAccessToken('in-memory-test-token');
  });

  Future<void> pumpIntegratedApp(WidgetTester tester) async {
    await tester.pumpWidget(
      SahyogApp(
        apiSession: session,
        dashboardRepository: DashboardRepository(
          client: client,
          session: session,
        ),
      ),
    );
  }

  Future<void> scrollToScenario(WidgetTester tester) async {
    final scrollable = find.byType(Scrollable).first;
    await tester.drag(scrollable, const Offset(0, 10000));
    await tester.pumpAndSettle();
    final scenario = find.text('Normal · NORMAL');
    await tester.scrollUntilVisible(scenario, 280, scrollable: scrollable);
    await tester.pumpAndSettle();
  }

  Future<void> openDashboard(WidgetTester tester) async {
    await tester.tap(find.byTooltip('Backend dashboard'));
    await tester.pumpAndSettle();
  }

  testWidgets('shows the backend dashboard fields from the flat response', (
    tester,
  ) async {
    transport.responses.add(
      const ApiTransportResponse(statusCode: 200, body: _dashboardWithIncident),
    );
    await pumpIntegratedApp(tester);
    await tester.pumpAndSettle();
    await openDashboard(tester);

    expect(find.text('Backend dashboard response'), findsOneWidget);
    expect(find.text('Subject ID: subject-123'), findsOneWidget);
    expect(find.text('Monitoring status: INCIDENT_ACTIVE'), findsOneWidget);
    expect(find.text('Latest reading: 86 bpm'), findsOneWidget);
    expect(find.text('Reading source: SIMULATED'), findsOneWidget);
    expect(find.text('Active incident: incident-456'), findsOneWidget);
    expect(find.text('Incident status: PENDING_VERIFICATION'), findsOneWidget);
    expect(transport.requests, hasLength(1));
  });

  testWidgets('handles nullable latest reading and incident fields safely', (
    tester,
  ) async {
    transport.responses.add(
      const ApiTransportResponse(
        statusCode: 200,
        body: _dashboardWithoutOptionalData,
      ),
    );
    await pumpIntegratedApp(tester);
    await tester.pumpAndSettle();
    await openDashboard(tester);

    expect(find.text('Latest reading: Unavailable'), findsOneWidget);
    expect(
      find.text('Active incident: None reported by backend'),
      findsOneWidget,
    );
    expect(find.text('Incident status: Unavailable'), findsOneWidget);
    expect(find.text('Latest update: Unavailable'), findsOneWidget);
  });

  testWidgets('shows loading while the dashboard request is pending', (
    tester,
  ) async {
    tester.view.devicePixelRatio = 1;
    tester.view.physicalSize = const Size(900, 2400);
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    transport.pending = Completer<ApiTransportResponse>();
    await pumpIntegratedApp(tester);
    await tester.pump();
    await tester.tap(find.byTooltip('Backend dashboard'));
    await tester.pump();

    expect(find.text('Backend dashboard'), findsOneWidget);
    expect(find.text('Loading the latest dashboard response…'), findsOneWidget);

    transport.pending!.complete(
      const ApiTransportResponse(statusCode: 200, body: _dashboardWithIncident),
    );
    await tester.pumpAndSettle();
    expect(find.text('Monitoring status: INCIDENT_ACTIVE'), findsOneWidget);
  });

  testWidgets('shows API error and retry reloads the dashboard', (
    tester,
  ) async {
    transport.responses.addAll([
      const ApiTransportResponse(
        statusCode: 503,
        body: '{"detail":"Dashboard service unavailable"}',
      ),
      const ApiTransportResponse(statusCode: 200, body: _dashboardWithIncident),
    ]);
    await pumpIntegratedApp(tester);
    await tester.pumpAndSettle();
    await openDashboard(tester);

    expect(find.text('Dashboard unavailable'), findsOneWidget);
    expect(find.text('Dashboard service unavailable'), findsOneWidget);
    await tester.tap(find.text('Try again'));
    await tester.pumpAndSettle();

    expect(find.text('Monitoring status: INCIDENT_ACTIVE'), findsOneWidget);
    expect(transport.requests, hasLength(2));
  });

  testWidgets(
    'unauthenticated dashboard explains sign-in and sends no request',
    (tester) async {
      session.clear();
      await pumpIntegratedApp(tester);
      await tester.pumpAndSettle();
      await openDashboard(tester);

      expect(find.text('Sign-in required'), findsOneWidget);
      expect(
        find.text(
          'Authenticate to load dashboard data. No protected API request was sent.',
        ),
        findsOneWidget,
      );
      expect(transport.requests, isEmpty);
    },
  );

  testWidgets('local preview data and scenario controls remain available', (
    tester,
  ) async {
    session.clear();
    await pumpIntegratedApp(tester);
    await tester.pumpAndSettle();

    expect(find.text('NOT LIVE DATA'), findsOneWidget);
    expect(find.text('SAMPLE / DEMO DATA'), findsOneWidget);
    await scrollToScenario(tester);
    final scenario = find.text('Normal · NORMAL');
    final scenarioCard = find
        .ancestor(of: scenario, matching: find.byType(Card))
        .first;
    final playButton = find.descendant(
      of: scenarioCard,
      matching: find.widgetWithText(FilledButton, 'Play'),
    );
    expect(playButton, findsOneWidget);
    expect(tester.widget<FilledButton>(playButton).onPressed, isNotNull);
  });
}
