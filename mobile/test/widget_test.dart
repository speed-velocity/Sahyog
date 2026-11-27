import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/app/sahyog_app.dart';
import 'package:sahyog_mobile/features/monitoring/presentation/monitoring_reading_panel.dart';
import 'package:sahyog_mobile/features/monitoring/presentation/preview_session_controller.dart';
import 'package:sahyog_mobile/shared/widgets/async_state_panel.dart';

Future<void> _scrollTo(WidgetTester tester, Finder finder) async {
  final scrollable = find.byType(Scrollable).first;
  await tester.drag(scrollable, const Offset(0, 10000));
  await tester.pumpAndSettle();
  await tester.scrollUntilVisible(
    finder,
    280,
    scrollable: scrollable,
  );
  await tester.pumpAndSettle();
}

Finder _scenarioCard(DemoScenario scenario) => find
    .ancestor(
      of: find.text('${scenario.title} · ${scenario.wireLabel}'),
      matching: find.byType(Card),
    )
    .first;

Finder _scenarioButton(DemoScenario scenario, String label) => find.descendant(
  of: _scenarioCard(scenario),
  matching: find.widgetWithText(FilledButton, label),
);

Future<void> _startScenario(
  WidgetTester tester,
  DemoScenario scenario, {
  String buttonLabel = 'Play',
}) async {
  await _scrollTo(
    tester,
    find.text('${scenario.title} · ${scenario.wireLabel}'),
  );
  final button = _scenarioButton(scenario, buttonLabel);
  await tester.ensureVisible(button);
  await tester.tap(button);
  await tester.pump();
}

void main() {
  testWidgets('sample value is separated from live reading state', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await _scrollTo(tester, find.text('72 bpm'));
    expect(find.text('72 bpm'), findsOneWidget);
    expect(find.text('NOT LIVE DATA'), findsOneWidget);
    expect(find.text('SAMPLE / DEMO DATA'), findsOneWidget);
    expect(
      find.text(
        'Sample value only · not from a sensor, simulator, or backend.',
      ),
      findsOneWidget,
    );
  });

  testWidgets('all scenarios start in the preview and can be reset', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());

    for (final scenario in DemoScenario.values) {
      final scenarioTitle = find.textContaining(scenario.wireLabel);
      await _scrollTo(tester, scenarioTitle);
      final scenarioCard = find
          .ancestor(of: scenarioTitle, matching: find.byType(Card))
          .first;
      final playButton = find.descendant(
        of: scenarioCard,
        matching: find.widgetWithText(FilledButton, 'Play'),
      );
      await tester.ensureVisible(playButton);
      await tester.pumpAndSettle();
      await tester.tap(playButton);
      await tester.pump();

      expect(
        find.text('${scenario.wireLabel} · ${scenario.title}'),
        findsOneWidget,
      );
      expect(find.text('60s remaining'), findsOneWidget);
      expect(find.text('Running'), findsOneWidget);
      expect(find.text('PREVIEW RUNNING'), findsOneWidget);

      await tester.drag(
        find.byType(ListView).first,
        const Offset(0, 10000),
      );
      await tester.pump();
      expect(
        find.text('Local preview only · no sensor, simulator, or backend is connected.'),
        findsOneWidget,
      );
      expect(find.text('SAMPLE / DEMO DATA'), findsOneWidget);
      expect(find.text('NOT LIVE DATA'), findsOneWidget);
      expect(find.text('Connected'), findsNothing);
      expect(find.text('No readings available'), findsOneWidget);

      await tester.pump(const Duration(seconds: 1));
      expect(find.text('59s remaining'), findsOneWidget);

      if (scenario == DemoScenario.normal) {
        final otherScenario = find.textContaining('TRUE_ANOMALY');
        await _scrollTo(tester, otherScenario);
        final otherCard = find
            .ancestor(of: otherScenario, matching: find.byType(Card))
            .first;
        final otherButton = find.descendant(
          of: otherCard,
          matching: find.byType(FilledButton),
        );
        expect(tester.widget<FilledButton>(otherButton).onPressed, isNull);
      }

      await _scrollTo(tester, find.text('Reset preview'));
      await tester.tap(find.text('Reset preview'));
      await tester.pumpAndSettle();
      await _scrollTo(tester, find.text('No preview selected'));
      expect(find.text('No preview selected'), findsOneWidget);
    }
  });

  testWidgets(
    'completed scenario can be replayed without claiming an outcome',
    (tester) async {
      await tester.pumpWidget(const SahyogApp());
      final normal = find.textContaining('NORMAL');
      await _scrollTo(tester, normal);
      final card = find.ancestor(of: normal, matching: find.byType(Card)).first;
      final playButton = find.descendant(
        of: card,
        matching: find.widgetWithText(FilledButton, 'Play'),
      );
      await tester.ensureVisible(playButton);
      await tester.pumpAndSettle();
      await tester.tap(playButton);
      await tester.pump();
      await tester.pump(const Duration(seconds: 60));

      await _scrollTo(tester, find.text('Local preview timer ended'));
      expect(find.text('Local preview timer ended'), findsOneWidget);
      expect(
        find.text(
          'Only the local preview timer ended. Monitoring and anomaly detection did not run, and no incident outcome was created.',
        ),
        findsOneWidget,
      );
      await tester.drag(find.byType(ListView).first, const Offset(0, 900));
      await tester.pumpAndSettle();
      final replay = find.widgetWithText(FilledButton, 'Replay');
      await _scrollTo(tester, replay);
      await tester.ensureVisible(replay);
      await tester.pumpAndSettle();
      await tester.tap(replay);
      await tester.pump();
      await _scrollTo(tester, find.text('Running'));
      expect(find.text('Running'), findsOneWidget);
    },
  );

  testWidgets('every running scenario disables the other scenario buttons', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());

    for (final activeScenario in DemoScenario.values) {
      await _startScenario(tester, activeScenario);
      expect(find.text('PREVIEW RUNNING'), findsOneWidget);

      for (final otherScenario in DemoScenario.values.where(
        (scenario) => scenario != activeScenario,
      )) {
        await _scrollTo(
          tester,
          find.text('${otherScenario.title} · ${otherScenario.wireLabel}'),
        );
        final otherButton = _scenarioButton(otherScenario, 'Play');
        await tester.ensureVisible(otherButton);
        expect(tester.widget<FilledButton>(otherButton).onPressed, isNull);
      }

      await _scrollTo(tester, find.text('Reset preview'));
      await tester.tap(find.text('Reset preview'));
      await tester.pumpAndSettle();
      expect(find.text('No preview selected'), findsOneWidget);
    }
  });

  testWidgets('resetting a completed scenario allows a different scenario', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await _startScenario(tester, DemoScenario.normal);
    await tester.pump(const Duration(seconds: 60));

    await _scrollTo(tester, find.text('Local preview timer ended'));
    expect(find.text('Local preview timer ended'), findsOneWidget);
    await _scrollTo(tester, find.text('Reset preview'));
    await tester.tap(find.text('Reset preview'));
    await tester.pumpAndSettle();

    expect(find.text('No preview selected'), findsOneWidget);
    expect(find.text('IDLE'), findsOneWidget);
    await _startScenario(tester, DemoScenario.falseAlarm);
    expect(find.text('FALSE_ALARM · False alarm'), findsOneWidget);
    expect(find.text('60s remaining'), findsOneWidget);
    expect(find.text('Running'), findsOneWidget);
  });

  testWidgets('replay resets completed preview progress to the beginning', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await _startScenario(tester, DemoScenario.normal);
    await tester.pump(const Duration(seconds: 60));
    await _scrollTo(tester, find.text('Local preview timer ended'));

    await tester.drag(find.byType(ListView).first, const Offset(0, 5000));
    await tester.pumpAndSettle();
    await _startScenario(tester, DemoScenario.normal, buttonLabel: 'Replay');
    await tester.drag(
      find.byType(ListView).first,
      const Offset(0, 10000),
    );
    await tester.pump();
    expect(find.text('Running'), findsOneWidget);
    expect(find.text('60s remaining'), findsOneWidget);
    expect(find.text('0% of local preview elapsed'), findsOneWidget);
  });

  testWidgets('navigation preserves and advances a running preview', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await _startScenario(tester, DemoScenario.trueAnomaly);
    expect(find.text('Running'), findsOneWidget);

    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 2));
    await tester.tap(find.text('Monitor'));
    await tester.pumpAndSettle();
    expect(find.text('TRUE_ANOMALY · True anomaly'), findsOneWidget);
    expect(find.text('PREVIEW RUNNING'), findsOneWidget);
    expect(find.text('Running'), findsOneWidget);

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    await tester.pump(const Duration(seconds: 60));
    await tester.tap(find.text('Monitor'));
    await tester.pumpAndSettle();
    expect(find.text('TRUE_ANOMALY · True anomaly'), findsOneWidget);
    await _scrollTo(tester, find.text('Replay'));
    expect(find.text('Replay'), findsOneWidget);
    await _scrollTo(tester, find.text('Local preview timer ended'));
    expect(find.text('Local preview timer ended'), findsOneWidget);
  });

  testWidgets('true-anomaly and false-alarm previews complete and replay', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());

    for (final scenario in [
      DemoScenario.trueAnomaly,
      DemoScenario.falseAlarm,
    ]) {
      await _startScenario(tester, scenario);
      await tester.pump(const Duration(seconds: 60));
      await _scrollTo(tester, find.text('Local preview timer ended'));
      expect(find.text('Local preview timer ended'), findsOneWidget);
      expect(
        find.text(
          'Only the local preview timer ended. Monitoring and anomaly detection did not run, and no incident outcome was created.',
        ),
        findsOneWidget,
      );

      await tester.drag(find.byType(ListView).first, const Offset(0, 900));
      await tester.pumpAndSettle();
      await _startScenario(tester, scenario, buttonLabel: 'Replay');
      await _scrollTo(tester, find.text('Running'));
      expect(find.text('Running'), findsOneWidget);
      await _scrollTo(
        tester,
        find.text('${scenario.title} · ${scenario.wireLabel}'),
      );
      expect(
        find.text('${scenario.title} · ${scenario.wireLabel}'),
        findsOneWidget,
      );
      await _scrollTo(tester, find.text('Reset preview'));
      await tester.tap(find.text('Reset preview'));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('navigation exposes unavailable verification and incident data', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(find.text('Verification status unavailable'), findsOneWidget);
    expect(
      find.textContaining(
        'cannot determine whether a real verification is pending',
      ),
      findsOneWidget,
    );

    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    await tester.tap(find.text("Preview only: I'm okay"));
    await tester.pumpAndSettle();
    expect(
      find.text(
        'Preview interaction only. No reply was sent and no incident status was changed.',
      ),
      findsOneWidget,
    );

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    expect(
      find.text('Status unavailable in this frontend preview'),
      findsOneWidget,
    );
    expect(
      find.textContaining('does not indicate a safe state'),
      findsOneWidget,
    );
    await _scrollTo(tester, find.text('Escalation state supplied by backend'));
    await tester.pumpAndSettle();
    expect(find.text('Escalation state supplied by backend'), findsOneWidget);
  });

  testWidgets('repeated preview acknowledgements show one clear message', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text("Preview only: I'm okay"));

    final action = find.text("Preview only: I'm okay");
    for (var tap = 0; tap < 3; tap++) {
      await tester.tap(action);
      await tester.pumpAndSettle();
    }

    expect(action, findsOneWidget);
    expect(
      find.text(
        'Preview interaction only. No reply was sent and no incident status was changed.',
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('preview acknowledgement persists after leaving Verification', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    await tester.tap(find.text("Preview only: I'm okay"));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Monitor'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();

    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    expect(
      find.text(
        'Preview interaction only. No reply was sent and no incident status was changed.',
      ),
      findsOneWidget,
    );
    expect(tester.takeException(), isNull);
  });

  testWidgets('Incident screen remains available after tab navigation', (
    tester,
  ) async {
    await tester.pumpWidget(const SahyogApp());
    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    expect(
      find.text('Status unavailable in this frontend preview'),
      findsOneWidget,
    );

    await tester.tap(find.text('Monitor'));
    await tester.pumpAndSettle();
    expect(find.text('Good care starts with clarity.'), findsOneWidget);

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    expect(find.text('Incident status'), findsNWidgets(2));
    expect(
      find.text('Status unavailable in this frontend preview'),
      findsOneWidget,
    );
  });

  testWidgets(
    'planned escalation and resolution are labeled backend supplied',
    (tester) async {
      await tester.pumpWidget(const SahyogApp());
      await tester.tap(find.text('Incident'));
      await tester.pumpAndSettle();

      await _scrollTo(
        tester,
        find.text('Escalation state supplied by backend'),
      );
      expect(find.text('How the status will be presented'), findsOneWidget);
      expect(find.text('Escalation state supplied by backend'), findsOneWidget);
      await _scrollTo(
        tester,
        find.text('Resolution state supplied by backend'),
      );
      expect(find.text('Resolution state supplied by backend'), findsOneWidget);
    },
  );

  testWidgets(
    'unavailable Incident state does not claim an emergency outcome',
    (tester) async {
      await tester.pumpWidget(const SahyogApp());
      await tester.tap(find.text('Incident'));
      await tester.pumpAndSettle();

      expect(
        find.text('Status unavailable in this frontend preview'),
        findsOneWidget,
      );
      expect(
        find.textContaining('Incident status cannot be determined'),
        findsOneWidget,
      );
      expect(
        find.textContaining(
          'does not indicate a safe state or confirm detection, escalation or resolution',
        ),
        findsOneWidget,
      );
      expect(find.textContaining('Emergency detected'), findsNothing);
      expect(find.textContaining('Emergency escalated'), findsNothing);
      expect(find.textContaining('Emergency acknowledged'), findsNothing);
      expect(find.textContaining('Emergency resolved'), findsNothing);
    },
  );

  testWidgets('monitoring panel presents all connection states', (
    tester,
  ) async {
    for (final state in ConnectionDisplayState.values) {
      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(
            body: MonitoringReadingPanel(
              connectionState: state,
              readingState: ReadingDisplayState.noReadings,
            ),
          ),
        ),
      );

      final label = switch (state) {
        ConnectionDisplayState.connecting => 'Connecting',
        ConnectionDisplayState.connected => 'Connected',
        ConnectionDisplayState.disconnected => 'Disconnected',
      };
      expect(find.text(label), findsOneWidget);
      expect(find.text(label.toUpperCase()), findsOneWidget);
      expect(find.text('No readings available'), findsOneWidget);
    }
  });

  testWidgets('reading panel presents empty, available and invalid states', (
    tester,
  ) async {
    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MonitoringReadingPanel(
            connectionState: ConnectionDisplayState.disconnected,
            readingState: ReadingDisplayState.noReadings,
          ),
        ),
      ),
    );
    expect(find.text('No readings available'), findsOneWidget);
    expect(find.text('No reading timestamp available'), findsOneWidget);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MonitoringReadingPanel(
            connectionState: ConnectionDisplayState.connected,
            readingState: ReadingDisplayState.available,
            latestBpm: 84,
            timestampLabel: '2026-11-26 10:00 UTC',
          ),
        ),
      ),
    );
    expect(find.text('84'), findsOneWidget);
    expect(find.text('Latest reading timestamp'), findsOneWidget);
    expect(find.text('2026-11-26 10:00 UTC'), findsOneWidget);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MonitoringReadingPanel(
            connectionState: ConnectionDisplayState.connected,
            readingState: ReadingDisplayState.available,
            timestampLabel: '2026-11-26 10:00 UTC',
          ),
        ),
      ),
    );
    expect(find.text('Reading unavailable or invalid'), findsOneWidget);
    expect(
      find.text('The latest reading is missing its BPM value.'),
      findsOneWidget,
    );
    expect(find.text('Latest reading'), findsNothing);

    await tester.pumpWidget(
      const MaterialApp(
        home: Scaffold(
          body: MonitoringReadingPanel(
            connectionState: ConnectionDisplayState.connected,
            readingState: ReadingDisplayState.unavailableOrInvalid,
          ),
        ),
      ),
    );
    expect(find.text('Reading unavailable or invalid'), findsOneWidget);
    expect(find.text('Timestamp unavailable'), findsOneWidget);
  });

  testWidgets('frontend remains usable at a narrow phone width', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(320, 640);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const SahyogApp());
    await _scrollTo(tester, find.textContaining('FALSE_ALARM'));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    expect(find.text('Verification status unavailable'), findsOneWidget);
    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    expect(tester.takeException(), isNull);
  });

  testWidgets('frontend remains usable on a larger Android layout', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(1024, 1366);
    tester.view.devicePixelRatio = 1;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    await tester.pumpWidget(const SahyogApp());
    await _scrollTo(tester, find.textContaining('FALSE_ALARM'));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text('Resolution state supplied by backend'));
    expect(tester.takeException(), isNull);
  });

  testWidgets('frontend handles increased text scaling across screens', (
    tester,
  ) async {
    tester.view.physicalSize = const Size(360, 800);
    tester.view.devicePixelRatio = 1;
    tester.platformDispatcher.textScaleFactorTestValue = 1.6;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    addTearDown(tester.platformDispatcher.clearTextScaleFactorTestValue);

    await tester.pumpWidget(const SahyogApp());
    await _scrollTo(tester, find.textContaining('TRUE_ANOMALY'));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Verify'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text("Preview only: I'm okay"));
    expect(tester.takeException(), isNull);

    await tester.tap(find.text('Incident'));
    await tester.pumpAndSettle();
    await _scrollTo(tester, find.text('Resolution state supplied by backend'));
    expect(tester.takeException(), isNull);
  });

  testWidgets('shared panels render loading and retryable error states', (
    tester,
  ) async {
    var retried = false;
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AsyncStatePanel(
            state: AsyncPanelState.loading,
            title: 'Loading preview data',
            message: 'Waiting for a response.',
          ),
        ),
      ),
    );
    expect(find.text('Loading preview data'), findsOneWidget);
    expect(find.byType(LinearProgressIndicator), findsOneWidget);

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: AsyncStatePanel(
            state: AsyncPanelState.error,
            title: 'Preview data unavailable',
            message: 'No service is connected.',
            onRetry: () => retried = true,
          ),
        ),
      ),
    );
    expect(find.text('Preview data unavailable'), findsOneWidget);
    await tester.tap(find.text('Try again'));
    expect(retried, isTrue);
  });

  test('preview controller prevents overlapping runs and resets', () {
    final controller = PreviewSessionController(
      duration: const Duration(seconds: 2),
    );
    expect(controller.start(DemoScenario.normal), isTrue);
    expect(controller.start(DemoScenario.falseAlarm), isFalse);
    expect(controller.scenario, DemoScenario.normal);
    controller.replay();
    expect(controller.isRunning, isTrue);
    expect(controller.remainingSeconds, 2);
    expect(controller.elapsedPercentage, 0);
    controller.reset();
    expect(controller.isRunning, isFalse);
    expect(controller.scenario, isNull);
    controller.dispose();
  });
}
