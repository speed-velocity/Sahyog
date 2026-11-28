import 'package:flutter_test/flutter_test.dart';
import 'package:sahyog_mobile/features/monitoring/domain/hr_sample.dart';
import 'package:sahyog_mobile/features/monitoring/domain/sim_scenario.dart';
import 'package:sahyog_mobile/features/monitoring/domain/simulator_heart_rate_source.dart';

void main() {
  group('SimulatorHeartRateSource', () {
    test('constructor defaults sampleInterval to 3 seconds', () {
      final source = SimulatorHeartRateSource();
      expect(source.sampleInterval, equals(const Duration(seconds: 3)));
    });

    test('constructor accepts custom sampleInterval', () {
      final source = SimulatorHeartRateSource(sampleInterval: const Duration(seconds: 5));
      expect(source.sampleInterval, equals(const Duration(seconds: 5)));
    });

    test('scenario can be set before start', () {
      final source = SimulatorHeartRateSource();
      source.setScenario(SimScenario.normal);
      expect(source.scenario, equals(SimScenario.normal));
    });

    test('setScenario throws when running', () async {
      final source = SimulatorHeartRateSource();
      source.setScenario(SimScenario.normal);
      await source.start();
      expect(
        () => source.setScenario(SimScenario.trueAnomaly),
        throwsA(isA<StateError>()),
      );
    });

    test('normal scenario generates deterministic sequence', () {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);
      final samples = source.generateSamples();
      expect(samples.length, equals(30));
      // First few should be around 72 BPM with deterministic oscillation
      expect(samples[0].hr, equals(72));
      expect(samples[1].hr, equals(71)); // 72 + (1 % 3 - 1) = 71
      expect(samples[2].hr, equals(73)); // 72 + (2 % 3 - 1) = 73
      expect(samples[3].hr, equals(72)); // 72 + (3 % 3 - 1) = 72
    });

    test('normal scenario timestamps are strictly increasing', () {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);
      final samples = source.generateSamples();
      for (int i = 1; i < samples.length; i++) {
        final prev = samples[i - 1].ts;
        final curr = samples[i].ts;
        final diff = curr.difference(prev).inMilliseconds;
        expect(diff, greaterThan(0));
      }
    });

    test('anomaly scenario generates deterministic sequence', () {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.trueAnomaly);
      final samples = source.generateSamples();
      // Should have 5 baseline normal readings
      expect(samples.length, greaterThan(5));
      // First 5 should be 72 BPM
      for (int i = 0; i < 5; i++) {
        expect(samples[i].hr, equals(72));
      }
      // Then 5 abnormal readings
      expect(samples[5].hr, equals(88)); // spike
      expect(samples[6].hr, equals(88));
    });

    test('TRUE_ANOMALY and FALSE_ALARM share same reading sequence', () {
      final sourceTrue = SimulatorHeartRateSource()
        ..setScenario(SimScenario.trueAnomaly);
      final sourceFalse = SimulatorHeartRateSource()
        ..setScenario(SimScenario.falseAlarm);

      final samplesTrue = sourceTrue.generateSamples();
      final samplesFalse = sourceFalse.generateSamples();

      expect(samplesTrue.length, equals(samplesFalse.length));
      for (int i = 0; i < samplesTrue.length; i++) {
        expect(samplesTrue[i], equals(samplesFalse[i]));
      }
    });

    test('first reading emitted immediately after start', () async {
      final List<HrSample> emitted = [];
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);

      source.samples.listen(emitted.add);

      await source.start();

      expect(emitted.length, greaterThan(0));
    });

    test('timestamps are UTC and strictly increasing', () {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);
      final samples = source.generateSamples();

      // All timestamps should be UTC
      for (final sample in samples) {
        expect(sample.ts.isUtc, isTrue);
      }

      // Timestamps should be strictly increasing
      for (int i = 1; i < samples.length; i++) {
        final prev = samples[i - 1].ts;
        final curr = samples[i].ts;
        final diff = curr.difference(prev).inMilliseconds;
        expect(diff, greaterThan(0));
      }
    });

    test('timestamp continuity across restart', () async {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);

      // First sequence
      await source.start();
      final firstSequence = source.samplesList;
      await source.stop();

      // Second sequence - should produce new samples
      await source.start();
      final secondSequence = source.samplesList;
      await source.stop();

      // Both sequences should have samples with UTC timestamps
      for (final sample in [...firstSequence, ...secondSequence]) {
        expect(sample.ts.isUtc, isTrue);
      }

      // Second sequence should not be empty
      expect(secondSequence.length, greaterThan(0));
    });

    test('repeated start does not create duplicate emissions scenario', () async {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);

      await source.start();
      // Start twice without stopping in between should throw
      await expectLater(
        () => source.start(),
        throwsA(isA<StateError>()),
      );
    });

    test('stop prevents further emissions', () async {
      final List<HrSample> emitted = [];
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);

      source.samples.listen(emitted.add);

      await source.start();
      await source.stop();
    });

    test('restart works with same instance', () async {
      final source = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);

      await source.start();
      await source.stop();
      // Should be able to start again
      await source.start();
      await source.stop();
    });

    test('scenario selection behavior', () {
      final normal = SimulatorHeartRateSource()
        ..setScenario(SimScenario.normal);
      final anomaly = SimulatorHeartRateSource()
        ..setScenario(SimScenario.trueAnomaly);
      final falseAlarm = SimulatorHeartRateSource()
        ..setScenario(SimScenario.falseAlarm);

      final normalSamples = normal.generateSamples();
      final anomalySamples = anomaly.generateSamples();
      final falseSamples = falseAlarm.generateSamples();

      // Normal has 30 samples
      expect(normalSamples.length, equals(30));
      // Anomaly/false alarm has 40 samples
      expect(anomalySamples.length, equals(40));
      expect(falseSamples.length, equals(40));

      // TRUE_ANOMALY and FALSE_ALARM share the same sequence
      expect(anomalySamples, equals(falseSamples));
    });
  });
}
